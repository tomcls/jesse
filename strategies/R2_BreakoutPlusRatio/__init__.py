from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils
import numpy as np


class R2_BreakoutPlusRatio(Strategy):
    """
    Research Run #2. Overlay #2: asymmetric Keltner breakout + ETH/BTC
    ratio z-score fade. Round 1 (th 3.0/3.4, adx22, dz0.3): 187t/1.2953
    -- the ratio trades' long holding times BLOCK breakout entries
    (single-position mechanics), diluting the stronger component. Round
    2: rarer, shorter-lived ratio trades -- th 3.2/3.6, adx_max 20,
    exit_dz 1.2 (exit as soon as z re-enters 1.2 rather than 0.3).
    Requires a BTC-USD data route (1h).
    """

    @property
    def btc_candles(self):
        return self.get_candles(self.exchange, 'BTC-USD', self.timeframe)

    @property
    def ratio_z(self):
        n = self.hp['ratio_period'] + 5
        eth_close = self.candles[-n:, 2]
        btc_close = self.btc_candles[-n:, 2]
        m = min(len(eth_close), len(btc_close))
        series = np.log(eth_close[-m:] / btc_close[-m:])
        window = series[-self.hp['ratio_period']:]
        std = np.std(window)
        if std == 0:
            return 0.0
        return (series[-1] - np.mean(window)) / std

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
    def ratio_long_signal(self):
        return self.ratio_z < -self.hp['ratio_long_th'] and self.adx < self.hp['ratio_adx_max']

    @property
    def ratio_short_signal(self):
        return self.ratio_z > self.hp['ratio_short_th'] and self.adx < self.hp['ratio_adx_max']

    @property
    def raw_long(self):
        return self.bo_long_signal or self.ratio_long_signal

    @property
    def raw_short(self):
        return self.bo_short_signal or self.ratio_short_signal

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
            self.vars['mode'] = 'ratio'
            entry = self.price * (1 - self.hp['ratio_offset_pct'] / 100)
            stop = entry - self.atr * self.hp['ratio_atr_mult']
            qty = utils.risk_to_qty(self.available_margin, self.hp['risk_percent'], entry, stop, fee_rate=self.fee_rate)
            self.buy = qty, entry
            self.stop_loss = qty, stop

    def go_short(self):
        if self.bo_short_signal:
            self.vars['mode'] = 'breakout'
            entry = self.price
            stop = entry + self.atr * self.hp['bo_atr_mult']
            qty = utils.risk_to_qty(self.available_margin, self.hp['risk_percent'], entry, stop, fee_rate=self.fee_rate)
            self.sell = qty, entry
            self.stop_loss = qty, stop
        else:
            self.vars['mode'] = 'ratio'
            entry = self.price * (1 + self.hp['ratio_offset_pct'] / 100)
            stop = entry + self.atr * self.hp['ratio_atr_mult']
            qty = utils.risk_to_qty(self.available_margin, self.hp['risk_percent'], entry, stop, fee_rate=self.fee_rate)
            self.sell = qty, entry
            self.stop_loss = qty, stop

    def update_position(self):
        mode = self.vars.get('mode', 'breakout')
        if mode == 'ratio':
            if self.is_long and self.ratio_z >= -self.hp['ratio_exit_dz']:
                self.liquidate()
            elif self.is_short and self.ratio_z <= self.hp['ratio_exit_dz']:
                self.liquidate()
        else:
            if self.is_long and self.price <= self.kc_long.middleband:
                self.liquidate()
            elif self.is_short and self.price >= self.kc_short.middleband:
                self.liquidate()

    def hyperparameters(self) -> list:
        return [
            {'name': 'kc_period', 'type': int, 'min': 10, 'max': 150, 'default': 76},
            {'name': 'kc_long_mult', 'type': float, 'min': 1.0, 'max': 6.0, 'step': 0.1, 'default': 4.9},
            {'name': 'kc_short_mult', 'type': float, 'min': 1.0, 'max': 7.0, 'step': 0.1, 'default': 4.4},
            {'name': 'vol_expansion_mult', 'type': float, 'min': 0.8, 'max': 2.0, 'step': 0.05, 'default': 1.25},
            {'name': 'bo_atr_mult', 'type': float, 'min': 1.0, 'max': 4.0, 'step': 0.1, 'default': 1.45},
            {'name': 'ratio_period', 'type': int, 'min': 30, 'max': 200, 'default': 80},
            {'name': 'ratio_long_th', 'type': float, 'min': 2.0, 'max': 4.0, 'step': 0.1, 'default': 3.2},
            {'name': 'ratio_short_th', 'type': float, 'min': 2.0, 'max': 4.5, 'step': 0.1, 'default': 3.6},
            {'name': 'ratio_adx_max', 'type': int, 'min': 12, 'max': 45, 'default': 20},
            {'name': 'ratio_offset_pct', 'type': float, 'min': 0.05, 'max': 0.5, 'step': 0.05, 'default': 0.15},
            {'name': 'ratio_atr_mult', 'type': float, 'min': 1.5, 'max': 5.0, 'step': 0.1, 'default': 3.0},
            {'name': 'ratio_exit_dz', 'type': float, 'min': 0.0, 'max': 2.0, 'step': 0.1, 'default': 1.2},
            {'name': 'adx_period', 'type': int, 'min': 7, 'max': 30, 'default': 14},
            {'name': 'atr_period', 'type': int, 'min': 5, 'max': 30, 'default': 14},
            {'name': 'atr_sma_period', 'type': int, 'min': 10, 'max': 50, 'default': 20},
            {'name': 'risk_percent', 'type': float, 'min': 0.5, 'max': 3.0, 'step': 0.1, 'default': 1.5},
        ]
