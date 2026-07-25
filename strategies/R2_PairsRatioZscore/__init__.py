from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils
import numpy as np


class R2_PairsRatioZscore(Strategy):
    """
    Research Run #2. ETH/BTC ratio z-score fade, ADX-gated, limit orders.
    Progress: symmetric 2.8 -> 0.5445; asym 2.6/3.1 -> 0.6537 (best);
    asym 2.4/3.4 -> 0.5876 (overshot). Round 3: keep 2.6/3.1 thresholds,
    widen exit_deadzone 0.3 -> 0.5 (helped quality in the earlier
    period=120 probe).
    Requires a BTC-USD data route on the same exchange/timeframe.
    """

    @property
    def btc_candles(self):
        return self.get_candles(self.exchange, 'BTC-USD', self.timeframe)

    @property
    def ratio_series(self):
        n = self.hp['period'] + 5
        eth_close = self.candles[-n:, 2]
        btc_close = self.btc_candles[-n:, 2]
        m = min(len(eth_close), len(btc_close))
        return np.log(eth_close[-m:] / btc_close[-m:])

    @property
    def ratio_z(self):
        series = self.ratio_series
        window = series[-self.hp['period']:]
        mean = np.mean(window)
        std = np.std(window)
        if std == 0:
            return 0.0
        return (series[-1] - mean) / std

    @property
    def adx(self):
        return ta.adx(self.candles, self.hp['adx_period'])

    @property
    def atr(self):
        return ta.atr(self.candles, self.hp['atr_period'])

    def should_long(self) -> bool:
        return self.ratio_z < -self.hp['long_threshold'] and self.adx < self.hp['adx_max']

    def should_short(self) -> bool:
        return self.ratio_z > self.hp['short_threshold'] and self.adx < self.hp['adx_max']

    def should_cancel_entry(self) -> bool:
        return True

    def go_long(self):
        entry = self.price * (1 - self.hp['limit_offset_pct'] / 100)
        stop = entry - self.atr * self.hp['atr_mult']
        qty = utils.risk_to_qty(self.available_margin, self.hp['risk_percent'], entry, stop, fee_rate=self.fee_rate)
        self.buy = qty, entry
        self.stop_loss = qty, stop

    def go_short(self):
        entry = self.price * (1 + self.hp['limit_offset_pct'] / 100)
        stop = entry + self.atr * self.hp['atr_mult']
        qty = utils.risk_to_qty(self.available_margin, self.hp['risk_percent'], entry, stop, fee_rate=self.fee_rate)
        self.sell = qty, entry
        self.stop_loss = qty, stop

    def update_position(self):
        if self.is_long and self.ratio_z >= -self.hp['exit_deadzone']:
            self.liquidate()
        elif self.is_short and self.ratio_z <= self.hp['exit_deadzone']:
            self.liquidate()

    def hyperparameters(self) -> list:
        return [
            {'name': 'period', 'type': int, 'min': 30, 'max': 200, 'default': 80},
            {'name': 'long_threshold', 'type': float, 'min': 2.0, 'max': 4.0, 'step': 0.1, 'default': 2.6},
            {'name': 'short_threshold', 'type': float, 'min': 2.0, 'max': 4.5, 'step': 0.1, 'default': 3.1},
            {'name': 'exit_deadzone', 'type': float, 'min': 0.0, 'max': 1.5, 'step': 0.1, 'default': 0.5},
            {'name': 'adx_period', 'type': int, 'min': 7, 'max': 30, 'default': 14},
            {'name': 'adx_max', 'type': int, 'min': 12, 'max': 45, 'default': 25},
            {'name': 'limit_offset_pct', 'type': float, 'min': 0.05, 'max': 0.5, 'step': 0.05, 'default': 0.15},
            {'name': 'atr_period', 'type': int, 'min': 5, 'max': 30, 'default': 14},
            {'name': 'atr_mult', 'type': float, 'min': 1.5, 'max': 5.0, 'step': 0.1, 'default': 3.0},
            {'name': 'risk_percent', 'type': float, 'min': 0.5, 'max': 3.0, 'step': 0.1, 'default': 1.5},
        ]
