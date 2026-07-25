from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class MomentumRsi50Cross(Strategy):
    """
    Momentum continuation: enter when RSI crosses the 50 midline
    (confirming a shift in momentum direction), exit on the opposite
    cross or an ATR stop.
    """

    @property
    def rsi(self):
        return ta.rsi(self.candles, self.hp['period'])

    @property
    def atr(self):
        return ta.atr(self.candles, self.hp['atr_period'])

    def should_long(self) -> bool:
        return self.rsi > self.hp['midline']

    def should_short(self) -> bool:
        return self.rsi < self.hp['midline']

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
        if self.is_long and self.rsi < self.hp['midline']:
            self.liquidate()
        if self.is_short and self.rsi > self.hp['midline']:
            self.liquidate()

    def hyperparameters(self) -> list:
        return [
            {'name': 'period', 'type': int, 'min': 5, 'max': 30, 'default': 14},
            {'name': 'midline', 'type': int, 'min': 45, 'max': 55, 'default': 50},
            {'name': 'atr_period', 'type': int, 'min': 5, 'max': 30, 'default': 14},
            {'name': 'atr_mult', 'type': float, 'min': 1.0, 'max': 5.0, 'step': 0.1, 'default': 3.0},
            {'name': 'risk_percent', 'type': float, 'min': 0.5, 'max': 3.0, 'step': 0.1, 'default': 1.5},
        ]
