import copy
import sys
from termcolor import cprint
from core.key_definition import TrdAction, TrdLogic


class FutureTradingAccount():
    # TODO: rewrite the __init__ function to take in initial status from database
    def __init__(self, 
        initail_cash_bal: float,
        bal_cash: float                 = None,
        bal_available: float            = None,
        bal_equity: float                      = None,
        pnl_unrealized: float           = 0,
        margin_rate:float               = 0.1, 
        margin_initial:float            = 0,
        cap_usage:float                 = 0,
        margin_maintanence_rate:float   = 0.8,
        margin_force_close_rate:float   = 0.6,
        contract_multiplier:int         = 50,
        commission_rate:float           = 23.54,
        position_size:int               = 0,
        position_price:float            = 0,
        stop_level:float                = None,
        target_level:float              = None,
    ):
        self.bal_initial             = initail_cash_bal
        self.bal_cash                = initail_cash_bal if bal_cash is None else bal_cash                   # cash balance
        self.bal_available           = initail_cash_bal if bal_available is None else bal_available         # cash available for trading = cash balance - initial margin + unrealized profit and loss
        self.bal_equity              = initail_cash_bal if bal_equity is None else bal_equity               # total equity(NAV) = cash balance + unrealized profit and loss
        self.pnl_unrealized          = pnl_unrealized                                                       # unrealized profit and loss
        self.margin_rate             = margin_rate                                                          # margin rate for opening a position
        self.margin_initial          = margin_initial                                                       # initial margin in $ term
        self.cap_usage               = cap_usage                                                            # usage of the capital = initial margin / cash balance
        self.margin_maintanence_rate = margin_maintanence_rate                                              # margin call level
        self.margin_force_close_rate = margin_force_close_rate                                              # margin force close level
        self.contract_multiplier     = contract_multiplier                                                  # contract multiplier for the future
        self.commission_rate         = commission_rate
        self.position_size           = position_size                                                        # position size -> number of contracts. note: -ve denotes short position
        self.position_price          = position_price                                                       # position price -> the averave price of the current position
        self.stop_level              = stop_level                                                           # stop level for the current position
        self.target_level            = target_level                                                         # target level for the current position

        self.pending_orders         = {}                                                                    # dictionary of pending orders

    def mark_to_market(self, mk_price) -> dict|None:
        if self.position_size == 0:
            self.pnl_unrealized = 0
            self.margin_initial = 0
            self.cap_usage      = 0
            self.position_price = 0
            self.stop_level     = None
            self.target_level   = None
        else:
            self.pnl_unrealized = (mk_price - self.position_price) * self.position_size * self.contract_multiplier
            self.margin_initial = abs(self.position_size) * mk_price * self.contract_multiplier * self.margin_rate
            self.bal_available  = self.bal_cash - self.margin_initial + self.pnl_unrealized
            self.bal_equity     = self.bal_cash + self.pnl_unrealized
            self.cap_usage      = round(self.margin_initial / (self.bal_cash + 0.0001), 4)
            if self.bal_equity < self.margin_initial * self.margin_maintanence_rate:
                cprint(f"Warning! Margin call: ${self.margin_initial - self.bal_equity}, Margin-level: {(self.bal_equity / self.margin_initial * 100):.2f}%, ", "red")
                return {'t_size': 0, 'action': None, 'logic': TrdLogic.MARGIN_CALL}
            if self.bal_equity < self.margin_initial * self.margin_force_close_rate:
                cprint(f"Warning! Force Closure!!! \nMargin-level: {(self.bal_equity / self.margin_initial * 100):.2f}%, ", "red")
                return {'t_size': -self.position_size, 'action': TrdAction.FORCED_CLOSE, 'logic': TrdLogic.MARGIN_CALL}
            
        return None


    def open_position(self, t_size:int, t_price:float):
        # new position size shall have the same sign as the current position size
        if t_size == 0 or self.position_size/t_size < 0:
            cprint("Error: New position size is 0 or direction is wrong", "red")
            sys.exit()

        self.position_price  = (self.position_size * self.position_price + t_size * t_price) / (self.position_size + t_size)
        self.position_size  += t_size
        commission           = abs(t_size) * self.commission_rate
        self.bal_cash       -= commission
        self.mark_to_market(t_price)
        return commission, -commission


    def close_position(self, t_size:int, t_price:float):
        # assume the t_size comes in with direction => t_size must have the opposite sign of the position size
        if t_size == 0 or self.position_size/t_size > 0:
            cprint("Error: Close position size is 0 or direction is wrong", "red")
            cprint(f"t_size: {t_size}, position_size: {self.position_size}", "red")
            sys.exit()

        self.position_size  += t_size
        commission           = abs(t_size) * self.commission_rate

        pnl_realized = (self.position_price - t_price) * t_size * self.contract_multiplier - commission

        self.bal_cash += pnl_realized
        self.mark_to_market(t_price)
        return commission, pnl_realized
        
