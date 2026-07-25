from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class R2_RegimeSwitch4h(Strategy):
    """
    Research Run #2. Fade overlay on the 4h MILESTONE (1.5004@118).
    Round 1 (dc14/adx28/offset0.14): 119 trades, Sharpe 1.5103 -- fade
    stream barely fires on 4h at those settings (+1 net trade). Round 2:
    make the fade contribute meaningfully -- dc=10 (more channel
    touches), adx_gate=32, offset=0.1. Expect ~15-25 fade trades.
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
            {'name': 'adx_period', 'type': int, 'min': 7, 'max': 30, 'default': 14},
            {'name': 'adx_gate', 'type': int, 'min': 15, 'max': 40, 'default': 32},
            {'name': 'atr_period', 'type': int, 'min': 5, 'max': 30, 'default': 14},
            {'name': 'atr_sma_period', 'type': int, 'min': 10, 'max': 50, 'default': 20},
            {'name': 'vol_expansion_mult', 'type': float, 'min': 0.8, 'max': 2.0, 'step': 0.05, 'default': 1.0},
            {'name': 'dc_period', 'type': int, 'min': 8, 'max': 60, 'default': 10},
            {'name': 'fade_offset_pct', 'type': float, 'min': 0.02, 'max': 1.0, 'step': 0.02, 'default': 0.1},
            {'name': 'fade_atr_mult', 'type': float, 'min': 1.5, 'max': 5.0, 'step': 0.1, 'default': 2.5},
            {'name': 'kc_period', 'type': int, 'min': 10, 'max': 100, 'default': 25},
            {'name': 'kc_long_mult', 'type': float, 'min': 1.0, 'max': 5.0, 'step': 0.1, 'default': 2.1},
            {'name': 'kc_short_mult', 'type': float, 'min': 1.0, 'max': 6.0, 'step': 0.1, 'default': 2.8},
            {'name': 'bo_atr_mult', 'type': float, 'min': 1.0, 'max': 4.0, 'step': 0.1, 'default': 1.35},
            {'name': 'risk_percent', 'type': float, 'min': 0.5, 'max': 3.0, 'step': 0.1, 'default': 1.5},
        ]
