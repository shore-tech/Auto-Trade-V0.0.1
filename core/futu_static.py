import sys
from futu import OpenQuoteContext, RET_OK
from termcolor import cprint

def get_trd_code(code:str) -> str:
    quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
    ret, data = quote_ctx.get_future_info([code])
    if ret == RET_OK:
        original_code = data.iloc[0]['origin_code']
        quote_ctx.close()
        return original_code
    else:
        quote_ctx.close()
        return 'error'


def get_realtime_kline(code:str, kl_type:str, num:int) -> list | str:
    quote_ctx = OpenQuoteContext(host="127.0.0.1", port=11111)
    ret_sub, err_message = quote_ctx.subscribe([code], [kl_type], subscribe_push=False)
    if ret_sub == RET_OK:
        ret, data = quote_ctx.get_cur_kline(code, num, kl_type)
        quote_ctx.close()
        if ret == RET_OK:
            # print(data)
            data = data[['time_key', 'code', 'open', 'high', 'low', 'close', 'volume']]
            data['k_type'] = kl_type
            return data.values.tolist()
        else:
            cprint("Faital Error: get_realtime_kline fail", "red")
            sys.exit()
    else:
        cprint("Faital Error: get_realtime_kline subsciption fail", "red")
        sys.exit()



if __name__ == '__main__':
    get_realtime_kline('HK.HSImain', 'K_5M', 2)