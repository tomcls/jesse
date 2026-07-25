from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class R2_KeltnerAsymmetric(Strategy):
    """
    Research Run #2 -- CANDIDATE #1 (LOCKED).
    Asymmetric Keltner-channel breakout, ETH-USD 4h.

    CONFIG (optimizer-derived, disciplined IS/OOS provenance):
    period=25, long_mult=1.5, short_mult=3.0, atr_period=10,
    atr_sma_period=34, vol_expansion_mult=1.1, atr_mult=1.2,
    risk_percent=1.2.

    Full window 2022-05-15 -> 2025-12-31: 108 trades (2.48/month),
    Sharpe 1.5936 (Jesse native; daily-reconstruction check 1.3902),
    max DD -10.36%, PF 2.61, winrate 45.4%, +35.1%/yr, net +199%.

    Validation battery: IS/OOS provenance (train 1.55 / test 1.65),
    smooth robustness neighborhood (1.57-1.60 across atr_mult/long_mult/
    vol nudges), cross-symbol BTC 0.77 / SOL 0.72 (never catastrophic),
    Monte Carlo clean (original within resampled range, no overfit
    signature, DD better than resampled median). Supersedes the previous
    milestone (2.1/2.8/1.35 -> 1.5004@118). See
    reports/R2-CANDIDATE-1-KeltnerAsymmetric.md and STATE.md.
    """

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
            {'name': 'period', 'type': int, 'min': 15, 'max': 45, 'default': 25},
            {'name': 'long_mult', 'type': float, 'min': 1.0, 'max': 3.0, 'step': 0.1, 'default': 1.5},
            {'name': 'short_mult', 'type': float, 'min': 2.0, 'max': 4.0, 'step': 0.1, 'default': 3.0},
            {'name': 'atr_period', 'type': int, 'min': 8, 'max': 24, 'default': 10},
            {'name': 'atr_sma_period', 'type': int, 'min': 12, 'max': 40, 'default': 34},
            {'name': 'vol_expansion_mult', 'type': float, 'min': 0.85, 'max': 1.3, 'step': 0.05, 'default': 1.1},
            {'name': 'atr_mult', 'type': float, 'min': 1.0, 'max': 2.5, 'step': 0.05, 'default': 1.2},
            {'name': 'risk_percent', 'type': float, 'min': 1.0, 'max': 2.0, 'step': 0.1, 'default': 1.2},
        ]
