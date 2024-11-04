from futu import TradeOrderHandlerBase, RET_OK, OrderStatus, TrdEnv, ModifyOrderOp
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


def order_query(trade_ctx, acc_id=11377717, trd_env=TrdEnv.SIMULATE) -> dict:
    ret, data = trade_ctx.order_list_query(
        status_filter_list  = [OrderStatus.SUBMITTING, OrderStatus.SUBMITTED, OrderStatus.FILLED_PART],
        acc_id              = acc_id,
        trd_env             = trd_env,
    )
    if ret == RET_OK:
        if len(data) > 0:
            data = data[['order_id', 'code', 'trd_side', 'order_type', 'order_status', 'qty','price', 'create_time', 'updated_time', 'dealt_qty', 'dealt_avg_price' ]]
            # data = data.iloc[0].to_dict(orient='records')
            print(data)
            return data
        else:
            cprint('No outstanding order', 'green')
            return {}
    else:
        cprint(f'order_list_query error: {data}', 'red')
        return {}
    

def cancel_order(trade_ctx, order_id, acc_id=11377717, trd_env=TrdEnv.SIMULATE) -> bool:
    ret, data = trade_ctx.modify_order(
        ModifyOrderOp.CANCEL, 
        order_id    = order_id,
        acc_id      = acc_id,
        trd_env     = trd_env,
        qty         = 0,
        price       = 0
    )
    if ret == RET_OK:
        cprint(f'Canceling order: {order_id}', 'yellow', 'on_cyan')
        print(data)
        cprint('Order cancelled', 'green')
        return True
    else:
        print('cancel_order error: ', data)
        return False


def cancel_all_order(trade_ctx, acc_id=11377717, trd_env=TrdEnv.SIMULATE):
    ret, data = trade_ctx.cancel_all_order(trd_env=trd_env, acc_id=acc_id)
    if ret == RET_OK:
        cprint('Canceling all outstanding orders', 'yellow', 'on_cyan')
        print(data)
        cprint('All order cancelled', 'green')
    else:
        print('cancel_all_order error: ', data)


def accinfo_query(trade_ctx, acc_id=11377717, trd_env=TrdEnv.SIMULATE):
    # trade_ctx = OpenSecTradeContext(host='127.0.0.1', port=11111)
    ret, data = trade_ctx.accinfo_query(
        acc_id=acc_id,
        trd_env=TrdEnv.SIMULATE
    )
    if ret == RET_OK:
        print(data)  # 取第一行的购买力
    else:
        print('accinfo_query error: ', data)
    trade_ctx.close()