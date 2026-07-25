from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class R2_KeltnerBreakoutSelective(Strategy):
    """
    Research Run #2. Keltner-channel breakout, deliberately made rare via a
    wide channel (large period/mult) plus the volatility-expansion gate
    that Research Run #1 validated as a genuine (p=0.0000), non-catastrophic
    signal. Widening the channel is the direct lever to cut frequency into
    this run's 100-169 total-trade band while keeping the same validated
    entry mechanism. Exit-at-midline (Run #1's most consistent exit style,
    confirmed again this run: an ATR-trailing-stop sibling strategy scored
    lower at the same entry settings, Sharpe 1.23 vs 1.40).

    Best stable in-range config found this run, 4h ETH-USD: 102 closed
    trades over 2022-05-15 to 2025-12-31, Sharpe 1.3956, max DD -13.46%,
    profit factor 2.24, winrate 42.2%. Cross-symbol replicated (BTC Sharpe
    0.98/96 trades, SOL Sharpe 0.37/88 trades, both never catastrophic).
    BTC-specific re-tuning, ATR-trail exit, atr_sma_period variation, 1D
    anchor-trend filter, and Jesse's built-in optimizer (210 trials,
    IS/OOS cross-check, top 2 in-range candidates re-validated on the full
    window) were all tried and none beat this config -- it appears to be
    at or near this mechanism's genuine ceiling for this pool. Strongest
    candidate of Research Run #2, still below the 1.5 Sharpe acceptance
    bar.
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
        return self.price > self.kc.upperband and self.atr > self.atr_sma * self.hp['vol_expansion_mult']

    def should_short(self) -> bool:
        return self.price < self.kc.lowerband and self.atr > self.atr_sma * self.hp['vol_expansion_mult']

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
            {'name': 'period', 'type': int, 'min': 10, 'max': 100, 'default': 25},
            {'name': 'mult', 'type': float, 'min': 1.0, 'max': 5.0, 'step': 0.1, 'default': 2.6},
            {'name': 'atr_period', 'type': int, 'min': 5, 'max': 30, 'default': 14},
            {'name': 'atr_sma_period', 'type': int, 'min': 10, 'max': 50, 'default': 20},
            {'name': 'vol_expansion_mult', 'type': float, 'min': 0.8, 'max': 2.0, 'step': 0.05, 'default': 1.1},
            {'name': 'atr_mult', 'type': float, 'min': 1.0, 'max': 4.0, 'step': 0.1, 'default': 1.5},
            {'name': 'risk_percent', 'type': float, 'min': 0.5, 'max': 3.0, 'step': 0.1, 'default': 1.5},
        ]
