from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class R2_KeltnerAsymmetric1h(Strategy):
    """
    Research Run #2 -- ACCEPTED STRATEGY #2 (LOCKED).
    Asymmetric Keltner-channel breakout, ETH-USD 1h.

    CONFIG (optimizer-derived, disciplined IS/OOS provenance):
    period=64, long_mult=4.8, short_mult=4.1, atr_period=15,
    atr_sma_period=18, vol_expansion_mult=1.25, atr_mult=1.25,
    risk_percent=1.7.

    Full window 2022-04-25 -> 2025-12-31: 162 trades (3.66/month),
    Sharpe 1.5559, max DD -13.73%, +54.3%/yr, net +395%, winrate 30.9%.
    Correlation vs accepted #1 (ETH 4h): 0.1705.

    Validation: IS/OOS provenance (train 1.45 / test 1.83), Monte Carlo
    textbook-clean (original Sharpe at the resampled median, net profit
    between median and best-5%), cross-symbol BTC 1.293@180t / SOL 0.18,
    cross-venue Binance same-period 1.3864@153t, HOLDOUT 2026 (one-shot,
    fired 2026-07-24): +0.79 Sharpe / 29 trades / +10.8% net on virgin
    data. Config FROZEN -- do not retune (holdout is spent).
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
            {'name': 'period', 'type': int, 'min': 60, 'max': 95, 'default': 64},
            {'name': 'long_mult', 'type': float, 'min': 3.8, 'max': 5.2, 'step': 0.1, 'default': 4.8},
            {'name': 'short_mult', 'type': float, 'min': 3.4, 'max': 4.6, 'step': 0.1, 'default': 4.1},
            {'name': 'atr_period', 'type': int, 'min': 10, 'max': 20, 'default': 15},
            {'name': 'atr_sma_period', 'type': int, 'min': 14, 'max': 30, 'default': 18},
            {'name': 'vol_expansion_mult', 'type': float, 'min': 1.1, 'max': 1.4, 'step': 0.05, 'default': 1.25},
            {'name': 'atr_mult', 'type': float, 'min': 1.2, 'max': 1.8, 'step': 0.05, 'default': 1.25},
            {'name': 'risk_percent', 'type': float, 'min': 1.2, 'max': 1.8, 'step': 0.1, 'default': 1.7},
        ]
