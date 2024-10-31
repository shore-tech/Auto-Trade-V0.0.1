import sys
from termcolor import cprint
from queue import Queue
import psycopg2
from futu import TrdEnv, OpenQuoteContext, OpenFutureTradeContext, SubType, TrdSide
from core.futu_live_data import CurKline, CurBidAsk, CurLast
from core.futu_static import get_trd_code, get_realtime_kline
from core.futu_trade import TradeOrder, place_order
from core.env_variables import PSQL_CREDENTIALS
from core.trading_acc import FutureTradingAccount
from core.key_definition import TrdAction, TrdLogic, MtmReason, DBTableColumns


class GoldenCrossEnhanceStop:
    def __init__(self, initial_capital, underlying, bar_size, para_dict, trd_env=TrdEnv.SIMULATE, acc_id=11377717):
        # database tables
        self.table_k_line       = "golden_cross_es.k_line"
        self.table_order        = "golden_cross_es.order_record"
        self.table_acc_status   = "golden_cross_es.acc_status"
        # TODO: check acc_status table -> is_close_only = True -> no trading
        acc_status = self.read_last_record(self.table_acc_status, 1)
        if len(acc_status) == 0:
            self.is_close_only = False
        else:
            pass

        self.trd_code     = get_trd_code(underlying)

        self.trd_env        = trd_env
        self.acc_id         = acc_id
        self.trade_account  = FutureTradingAccount(initial_capital)
        self.bar_size       = bar_size
        self.para_dict      = para_dict
        self.long_window    = para_dict["long_window"]
        self.short_window   = para_dict["short_window"]
        self.data_q         = Queue()
        self.cur_signal_open     = 0
        self.cur_signal_close    = 0


    def read_last_record(self, table, record_size=1) -> list:
        conn   = psycopg2.connect(**PSQL_CREDENTIALS)
        cur    = conn.cursor()
        query  = f"SELECT * FROM {table} ORDER BY updated_time DESC LIMIT {record_size}"
        cur.execute(query)
        last_record = cur.fetchall()
        last_record = last_record[::-1]
        cur.close()
        conn.close()
        last_record = [list(record) for record in last_record]
        return last_record


    def insert_data(self, table, data) -> bool:
        conn   = psycopg2.connect(**PSQL_CREDENTIALS)
        cur    = conn.cursor()

        match table:
            case (self.table_k_line | 'golden_cross_es.dummy'):
                columns = DBTableColumns.k_line

            case self.table_order:
                columns = DBTableColumns.order_record

            case self.table_acc_status:
                columns = DBTableColumns.acc_status

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


    def generate_signal_open(self, last_k_dummy) -> int:
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


    def generate_signal_close(self, last_k_dummy) -> int:
        # check if position in su_trd_acc
        # if yes, action_signal = su_trd_acc.mark_to_market() -> [margin_call, change_stop_level]
        #                           -> action_signal == margin_call -> return signal_close[1,-1]
        #                           -> action_signal == change_stop_level -> db_acc_mtm() -> return 0
        return 0


    def action_on_signal_open(self, price_bid, price_ask) -> bool:
        # if signal is generated, check the current portfolio 
        # a) if there is sufficient fund for extra contract
        # b) if position is open 
        # c) if position is on the same direction
        # d) check if there are pending orders -> yes, check order direction
        t_size      = self.cur_signal_open
        t_price     = price_bid if t_size < 0 else price_ask
        trd_side    = TrdSide.SELL if t_size < 0 else TrdSide.BUY
        trd_login   = TrdLogic.SIGNAL_SELL if t_size < 0 else TrdLogic.SIGNAL_BUY
        is_sufficient_fund = self.trade_account.bal_available > abs(t_size) * t_price * self.trade_account.contract_multiplier * self.trade_account.margin_rate
        if is_sufficient_fund:
            if (self.trade_account.position_size == 0) or (self.trade_account.position_size * t_size > 0):
                # no position / same direction -> add more contracts
                order_rsp = place_order(
                    self.trade_ctx, self.trd_code, 
                    trd_side, abs(t_size), t_price, 
                    self.acc_id, self.trd_env
                )
                if order_rsp != 'error':
                    #  update trading account
                    self.trade_account.pending_orders[order_rsp['order_id']] = {'order_status': order_rsp['order_status'], 'action': TrdAction.OPEN, 'logic': trd_login}
            else:
                #different direction -> pass, leave it to mtm() to handle
                pass
        self.cur_signal_open = 0



    
    def db_acc_mtm(self, update_time, mkt_price:float, reason:str, k_type=None, order_id=None) -> None:
        # simple record the latest account status
        match reason:
            case (MtmReason.K_LINE):
                if self.trade_account.position_size != 0:
                    # NOTE: mark_to_market() needs updated since it will trigger open/close position in simulate trade
                    # mark_to_market() should only responsible for raising action signal instead of execute directly
                    self.trade_account.mark_to_market(mkt_price)
                pass
            case MtmReason.BID_ASK:
                if self.trade_account.position_size != 0:
                    self.trade_account.mark_to_market(mkt_price)
                pass
            case MtmReason.STOP_LOSS_UPDATE:
                pass
            case MtmReason.STOP_PROFIT_UPDATE:
                pass
        values = [
            update_time,
            reason,
            self.trade_account.nav,
            self.trade_account.bal_cash,
            self.trade_account.bal_available,
            self.trade_account.margin_initial,
            self.trade_account.margin_initial * self.trade_account.margin_maintanence_rate,
            self.trade_account.cap_usage,
            self.trd_code,
            self.trade_account.position_size,
            self.trade_account.position_price,
            mkt_price,
            self.trade_account.stop_level,
            self.trade_account.target_level,
            self.trade_account.pnl_unrealized,
            k_type,
            order_id,
        ]
        self.insert_data(self.table_acc_status, values)


    def run(self):
        quote_ctx = OpenQuoteContext(host="127.0.0.1", port=11111)
        quote_ctx.set_handler(CurKline(self.data_q))
        quote_ctx.set_handler(CurBidAsk(self.data_q))
        quote_ctx.set_handler(CurLast(self.data_q))
        quote_ctx.subscribe([self.trd_code], [self.bar_size, SubType.ORDER_BOOK, SubType.QUOTE])

        self.trade_ctx = OpenFutureTradeContext(host='127.0.0.1', port=11111)
        # trade_ctx.unlock_trade('123456')
        self.trade_ctx.set_handler(TradeOrder(self.data_q))


        self.last_k_record = get_realtime_kline(self.trd_code, self.bar_size, self.long_window)
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
                            self.cur_signal_open = self.generate_signal_open(last_k_dummy)

                        # TODO: generate_signal_close()
                    last_k_dummy = data
                    # cprint(f"Data type: {data_type}, Data: {data}", "blue")

                case "bid_ask":
                    # bid_ask data is used to: a)determine the price for order and, b) mark-to-market current position
                    if self.cur_signal_open != 0:
                        cprint(f"Signal: {self.cur_signal_open}, Data: {data}", "yellow")
                        self.action_on_signal_open(data[-2], data[-1])
                    else:
                        # TODO: generate_signal_close()
                        pass

                case "order":
                    # handle with record_transaction(), mark_to_market()
                    try:
                        self.trade_account.pending_orders[data['order_id']]['order_status'] = data['order_status']
                        action = self.trade_account.pending_orders[data['order_id']]['action']
                        logic  = self.trade_account.pending_orders[data['order_id']]['logic']
                    except Exception as e:
                        cprint(f"Error: {e}", "red")
                        cprint(f"order {data['order_id']} is not initiated by this program", "red", "on_light_cyan")
                        sys.exit()

                    match data['order_status']:
                        # TODO: record transaction
                        case 'FILLED_ALL':
                            # TODO: record the su_trd_acc status
                            # TODO: remove the order from pending_orders
                            t_side = -1 if data['trd_side'] == TrdSide.SELL else 1
                            t_size = t_side * data['dealt_qty']
                            t_price = data['dealt_avg_price']
                            if action == TrdAction.OPEN:
                                stop_level = t_price - t_side * self.para_dict['stop_loss']
                                commission, pnl_realized = self.trade_account.open_position(t_size, t_price, stop_level)
                                # TODO: record the su_trd_acc status

                            else:
                                commission, pnl_realized = self.trade_account.close_position(t_size, t_price)
                                # TODO: record the su_trd_acc status
                            

                            values = list(data.values()) + [action, logic, commission, pnl_realized]
                            del self.trade_account.pending_orders[data['order_id']]
                        case _:
                            values = list(data.values()) + [action, logic, 0, 0]

                    self.insert_data(self.table_order, values)

                    cprint(f"Data type: {data_type}, Data: {data}", "yellow")


