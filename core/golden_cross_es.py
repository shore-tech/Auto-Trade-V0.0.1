import copy
import sys
from termcolor import cprint
from queue import Queue
import psycopg2
from futu import TrdEnv, OpenQuoteContext, OpenFutureTradeContext, SubType, TrdSide
import requests
from datetime import datetime, timedelta

from core.futu_live_data import CurKline, CurBidAsk, CurLast
from core.futu_static import get_trd_code, get_realtime_kline
from core.futu_trade import TradeOrder, place_order, order_query, cancel_order, cancel_all_order
from core.env_variables import PSQL_CREDENTIALS, TG_TOKEN, TARGET_AUDIENT_id, TIME_ZONES, WARN_L1, WARN_L2
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
        self.stop_dist      = para_dict["stop_loss"]
        self.ladder         = para_dict["ladder"]
        self.data_q         = Queue()
        self.cur_signal_open     = 0
        self.closing_position    = False
        self.cur_signal_close    = None

        self.trade_ctx      = OpenFutureTradeContext(host='127.0.0.1', port=11111)


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


    # functions for opening position
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
        cprint('recorded k-line data ...', 'yellow')
        return signal


    def action_on_signal_open(self, price_bid, price_ask) -> bool:
        # if sufficient fund and same direction, 
        #   a) place order to broker
        #   b) add the order to pending_orders in su_trd_acc
        # remove the signal_open to avoid unexpected order submission
        t_size      = self.cur_signal_open
        t_price     = price_bid if t_size < 0 else price_ask
        trd_side    = TrdSide.SELL if t_size < 0 else TrdSide.BUY
        trd_logic   = TrdLogic.SIGNAL_SELL if t_size < 0 else TrdLogic.SIGNAL_BUY
        is_sufficient_fund  = self.trade_account.bal_available > abs(t_size) * t_price * self.trade_account.contract_multiplier * self.trade_account.margin_rate
        is_same_direction   = (self.trade_account.position_size == 0) or (self.trade_account.position_size * t_size > 0)
        if is_sufficient_fund and is_same_direction:
            order_rsp = place_order(
                self.trade_ctx, self.trd_code, 
                trd_side, abs(t_size), t_price, 
                self.acc_id, self.trd_env
            )
            if order_rsp != 'error':
                self.trade_account.pending_orders[order_rsp['order_id']] = {'order_status': order_rsp['order_status'], 'action': TrdAction.OPEN, 'logic': trd_logic}

        self.cur_signal_open = 0
        cprint(f'action_on_signal_open() consumed self.cur_signal_open, self.cur_signal_open = {self.cur_signal_open}', 'yellow', 'on_magenta')


    # functions when there is an existing position, specifically for enhanced stop loss
    def update_stop_level(self, update_time, mkt_price:float, pos_direction) -> None:
        prev_stop_level = copy.deepcopy(self.trade_account.stop_level)
        if prev_stop_level is None:
            self.trade_account.stop_level = mkt_price - pos_direction * self.stop_dist
        elif (pos_direction > 0) and (mkt_price > prev_stop_level + self.stop_dist + self.ladder):
            self.trade_account.stop_level += self.ladder
        elif (pos_direction < 0) and (mkt_price < prev_stop_level - self.stop_dist - self.ladder):
            self.trade_account.stop_level -= self.ladder
        
        if self.trade_account.stop_level != prev_stop_level:
            self.record_acc_mtm(update_time, mkt_price, MtmReason.STOP_LOSS_UPDATE)
        return


    # functions for closing position
    def generate_signal_close(self, mkt_price) -> dict|None:
        pos_size        = self.trade_account.position_size
        pos_direction   = pos_size / abs(pos_size)
        stop_level      = self.trade_account.stop_level
        if (pos_direction > 0 and mkt_price < stop_level) or (pos_direction < 0 and mkt_price > stop_level):
            return {'t_size': -pos_size, 'action': TrdAction.CLOSE, 'logic': TrdLogic.STOP_LOSS}
        
        return self.trade_account.mark_to_market(mkt_price)


    def action_on_signal_close(self, price_bid, price_ask) -> None:
        # action when self.cur_signal_close != None
        # send order to futu
        t_size      = self.cur_signal_close['t_size']
        t_price     = price_bid if t_size < 0 else price_ask
        trd_side    = TrdSide.SELL if t_size < 0 else TrdSide.BUY
        trd_action  = self.cur_signal_close['action']
        trd_logic   = self.cur_signal_close['logic']
        order_rsp = place_order(
            self.trade_ctx, self.trd_code, 
            trd_side, abs(t_size), t_price, 
            self.acc_id, self.trd_env
        )
        if order_rsp != 'error':
            self.closing_position = True
            self.trade_account.pending_orders[order_rsp['order_id']] = {'order_status': order_rsp['order_status'], 'action': trd_action, 'logic': trd_logic}

        # remove signal_close to avoid multiple order submission
        self.cur_signal_close = None
        cprint(f'action_on_signal_close() consumed self.cur_signal_close, self.cur_signal_close = {self.cur_signal_close}', 'yellow', 'on_magenta')
        pass


    # function to record the account status
    def record_acc_mtm(self, update_time, mkt_price:float, reason:str, k_type=None, order_id=None) -> None:
        cprint(f'recording acc status with reason: {reason}', 'yellow')
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


    def eod_routine(self):
        # remove all pending orders 5 minutes before market close
        # chekc if position in broker acc is align with self-recorded status(su_trd_acc)
        # any descrepancy -> send notification via telegram
        outstanding_order = order_query(self.trade_ctx)
        if len(outstanding_order) > 0:
            # cancel all outstanding orders
            for _, order in outstanding_order.iterrows():
                if cancel_order(self.trade_ctx, order['order_id']):
                    msg = f'Order {order["order_id"]}, {order["trd_side"]} {order["code"]} @ {order["price"]} X {order["qty"]}, is cancelled'
                    cprint(msg, 'yellow')
                    self.tg_notify(msg)
            self.trade_account.pending_orders = {}
        else:
            print('No outstanding order')

        pass


    def tg_notify(self, msg) -> None:
        cprint(f'Sending notification: {msg}', 'yellow')
        result = requests.get(f'https://api.telegram.org/bot{TG_TOKEN}/sendMessage?chat_id={TARGET_AUDIENT_id}&text={msg}')
        print(result.json())


    def run(self):
        start_time = datetime.now(TIME_ZONES['hk_tz'])
        if start_time.hour < 3:
            end_time = start_time.replace(hour=2, minute=55, second=0)
        else:
            end_time = start_time.replace(hour=2, minute=55, second=0)+timedelta(days=1)

        quote_ctx = OpenQuoteContext(host="127.0.0.1", port=11111)
        quote_ctx.set_handler(CurKline(self.data_q))
        quote_ctx.set_handler(CurLast(self.data_q))
        quote_ctx.set_handler(CurBidAsk(self.data_q))
        quote_ctx.subscribe([self.trd_code], [self.bar_size, SubType.ORDER_BOOK, SubType.QUOTE])

        
        # trade_ctx.unlock_trade('123456')
        self.trade_ctx.set_handler(TradeOrder(self.data_q))


        self.last_k_record = get_realtime_kline(self.trd_code, self.bar_size, self.long_window)
        last_k_dummy = None

        while True:
            data_type, data = self.data_q.get()
            match data_type:
                case "k_line":      # check if signal generated
                    if last_k_dummy is not None:
                        if data[0] != last_k_dummy[0]:
                            # when there is a new k-line data, generate signal and record the current position status
                            self.cur_signal_open = self.generate_signal_open(last_k_dummy)
                            self.trade_account.mark_to_market(data[5])
                            self.record_acc_mtm(data[0], data[5], MtmReason.K_LINE)
                    last_k_dummy = data

                case "last":        # last price data is only for determining if existing position should be closed
                    if self.trade_account.position_size != 0:
                        pos_direction = self.trade_account.position_size / abs(self.trade_account.position_size)
                        self.update_stop_level(data[1] ,data[2], pos_direction)
                        if not self.closing_position:
                            self.cur_signal_close = self.generate_signal_close(data[-1])
                    pass

                case "bid_ask":     # bid_ask data is only for determining the price for order
                    if self.cur_signal_open != 0:
                        cprint(f"Signal_open: {self.cur_signal_open}, Data: {data}", "yellow")
                        self.action_on_signal_open(data[-2], data[-1])

                    if self.cur_signal_close is not None:
                        cprint(f"Signal_close: {self.cur_signal_close}, Data: {data}", "yellow")
                        self.action_on_signal_close(data[-2], data[-1])

                case "order":       # order type data is for: 1)recording orders, and 2)update the account status
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
                            t_side = -1 if data['trd_side'] == TrdSide.SELL else 1
                            t_size = t_side * data['dealt_qty']
                            t_price = data['dealt_avg_price']
                            if action == TrdAction.OPEN:
                                commission, pnl_realized = self.trade_account.open_position(t_size, t_price)
                                self.update_stop_level(data['updated_time'], t_price, t_side)
                            else:
                                commission, pnl_realized = self.trade_account.close_position(t_size, t_price)
                                self.closing_position = False
                            # record acc status
                            self.record_acc_mtm(data['updated_time'], t_price, action, None, data['order_id'])

                            values = list(data.values()) + [action, logic, commission, pnl_realized]
                            # remove the order from pending_orders
                            del self.trade_account.pending_orders[data['order_id']]

                        case _:
                            values = list(data.values()) + [action, logic, 0, 0]
                    # record the order record
                    self.insert_data(self.table_order, values)
                    cprint('recorded order record ...', 'yellow')

                    cprint(f"Data type: {data_type}, Data: {data}", "yellow")

            if datetime.now(TIME_ZONES['hk_tz']) > end_time:
                self.eod_routine()
                break


