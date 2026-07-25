from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class BreakoutAtrExpansion(Strategy):
    """
    Volatility breakout: enter when price has moved more than K x ATR
    from its value N bars ago, trading in the direction of that move
    (a volatility-expansion momentum trigger).
    """

    @property
    def atr(self):
        return ta.atr(self.candles, self.hp['atr_period'])

    @property
    def ref_close(self):
        return self.candles[-1 - self.hp['lookback'], 2]

    def should_long(self) -> bool:
        return self.price - self.ref_close > self.hp['atr_mult_entry'] * self.atr

    def should_short(self) -> bool:
        return self.ref_close - self.price > self.hp['atr_mult_entry'] * self.atr

    def should_cancel_entry(self) -> bool:
        return True

    def go_long(self):
        entry = self.price
        stop = entry - self.atr * self.hp['atr_mult_stop']
        qty = utils.risk_to_qty(self.available_margin, self.hp['risk_percent'], entry, stop, fee_rate=self.fee_rate)
        self.buy = qty, entry
        self.stop_loss = qty, stop
        self.take_profit = qty, entry + self.atr * self.hp['atr_mult_stop'] * self.hp['reward_risk']

    def go_short(self):
        entry = self.price
        stop = entry + self.atr * self.hp['atr_mult_stop']
        qty = utils.risk_to_qty(self.available_margin, self.hp['risk_percent'], entry, stop, fee_rate=self.fee_rate)
        self.sell = qty, entry
        self.stop_loss = qty, stop
        self.take_profit = qty, entry - self.atr * self.hp['atr_mult_stop'] * self.hp['reward_risk']

    def update_position(self):
        pass

    def hyperparameters(self) -> list:
        return [
            {'name': 'lookback', 'type': int, 'min': 3, 'max': 20, 'default': 8},
            {'name': 'atr_period', 'type': int, 'min': 5, 'max': 30, 'default': 14},
            {'name': 'atr_mult_entry', 'type': float, 'min': 1.0, 'max': 4.0, 'step': 0.1, 'default': 1.5},
            {'name': 'atr_mult_stop', 'type': float, 'min': 1.0, 'max': 4.0, 'step': 0.1, 'default': 2.0},
            {'name': 'reward_risk', 'type': float, 'min': 0.5, 'max': 3.0, 'step': 0.1, 'default': 1.5},
            {'name': 'risk_percent', 'type': float, 'min': 0.5, 'max': 3.0, 'step': 0.1, 'default': 1.5},
        ]
