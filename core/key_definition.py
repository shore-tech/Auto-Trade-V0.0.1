import pytz


class TrdAction:
    OPEN = 'open'
    CLOSE = 'close'
    FORCED_CLOSE = 'forced_close'


class TrdLogic:
    STOP_LOSS   = 'stop_loss'
    STOP_PROFIT = 'stop_profit'
    SIGNAL_BUY  = 'signal_buy'
    SIGNAL_SELL = 'signal_sell'
    MARGIN_CALL = 'margin_call'
    EOD_RECONCILIATION = 'eod_reconciliation'


class MtmReason:
    OPEN                = TrdAction.OPEN
    CLOSE               = TrdAction.CLOSE
    EOD_RECONCILIATION  = TrdLogic.EOD_RECONCILIATION
    K_LINE              = 'k_line'
    STOP_LOSS_UPDATE    = 'stop_loss_update'
    STOP_PROFIT_UPDATE  = 'stop_profit_update'


class DBTableColumns:
    k_line = ["updated_time", "code", "open", "high", "low", "close", "volume", "k_type", "sma_short", "sma_long", "signal"]
    order_record = [
            'updated_time', 'order_id', 'order_status', 
            'code', 'order_type', 'trd_side', 'qty', 'price', 
            'dealt_qty', 'dealt_avg_price', 
            'action', 'logic', 'commission', 'pnl_realized'
    ]
    acc_status = [
        'updated_time', 
        'reason', 
        'bal_equity', 'bal_cash', 'bal_available', 'margin_i', 'margin_m', 'cap_usage', 
        'code', 'pos_size', 'pos_price', 'mkt_price', 'stop_level', 'target_level', 'pnl_unrealized', 
        'k_type', 'order_id'
    ]


class TimeZones:
    UTC     = "UTC"
    hk_tz   = pytz.timezone('Asia/Hong_Kong')
    syd_tz  = pytz.timezone('Australia/Sydney')


class TgEmoji:
    WARN_L1 = "⚠️"
    WARN_L2 = "🆘"