from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils
import numpy as np


class R2_BBWidthSqueeze(Strategy):
    """
    Research Run #2. Volatility-squeeze breakout: enters when Bollinger
    Band width (relative to its own rolling average) contracted below a
    squeeze threshold within the recent lookback window, and price then
    breaks the band. Distinct mechanism from the Keltner-breakout family
    (that one fires on volatility EXPANSION; this one requires prior
    CONTRACTION first, a genuinely different filter). MARKET entry
    (breakout must be chased), ATR trailing stop.
    """

    @property
    def bb(self):
        return ta.bollinger_bands(self.candles, self.hp['bb_period'], self.hp['bb_mult'])

    @property
    def atr(self):
        return ta.atr(self.candles, self.hp['atr_period'])

    @property
    def was_squeezed(self):
        n = self.hp['bb_period'] + self.hp['squeeze_lookback'] + self.hp['squeeze_window'] + 20
        if len(self.candles) < n:
            return False
        bb_seq = ta.bollinger_bands(self.candles[-n:], self.hp['bb_period'], self.hp['bb_mult'], sequential=True)
        width_seq = (bb_seq.upperband - bb_seq.lowerband) / bb_seq.middleband
        width_sma = np.convolve(width_seq, np.ones(self.hp['squeeze_lookback']) / self.hp['squeeze_lookback'], mode='valid')
        aligned_width = width_seq[self.hp['squeeze_lookback'] - 1:]
        recent_width = aligned_width[-(self.hp['squeeze_window'] + 1):-1]
        recent_sma = width_sma[-(self.hp['squeeze_window'] + 1):-1]
        valid = ~np.isnan(recent_width) & ~np.isnan(recent_sma)
        if not np.any(valid):
            return False
        return bool(np.any(recent_width[valid] < recent_sma[valid] * self.hp['squeeze_mult']))

    def should_long(self) -> bool:
        return self.price > self.bb.upperband and self.was_squeezed

    def should_short(self) -> bool:
        return self.price < self.bb.lowerband and self.was_squeezed

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
        if self.is_long:
            self.stop_loss = self.position.qty, max(self.average_stop_loss, self.price - self.atr * self.hp['atr_mult'])
        elif self.is_short:
            self.stop_loss = self.position.qty, min(self.average_stop_loss, self.price + self.atr * self.hp['atr_mult'])

    def hyperparameters(self) -> list:
        return [
            {'name': 'bb_period', 'type': int, 'min': 10, 'max': 60, 'default': 20},
            {'name': 'bb_mult', 'type': float, 'min': 1.0, 'max': 3.5, 'step': 0.1, 'default': 2.3},
            {'name': 'squeeze_lookback', 'type': int, 'min': 10, 'max': 100, 'default': 40},
            {'name': 'squeeze_window', 'type': int, 'min': 3, 'max': 20, 'default': 3},
            {'name': 'squeeze_mult', 'type': float, 'min': 0.2, 'max': 0.95, 'step': 0.02, 'default': 0.4},
            {'name': 'atr_period', 'type': int, 'min': 5, 'max': 30, 'default': 14},
            {'name': 'atr_mult', 'type': float, 'min': 1.0, 'max': 4.0, 'step': 0.1, 'default': 2.0},
            {'name': 'risk_percent', 'type': float, 'min': 0.5, 'max': 3.0, 'step': 0.1, 'default': 1.5},
        ]
