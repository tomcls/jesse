from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class KeltnerBreakoutHybrid(Strategy):
    """
    Keltner channel breakout with a hybrid exit: take partial profit
    (half the position) at the channel midline to lock in gains early,
    then trail an ATR stop on the remaining half to let winners run.
    Combines wave 1's consistent-but-capped exit-at-midline with wave
    2's higher-ceiling-but-noisier ATR trail.
    """

    @property
    def kc(self):
        return ta.keltner(self.candles, self.hp['period'], self.hp['mult'])

    @property
    def atr(self):
        return ta.atr(self.candles, self.hp['atr_period'])

    def should_long(self) -> bool:
        return self.price > self.kc.upperband

    def should_short(self) -> bool:
        return self.price < self.kc.lowerband

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

    def on_open_position(self, order) -> None:
        half = abs(self.position.qty) / 2
        self.take_profit = half, self.kc.middleband

    def update_position(self):
        if self.is_long:
            self.stop_loss = self.position.qty, max(self.average_stop_loss, self.price - self.atr * self.hp['atr_mult'])
        elif self.is_short:
            self.stop_loss = self.position.qty, min(self.average_stop_loss, self.price + self.atr * self.hp['atr_mult'])

    def hyperparameters(self) -> list:
        return [
            {'name': 'period', 'type': int, 'min': 10, 'max': 40, 'default': 20},
            {'name': 'mult', 'type': float, 'min': 1.0, 'max': 3.5, 'step': 0.1, 'default': 2.0},
            {'name': 'atr_period', 'type': int, 'min': 5, 'max': 30, 'default': 14},
            {'name': 'atr_mult', 'type': float, 'min': 1.0, 'max': 4.0, 'step': 0.1, 'default': 2.0},
            {'name': 'risk_percent', 'type': float, 'min': 0.5, 'max': 3.0, 'step': 0.1, 'default': 1.5},
        ]
