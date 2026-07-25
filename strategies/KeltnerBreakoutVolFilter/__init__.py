from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class KeltnerBreakoutVolFilter(Strategy):
    """
    Keltner channel breakout, gated by a volatility-regime filter: only
    trade when ATR is above its own rolling average (expanding/elevated
    volatility), skipping the choppy low-volatility stretches that hurt
    the un-filtered version in wave 1/2's Fold1 and Fold3 IS windows.
    Exit-at-midline (wave 1's more consistent exit style).
    """

    @property
    def kc(self):
        return ta.keltner(self.candles, self.hp['period'], self.hp['mult'])

    @property
    def atr(self):
        return ta.atr(self.candles, self.hp['atr_period'])

    @property
    def atr_sma(self):
        return ta.sma(ta.atr(self.candles, self.hp['atr_period'], sequential=True), self.hp['atr_sma_period'])

    def should_long(self) -> bool:
        return self.price > self.kc.upperband and self.atr > self.atr_sma

    def should_short(self) -> bool:
        return self.price < self.kc.lowerband and self.atr > self.atr_sma

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
        if self.is_long and self.price <= self.kc.middleband:
            self.liquidate()
        if self.is_short and self.price >= self.kc.middleband:
            self.liquidate()

    def hyperparameters(self) -> list:
        return [
            {'name': 'period', 'type': int, 'min': 10, 'max': 40, 'default': 20},
            {'name': 'mult', 'type': float, 'min': 1.0, 'max': 3.5, 'step': 0.1, 'default': 2.0},
            {'name': 'atr_period', 'type': int, 'min': 5, 'max': 30, 'default': 14},
            {'name': 'atr_sma_period', 'type': int, 'min': 10, 'max': 50, 'default': 20},
            {'name': 'atr_mult', 'type': float, 'min': 1.0, 'max': 4.0, 'step': 0.1, 'default': 2.0},
            {'name': 'risk_percent', 'type': float, 'min': 0.5, 'max': 3.0, 'step': 0.1, 'default': 1.5},
        ]
