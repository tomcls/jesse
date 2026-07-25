from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class MomentumMacdZero(Strategy):
    """
    Momentum: enter when the MACD histogram crosses zero, exit on the
    opposite cross or an ATR stop, whichever comes first.
    """

    @property
    def macd(self):
        return ta.macd(self.candles, self.hp['fast'], self.hp['slow'], self.hp['signal'])

    @property
    def atr(self):
        return ta.atr(self.candles, self.hp['atr_period'])

    def should_long(self) -> bool:
        return self.macd.hist > 0

    def should_short(self) -> bool:
        return self.macd.hist < 0

    def should_cancel_entry(self) -> bool:
        return True

    def go_long(self):
        entry = self.price
        stop = entry - self.atr * self.hp['atr_mult']
        qty = utils.risk_to_qty(self.available_margin, self.hp['risk_percent'], entry, stop, fee_rate=self.fee_rate)
        self.buy = qty, entry
        self.stop_loss = qty, stop

    def go_short(self):
        entry = self.price
        stop = entry + self.atr * self.hp['atr_mult']
        qty = utils.risk_to_qty(self.available_margin, self.hp['risk_percent'], entry, stop, fee_rate=self.fee_rate)
        self.sell = qty, entry
        self.stop_loss = qty, stop

    def update_position(self):
        if self.is_long and self.macd.hist < 0:
            self.liquidate()
        if self.is_short and self.macd.hist > 0:
            self.liquidate()

    def hyperparameters(self) -> list:
        return [
            {'name': 'fast', 'type': int, 'min': 5, 'max': 20, 'default': 12},
            {'name': 'slow', 'type': int, 'min': 20, 'max': 40, 'default': 26},
            {'name': 'signal', 'type': int, 'min': 5, 'max': 15, 'default': 9},
            {'name': 'atr_period', 'type': int, 'min': 5, 'max': 30, 'default': 14},
            {'name': 'atr_mult', 'type': float, 'min': 1.0, 'max': 5.0, 'step': 0.1, 'default': 2.5},
            {'name': 'risk_percent', 'type': float, 'min': 0.5, 'max': 3.0, 'step': 0.1, 'default': 1.5},
        ]
