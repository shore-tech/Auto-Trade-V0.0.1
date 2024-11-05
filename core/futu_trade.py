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


def order_query(trade_ctx, acc_id=11377717, trd_env=TrdEnv.SIMULATE, status_filter_list=[OrderStatus.SUBMITTING, OrderStatus.SUBMITTED, OrderStatus.FILLED_PART]) -> dict:
    ret, data = trade_ctx.order_list_query(
        status_filter_list  = status_filter_list,
        acc_id              = acc_id,
        trd_env             = trd_env,
    )
    if ret == RET_OK:
        if len(data) > 0:
            data = data[['order_id', 'code', 'trd_side', 'order_type', 'order_status', 'qty','price', 'create_time', 'updated_time', 'dealt_qty', 'dealt_avg_price' ]]
            data = data.iloc[0].to_dict(orient='records')
            return data
        else:
            cprint('No outstanding order', 'green')
            return {}
    else:
        cprint(f'order_list_query error: {data}', 'red')
        return {}
    

def hist_order_query(trade_ctx, start_time, end_time, acc_id=11377717, trd_env=TrdEnv.SIMULATE, status_filter_list=[OrderStatus.FILLED_ALL]) -> list:
    ret, data = trade_ctx.history_order_list_query(
        status_filter_list  = status_filter_list,
        acc_id              = acc_id,
        trd_env             = trd_env,
        start               = start_time,
        end                 = end_time,
    )
    cprint(f'Historical order from {start_time} to {end_time}', 'yellow', 'on_cyan')
    if ret == RET_OK:
        if len(data) > 0:
            data = data[['updated_time', 'order_id', 'order_status', 'code', 'order_type', 'trd_side', 'qty', 'price', 'dealt_qty', 'dealt_avg_price']]
            data = data.to_dict(orient='records')
            for record in data:
                cprint(record, 'yellow')
            return data
        else:
            cprint('No historical order', 'green')
            return {}
    else:
        cprint(f'history_order_list_query error: {data}', 'red')
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
        print(data)
        cprint('Order cancelled', 'green')
        return True
    else:
        print('cancel_order error: ', data)
        return False


def position_query(trade_ctx, acc_id=11377717, trd_env=TrdEnv.SIMULATE) -> dict:
    ret, data = trade_ctx.position_list_query(
        acc_id  = acc_id,
        trd_env = trd_env,
    )
    if ret == RET_OK:
        data = data[['code', 'qty', 'can_sell_qty', 'cost_price', 'cost_price_valid', 'market_val', 'nominal_price']]
        data = data.iloc[0].to_dict()
        return data
    else:
        print('position_list_query error: ', data)
        return None