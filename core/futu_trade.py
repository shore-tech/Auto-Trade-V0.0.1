from futu import TradeOrderHandlerBase, RET_OK, OrderStatus, TrdEnv
from termcolor import cprint
class TradeOrder(TradeOrderHandlerBase):
    def __init__(self, data_q):
        self.data_q = data_q

    def on_recv_rsp(self, rsp_str):
        ret_code, data = super().on_recv_rsp(rsp_str)
        if ret_code == RET_OK:
            data = data[['updated_time', 'order_id', 'order_status', 'code', 'order_type', 'trd_side', 'qty', 'price', 'dealt_qty', 'dealt_avg_price']]
            data = data.iloc[0].to_dict()
            self.data_q.put(('order', data))


def order_query(trade_ctx, acc_id=11377717, trd_env=TrdEnv.SIMULATE) -> list:
    ret, data = trade_ctx.history_order_list_query(
        status_filter_list  = [OrderStatus.SUBMITTING, OrderStatus.SUBMITTED, OrderStatus.FILLED_PART],
        acc_id              = acc_id,
        trd_env             = TrdEnv.trd_env,
    )
    if ret == RET_OK:
        data = data[['order_id', 'code', 'trd_side', 'order_type', 'order_status', 'qty','price', 'create_time', 'updated_time', 'dealt_qty', 'dealt_avg_price' ]]
        cprint('order_query: {data}', 'green')
        return data.to_dict(orient='records')
    else:
        print('history_order_list_query error: ', data)

def place_order(trade_ctx, code, trd_side, qty, price, acc_id, trd_env=TrdEnv.SIMULATE) -> dict:
    ret, data = trade_ctx.place_order(
        code        = code,
        trd_side    = trd_side,
        qty         = qty,
        price       = price,
        acc_id      = acc_id,
        trd_env     = trd_env,
    )
    if ret == RET_OK:
        data = data[['updated_time', 'order_id', 'order_status', 'code', 'order_type', 'trd_side', 'qty', 'price', 'dealt_qty', 'dealt_avg_price']]
        cprint(f'place_order: {data}', 'green')
        return data.iloc[0].to_dict()
    else:
        print('place_order error: ', data)
        return 'error'