from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class R2_KeltnerAsymBTC(Strategy):
    """
    Research Run #2 -- ALTERNATIVE STRATEGY (documented, NOT accepted --
    below the 1.5 Sharpe bar). Asymmetric Keltner breakout, BTC-USD 4h.

    CONFIG (manual best; the disciplined optimizer found nothing better
    out-of-sample for BTC): period=25, long_mult=2.7, short_mult=2.8,
    atr_period=14, atr_sma_period=20, vol_expansion_mult=1.0,
    atr_mult=1.35, risk_percent=1.5.

    Full window 2022-05-15 -> 2025-12-31: 97 trades, Sharpe 1.0907,
    max DD -19.2%, +23.1%/yr. Correlation vs accepted #1 (ETH 4h):
    ~0.055 (family-level) -- the most diversifying leg available.

    NOTE: a BETTER BTC option exists -- routing the accepted
    R2_KeltnerAsymmetric1h (unchanged params) on BTC-USD 1h scored
    1.293 @ 180 trades, the best BTC result of the whole run. Prefer
    that route over this file if you want a BTC leg.
    See reports/R2-FINAL-REPORT.md.
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
            {'name': 'period', 'type': int, 'min': 18, 'max': 35, 'default': 25},
            {'name': 'long_mult', 'type': float, 'min': 1.5, 'max': 3.2, 'step': 0.1, 'default': 2.7},
            {'name': 'short_mult', 'type': float, 'min': 2.3, 'max': 3.6, 'step': 0.1, 'default': 2.8},
            {'name': 'atr_period', 'type': int, 'min': 8, 'max': 24, 'default': 14},
            {'name': 'atr_sma_period', 'type': int, 'min': 12, 'max': 40, 'default': 20},
            {'name': 'vol_expansion_mult', 'type': float, 'min': 0.85, 'max': 1.25, 'step': 0.05, 'default': 1.0},
            {'name': 'atr_mult', 'type': float, 'min': 1.0, 'max': 2.2, 'step': 0.05, 'default': 1.35},
            {'name': 'risk_percent', 'type': float, 'min': 1.0, 'max': 2.0, 'step': 0.1, 'default': 1.5},
        ]
