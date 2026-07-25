from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class R2_RegimeSwitchETH(Strategy):
    """
    Research Run #2 -- ALTERNATIVE STRATEGY (documented, NOT in the
    accepted portfolio). Regime-overlay combo, ETH-USD 1h: ungated
    asymmetric Keltner breakout + ADX-gated Donchian fade (LIMIT
    entries, TP at channel midline) in one strategy, conflict-skipped,
    per-mode exits via self.vars['mode'].

    CONFIG (optimizer-derived best): adx_gate=24, dc_period=17,
    fade_offset_pct=0.18, fade_atr_mult=2.7, kc_period=76,
    kc_long_mult=4.8, kc_short_mult=4.9, vol_expansion_mult=1.2,
    bo_atr_mult=1.3, risk_percent=1.6.

    Full window 2022-04-25 -> 2025-12-31: 177 trades (4.06/month --
    NOTE: 8 trades over the research protocol's 169 ceiling), Sharpe
    1.5594, max DD -15.71%, +57.3%/yr, net +431%.

    WHY NOT IN THE PORTFOLIO: daily-PnL correlation 0.456 with accepted
    R2_KeltnerAsymmetric1h (its breakout component IS that mechanism) --
    per the dedup rule they count as one strategy, and the 1h pure
    breakout won (strictly in-range, cleanest Monte Carlo of the
    project). Use EITHER this OR R2_KeltnerAsymmetric1h, never both.
    See reports/R2-FINAL-REPORT.md.
    """

    @property
    def adx(self):
        return ta.adx(self.candles, self.hp['adx_period'])

    @property
    def atr(self):
        return ta.atr(self.candles, self.hp['atr_period'])

    @property
    def atr_sma(self):
        return ta.sma(ta.atr(self.candles, self.hp['atr_period'], sequential=True), self.hp['atr_sma_period'])

    @property
    def donchian(self):
        return ta.donchian(self.candles, self.hp['dc_period'])

    @property
    def kc_long(self):
        return ta.keltner(self.candles, self.hp['kc_period'], self.hp['kc_long_mult'])

    @property
    def kc_short(self):
        return ta.keltner(self.candles, self.hp['kc_period'], self.hp['kc_short_mult'])

    @property
    def vol_ok(self):
        return self.atr > self.atr_sma * self.hp['vol_expansion_mult']

    @property
    def bo_long_signal(self):
        return self.price > self.kc_long.upperband and self.vol_ok

    @property
    def bo_short_signal(self):
        return self.price < self.kc_short.lowerband and self.vol_ok

    @property
    def fade_long_signal(self):
        return self.adx < self.hp['adx_gate'] and self.price <= self.donchian.lowerband

    @property
    def fade_short_signal(self):
        return self.adx < self.hp['adx_gate'] and self.price >= self.donchian.upperband

    @property
    def raw_long(self):
        return self.bo_long_signal or self.fade_long_signal

    @property
    def raw_short(self):
        return self.bo_short_signal or self.fade_short_signal

    def should_long(self) -> bool:
        return self.raw_long and not self.raw_short

    def should_short(self) -> bool:
        return self.raw_short and not self.raw_long

    def should_cancel_entry(self) -> bool:
        return True

    def go_long(self):
        if self.bo_long_signal:
            self.vars['mode'] = 'breakout'
            entry = self.price
            stop = entry - self.atr * self.hp['bo_atr_mult']
            qty = utils.risk_to_qty(self.available_margin, self.hp['risk_percent'], entry, stop, fee_rate=self.fee_rate)
            self.buy = qty, entry
            self.stop_loss = qty, stop
        else:
            self.vars['mode'] = 'fade'
            entry = self.price * (1 - self.hp['fade_offset_pct'] / 100)
            stop = entry - self.atr * self.hp['fade_atr_mult']
            qty = utils.risk_to_qty(self.available_margin, self.hp['risk_percent'], entry, stop, fee_rate=self.fee_rate)
            self.buy = qty, entry
            self.stop_loss = qty, stop
            self.take_profit = qty, self.donchian.middleband

    def go_short(self):
        if self.bo_short_signal:
            self.vars['mode'] = 'breakout'
            entry = self.price
            stop = entry + self.atr * self.hp['bo_atr_mult']
            qty = utils.risk_to_qty(self.available_margin, self.hp['risk_percent'], entry, stop, fee_rate=self.fee_rate)
            self.sell = qty, entry
            self.stop_loss = qty, stop
        else:
            self.vars['mode'] = 'fade'
            entry = self.price * (1 + self.hp['fade_offset_pct'] / 100)
            stop = entry + self.atr * self.hp['fade_atr_mult']
            qty = utils.risk_to_qty(self.available_margin, self.hp['risk_percent'], entry, stop, fee_rate=self.fee_rate)
            self.sell = qty, entry
            self.stop_loss = qty, stop
            self.take_profit = qty, self.donchian.middleband

    def update_position(self):
        mode = self.vars.get('mode', 'breakout')
        if mode == 'fade':
            if self.is_long:
                self.take_profit = self.position.qty, self.donchian.middleband
            elif self.is_short:
                self.take_profit = self.position.qty, self.donchian.middleband
        else:
            if self.is_long and self.price <= self.kc_long.middleband:
                self.liquidate()
            elif self.is_short and self.price >= self.kc_short.middleband:
                self.liquidate()

    def hyperparameters(self) -> list:
        return [
            {'name': 'adx_period', 'type': int, 'min': 13, 'max': 15, 'default': 14},
            {'name': 'adx_gate', 'type': int, 'min': 20, 'max': 34, 'default': 24},
            {'name': 'atr_period', 'type': int, 'min': 13, 'max': 15, 'default': 14},
            {'name': 'atr_sma_period', 'type': int, 'min': 18, 'max': 22, 'default': 20},
            {'name': 'vol_expansion_mult', 'type': float, 'min': 1.05, 'max': 1.35, 'step': 0.05, 'default': 1.2},
            {'name': 'dc_period', 'type': int, 'min': 12, 'max': 22, 'default': 17},
            {'name': 'fade_offset_pct', 'type': float, 'min': 0.08, 'max': 0.22, 'step': 0.02, 'default': 0.18},
            {'name': 'fade_atr_mult', 'type': float, 'min': 2.3, 'max': 2.9, 'step': 0.1, 'default': 2.7},
            {'name': 'kc_period', 'type': int, 'min': 70, 'max': 84, 'default': 76},
            {'name': 'kc_long_mult', 'type': float, 'min': 4.0, 'max': 5.4, 'step': 0.1, 'default': 4.8},
            {'name': 'kc_short_mult', 'type': float, 'min': 3.9, 'max': 5.4, 'step': 0.1, 'default': 4.9},
            {'name': 'bo_atr_mult', 'type': float, 'min': 1.2, 'max': 1.65, 'step': 0.05, 'default': 1.3},
            {'name': 'risk_percent', 'type': float, 'min': 1.4, 'max': 1.7, 'step': 0.1, 'default': 1.6},
        ]
