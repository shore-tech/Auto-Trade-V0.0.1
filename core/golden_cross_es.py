import sys
from termcolor import cprint
from queue import Queue
import psycopg2
from futu import TrdEnv, OpenQuoteContext, OpenFutureTradeContext, SubType, KLType, TrdSide
from core.futu_live_data import CurKline, CurBidAsk, CurLast
from core.futu_trade import TradeOrder, place_order
from core.env_variables import PSQL_CREDENTIALS
from core.trading_acc import FutureTradingAccount
from core.key_definition import TrdAction, TrdLogic


class GoldenCrossEnhanceStop:
    def __init__(self, initial_capital, underlying, bar_size, para_dict, trd_env=TrdEnv.SIMULATE, acc_id=11377717):
        self.trd_env        = trd_env
        self.acc_id         = acc_id
        self.trade_account  = FutureTradingAccount(initial_capital)
        self.underlying     = underlying
        self.bar_size       = bar_size
        self.para_dict      = para_dict
        self.long_window    = para_dict["long_window"]
        self.short_window   = para_dict["short_window"]
        self.data_q         = Queue()
        self.table_k_line   = "golden_cross_es.kline_1"
        self.table_order    = "golden_cross_es.order_record"
        self.cur_signal     = 0


    def read_last_record(self, table, record_size=1) -> list:
        conn   = psycopg2.connect(**PSQL_CREDENTIALS)
        cur    = conn.cursor()
        query  = f"SELECT * FROM {table} ORDER BY time_key DESC LIMIT {record_size}"
        cur.execute(query)
        last_record = cur.fetchall()
        last_record = last_record[::-1]
        cur.close()
        conn.close()
        last_record = [list(record) for record in last_record]
        return last_record
        

    def insert_data(self, table, data, mode:int=0) -> bool:
        conn   = psycopg2.connect(**PSQL_CREDENTIALS)
        cur    = conn.cursor()

        match table:
            case self.table_k_line:
                columns = ["time_key", "code", "open", "high", "low", "close", "volume", "k_type", "sma_short", "sma_long", "signal"]

            case self.table_order:
                match mode:
                    case 0: # for order status in process
                        columns = ['updated_time', 'order_id', 'order_status', 'code', 'order_type', 'trd_side', 'qty', 'price', 'dealt_qty', 'dealt_avg_price']
                    case 1: # for open/close position -> order status is submitting or filled
                        columns = ['updated_time', 'order_id', 'order_status', 'code', 'order_type', 'trd_side', 'qty', 'price', 'dealt_qty', 'dealt_avg_price', 'action', 'logic', 'commission', 'pnl_realized']

        column_str = ', '.join(columns)
        value_str = ', '.join(['%s' for _ in columns])
        query = f"INSERT INTO {table} ({column_str}) VALUES ({value_str})"

        try:
            cur.execute(query, data)
            conn.commit()
            cprint(f"inserting to: {table}", "blue")
            cprint(f"inserting data: {data}", "blue")
            cprint(f"execute result: {cur.statusmessage}", "blue")
            cur.close()
            conn.close()
            return True
        
        except Exception as e:
            cprint(f"Error: {e}", "red")
            return False


    def generate_signals(self, last_k_dummy) -> int:
        # calculate the short and long moving averages
        # determine the signals
        # insert the data into psql

        self.last_k_record.append(list(last_k_dummy))
        if len(self.last_k_record) > self.long_window + 1:
            del self.last_k_record[0]                       # remove the oldest record -> keep the size of last_k-records always < long_window + 1

        if len(self.last_k_record) < self.long_window:      # not enough data to calculate sma
            sma_short = None
            sma_long  = None
            signal     = 0
            pass
        else:                                               # calculate sma and signal
            short_window = self.last_k_record[-self.short_window:]
            long_window  = self.last_k_record[-self.long_window:]
            sma_short   = sum([record[5] for record in short_window]) / self.short_window
            sma_long    = sum([record[5] for record in long_window]) / self.long_window
            signal = 0
            if len(self.last_k_record) == self.long_window + 1:
                sma_short_prev = sum([record[5] for record in self.last_k_record[-self.short_window-1:-1]]) / self.short_window
                sma_long_prev  = sum([record[5] for record in self.last_k_record[-self.long_window-1:-1]]) / self.long_window
                if sma_short_prev < sma_long_prev and sma_short > sma_long:
                    signal = 1
                elif sma_short_prev > sma_long_prev and sma_short < sma_long:
                    signal = -1
                else:
                    signal = 0

        self.last_k_record[-1] = self.last_k_record[-1] + [sma_short, sma_long, signal]
        self.insert_data(self.table_k_line, self.last_k_record[-1])
        return signal


    def action_on_signals(self, price_bid, price_ask) -> bool:
        # if signal is generated, check the current portfolio 
        # a) if there is sufficient fund for extra contract
        # b) if position is open 
        # c) if position is on the same direction
        # d) check if there are pending orders -> yes, check order direction
        t_size      = self.cur_signal
        t_price     = price_bid if t_size < 0 else price_ask
        trd_side    = TrdSide.SELL if t_size < 0 else TrdSide.BUY
        trd_login   = TrdLogic.SIGNAL_SELL if t_size < 0 else TrdLogic.SIGNAL_BUY
        is_sufficient_fund = self.trade_account.bal_avialable > abs(t_size) * t_price * self.trade_account.contract_multiplier * self.trade_account.margin_rate
        if is_sufficient_fund:
            if (self.trade_account.position_size == 0) or (self.trade_account.position_size * t_size > 0):
                # no position / same direction -> add more contracts
                order_rsp = place_order(
                    self.trade_ctx, self.underlying, 
                    trd_side, abs(t_size), t_price, 
                    self.acc_id, self.trd_env
                )
                if order_rsp != 'error':
                    #  update trading account
                    self.trade_account.pending_orders[order_rsp['order_id']] = {'order_status': order_rsp['order_status'], 'action': TrdAction.OPEN, 'logic': trd_login}
            else:
                #different direction -> pass, leave it to mtm() to handle
                pass
        self.cur_signal = 0


    def run(self):
        quote_ctx = OpenQuoteContext(host="127.0.0.1", port=11111)
        quote_ctx.set_handler(CurKline(self.data_q))
        quote_ctx.set_handler(CurBidAsk(self.data_q))
        quote_ctx.set_handler(CurLast(self.data_q))
        quote_ctx.subscribe([self.underlying], [self.bar_size, SubType.ORDER_BOOK, SubType.QUOTE])

        self.trade_ctx = OpenFutureTradeContext(host='127.0.0.1', port=11111)
        # trade_ctx.unlock_trade('123456')
        self.trade_ctx.set_handler(TradeOrder(self.data_q))


        self.last_k_record = self.read_last_record(self.table_k_line, self.long_window) # read last record is necessary in case of system crash and reboot is needed
        last_k_dummy = None

        while True:
            # receive data from futu api subscription
            data_type, data = self.data_q.get()

            # process depends on incoming data type
            match data_type:
                case "k_line":      # check if signal generated
                    if last_k_dummy is not None:
                        if data[0] != last_k_dummy[0]:
                            # when there is a new k-line data, generate signal and record the current position status
                            self.cur_signal = self.generate_signals(last_k_dummy)
                            # TODO: portfolio mark_to_market() -> record account status
                    last_k_dummy = data
                    # cprint(f"Data type: {data_type}, Data: {data}", "blue")

                case "bid_ask":
                    # bid_ask data is used to: a)determine the price for order and, b) mark-to-market current position
                    if self.cur_signal != 0:
                        cprint(f"Signal: {self.cur_signal}, Data: {data}", "yellow")
                        self.action_on_signals(data[-2], data[-1])

                case "order":
                    # handle with record_transaction()
                    self.trade_account.pending_orders[data['order_id']]['order_status'] = data['order_status']
                    action = self.trade_account.pending_orders[data['order_id']]['action']
                    logic  = self.trade_account.pending_orders[data['order_id']]['logic']
                    mode   = 0
                    match data['order_status']:
                        case ('SUBMITTING'|'SUBMITTED'):
                            values = list(data.values()) + [action, logic, 0, 0]
                            mode = 1
                        case 'FILLED_ALL':
                            # update need to calculated realized pnl and commission
                            # TODO: portfolio mark_to_market() -> record account status
                            if action == TrdAction.OPEN:
                                commission, pnl_realized = self.trade_account.open_position(data['dealt_qty'], data['dealt_avg_price'])
                            else:
                                commission, pnl_realized = self.trade_account.close_position(data['dealt_qty'], data['dealt_avg_price'])
                            values = list(data.values()) + [action, logic, commission, pnl_realized]
                            mode = 1
                            del self.trade_account.pending_orders[data['order_id']]
                        case _:
                            values = list(data.values())

                    self.insert_data(self.table_order, values, mode=mode)

                    cprint(f"Data type: {data_type}, Data: {data}", "yellow")


