from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class MeanRevBband(Strategy):
    """
    Mean reversion: enter when price closes outside the Bollinger Bands,
    exit when price reverts to the middle band (the moving average).
    """

    @property
    def bb(self):
        return ta.bollinger_bands(self.candles, self.hp['period'], self.hp['dev'], self.hp['dev'])

    @property
    def atr(self):
        return ta.atr(self.candles, self.hp['atr_period'])

    def should_long(self) -> bool:
        return self.price < self.bb.lowerband

    def should_short(self) -> bool:
        return self.price > self.bb.upperband

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
        if self.is_long and self.price >= self.bb.middleband:
            self.liquidate()
        if self.is_short and self.price <= self.bb.middleband:
            self.liquidate()

    def hyperparameters(self) -> list:
        return [
            {'name': 'period', 'type': int, 'min': 10, 'max': 40, 'default': 20},
            {'name': 'dev', 'type': float, 'min': 1.5, 'max': 3.5, 'step': 0.1, 'default': 2.0},
            {'name': 'atr_period', 'type': int, 'min': 5, 'max': 30, 'default': 14},
            {'name': 'atr_mult', 'type': float, 'min': 1.0, 'max': 4.0, 'step': 0.1, 'default': 2.5},
            {'name': 'risk_percent', 'type': float, 'min': 0.5, 'max': 3.0, 'step': 0.1, 'default': 1.5},
        ]
