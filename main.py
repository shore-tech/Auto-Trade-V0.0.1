
from core.golden_cross_es import GoldenCrossEnhanceStop
from futu import KLType

if __name__ == '__main__':
    code        = "HK.HSImain"
    bar_size    = KLType.K_1M 
    su = GoldenCrossEnhanceStop(
        initial_capital = 1_000_000,
        underlying      = code,
        bar_size        = bar_size,
        para_dict       = {
            "short_window"  : 5,
            "long_window"   : 20,
            "stop_loss"     : 30,
            "ladder"        : 20,
        }
    )
    su.run()



