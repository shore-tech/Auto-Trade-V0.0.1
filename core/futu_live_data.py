from futu import CurKlineHandlerBase, OrderBookHandlerBase, StockQuoteHandlerBase, RET_OK
class CurKline(CurKlineHandlerBase):
    def __init__(self, queue):
        self.queue = queue

    def on_recv_rsp(self, rsp_pb):
        ret_code, data = super().on_recv_rsp(rsp_pb)
        if ret_code == RET_OK:
            time_key = data["time_key"][0]
            code = data["code"][0]
            open = float(data["open"][0])
            high = float(data["high"][0])
            low = float(data["low"][0])
            close = float(data["close"][0])
            volume = int(data["volume"][0])
            # k_type = data["k_type"][0]
            # self.queue.put(('k_line' ,(time_key, code, open, high, low, close, volume, k_type)))
            self.queue.put(('k_line' ,(time_key, code, open, high, low, close, volume)))


class CurBidAsk(OrderBookHandlerBase):
    def __init__(self, queue):
        self.queue = queue

    def on_recv_rsp(self, rsp_str):
        ret_code, data = super().on_recv_rsp(rsp_str)
        if ret_code == RET_OK:
            code      = data['code']
            data_time = data['svr_recv_time_bid']
            bid_price = int(data['Bid'][0][0])
            ask_price = int(data['Ask'][0][0])
            self.queue.put(('bid_ask', (code, data_time, bid_price, ask_price)))
            
    
class CurLast(StockQuoteHandlerBase):
    def __init__(self, queue):
        self.queue = queue

    def on_recv_rsp(self, rsp_str):
        ret_code, data = super().on_recv_rsp(rsp_str)
        if ret_code == RET_OK:
            code        = data.at[0, 'code']
            data_time   = data.at[0, 'data_time']
            last_price  = int(data.at[0, 'last_price'])
            self.queue.put(('last', (code, data_time, last_price)))
        