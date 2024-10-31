
from core.golden_cross_es import GoldenCrossEnhanceStop
from futu import KLType

if __name__ == '__main__':
    code        = "HK.HSImain"
    bar_size    = KLType.K_1M 
    su = GoldenCrossEnhanceStop(
        initial_capital =1000000,
        underlying      =code,
        bar_size        =bar_size,
        para_dict       ={
            "short_window"  : 2,
            "long_window"   : 3,
            "stop_loss"     : 30,
            "ladder"        : 20,
        }
    )
    su.run()



