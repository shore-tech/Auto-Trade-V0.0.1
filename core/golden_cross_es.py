import sys
from termcolor import cprint
from queue import Queue
import psycopg2
from futu import OpenQuoteContext, SubType, KLType
from core.futu_live_data import CurKline, CurBidAsk, CurLast
from core.env_variables import PSQL_CREDENTIALS


class GoldenCrossEnhanceStop:
    def __init__(self, initial_capital, underlying, bar_size, para_dict):
        self.initial_capital = initial_capital
        self.underlying      = underlying
        self.bar_size        = bar_size
        self.para_dict       = para_dict

    def read_last_kl_data(self):
        conn   = psycopg2.connect(**PSQL_CREDENTIALS)
        cur    = conn.cursor()
        table  = "golden_cross_es.kline"
        query  = f"SELECT * FROM {table} ORDER BY time_key DESC LIMIT 1"
        cur.execute(query)
        last_record = cur.fetchone()
        cur.close()
        conn.close()
        return last_record
        

    def insert_kl_data(self, data)->None:
        conn   = psycopg2.connect(**PSQL_CREDENTIALS)
        cur    = conn.cursor()
        table  = "golden_cross_es.kline"
        cur.execute(
            f"""
            INSERT INTO {table} (time_key, code, open, high, low, close, volume)
            VALUES {data};
            """
        )
        conn.commit()
        cprint(f"inserting data: {data}", "red")
        cprint(f"execute result: {cur.statusmessage}", "red")
        cur.close()
        conn.close()


    def receive_mkt_data(self, mkt_data):
        '''This function determines and controls the size of the data for generating signals'''

        pass
    
    def generate_signals(self):
        pass

    def action_on_signals(self):
        pass

    def record_transaction(self):
        pass

    def update_unit_status(self):
        pass

    def run(self):
        self.data_q = Queue()

        quote_ctx = OpenQuoteContext(host="127.0.0.1", port=11111)
        quote_ctx.set_handler(CurKline(self.data_q))
        quote_ctx.set_handler(CurBidAsk(self.data_q))
        quote_ctx.set_handler(CurLast(self.data_q))
        quote_ctx.subscribe([self.underlying], [self.bar_size, SubType.ORDER_BOOK, SubType.QUOTE])
        
        last_k_record = self.read_last_kl_data() # read last record is necessary in case of system crash and reboot is needed

        while True:
            data_type, data = self.data_q.get()
            match data_type:
                case "k_line":
                    if (last_k_record is not None) and (data[0] != last_k_record[0]):
                            self.insert_kl_data(data)
                    last_k_record = data
                    print_color = 'green'
                case "bid_ask":
                    print_color = 'yellow'
                    # pass
                case "last":
                    print_color = 'blue'
                    # pass

            cprint(f'{data_type}: {data}', print_color)
