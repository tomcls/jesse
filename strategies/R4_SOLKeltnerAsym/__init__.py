from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class R4_SOLKeltnerAsym(Strategy):
    """R4 SOL working strategy. Current test: 4h, p24, (4.5, 6.0), vol 1.1, atr 1.5, risk 1.6."""

    @property
    def kc_long(self):
        return ta.keltner(self.candles, self.hp['period'], self.hp['long_mult'])

    @property
    def kc_short(self):
        return ta.keltner(self.candles, self.hp['period'], self.hp['short_mult'])

    @property
    def atr(self):
        return ta.atr(self.candles, self.hp['atr_period'])

    @property
    def atr_sma(self):
        return ta.sma(ta.atr(self.candles, self.hp['atr_period'], sequential=True), self.hp['atr_sma_period'])

    @property
    def vol_ok(self):
        return self.atr > self.atr_sma * self.hp['vol_expansion_mult']

    def should_long(self) -> bool:
        return self.price > self.kc_long.upperband and self.vol_ok

    def should_short(self) -> bool:
        return self.price < self.kc_short.lowerband and self.vol_ok

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
        if self.is_long and self.price <= self.kc_long.middleband:
            self.liquidate()
        if self.is_short and self.price >= self.kc_short.middleband:
            self.liquidate()

    def hyperparameters(self) -> list:
        return [
            {'name': 'period', 'type': int, 'min': 12, 'max': 120, 'default': 24},
            {'name': 'long_mult', 'type': float, 'min': 3.0, 'max': 8.0, 'step': 0.1, 'default': 4.5},
            {'name': 'short_mult', 'type': float, 'min': 3.0, 'max': 9.0, 'step': 0.1, 'default': 6.0},
            {'name': 'atr_period', 'type': int, 'min': 10, 'max': 20, 'default': 15},
            {'name': 'atr_sma_period', 'type': int, 'min': 14, 'max': 30, 'default': 18},
            {'name': 'vol_expansion_mult', 'type': float, 'min': 1.0, 'max': 1.4, 'step': 0.05, 'default': 1.1},
            {'name': 'atr_mult', 'type': float, 'min': 1.2, 'max': 2.0, 'step': 0.05, 'default': 1.5},
            {'name': 'risk_percent', 'type': float, 'min': 1.0, 'max': 3.0, 'step': 0.1, 'default': 1.6},
        ]
