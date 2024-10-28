import sys
from termcolor import cprint
from queue import Queue
import psycopg2
from futu import OpenQuoteContext, SubType, KLType
from core.futu_live_data import CurKline, CurBidAsk, CurLast
from core.env_variables import PSQL_CREDENTIALS
import pandas as pd


class GoldenCrossEnhanceStop:
    def __init__(self, initial_capital, underlying, bar_size, para_dict):
        self.initial_capital = initial_capital
        self.underlying      = underlying
        self.bar_size        = bar_size
        self.para_dict       = para_dict
        self.long_window     = para_dict["long_window"]
        self.short_window    = para_dict["short_window"]
        self.data_q          = Queue()
        self.table_k_line    = "golden_cross_es.kline_1"

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
        

    def insert_data(self, table, data) -> bool:
        conn   = psycopg2.connect(**PSQL_CREDENTIALS)
        cur    = conn.cursor()
        match table:
            case self.table_k_line:
                query  = f"""
                    INSERT INTO {table} (time_key, code, open, high, low, close, volume, k_type, sma_short, sma_long, signal)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
        try:
            cur.execute(query, data)
            conn.commit()
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


    def action_on_signals(self):
        pass

    def record_transaction(self):
        pass

    def update_unit_status(self):
        pass

    def run(self):
        quote_ctx = OpenQuoteContext(host="127.0.0.1", port=11111)
        quote_ctx.set_handler(CurKline(self.data_q))
        quote_ctx.set_handler(CurBidAsk(self.data_q))
        quote_ctx.set_handler(CurLast(self.data_q))
        # quote_ctx.subscribe([self.underlying], [self.bar_size, SubType.ORDER_BOOK, SubType.QUOTE])
        quote_ctx.subscribe([self.underlying], [self.bar_size])

        self.last_k_record = self.read_last_record(self.table_k_line, 20) # read last record is necessary in case of system crash and reboot is needed
        last_k_dummy = None
        cur_signal = 0

        while True:
            # receive data from futu api subscription
            data_type, data = self.data_q.get()

            # process depends on incoming data type
            match data_type:
                case "k_line":      # check if signal generated
                    if last_k_dummy is not None:
                        if data[0] != last_k_dummy[0]:
                            cur_signal = self.generate_signals(last_k_dummy)
                    last_k_dummy = data
                case "bid_ask":
                    if cur_signal != 0:
                        self.action_on_signals()
                    pass


