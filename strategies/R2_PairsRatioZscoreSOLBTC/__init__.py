from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils
import numpy as np


class R2_PairsRatioZscoreSOLBTC(Strategy):
    """
    Research Run #2. Statistical arbitrage between symbols, SOL/BTC leg
    (a genuinely different pair from R2_PairsRatioZscore's ETH/BTC).
    Trades SOL-USD on the entry signal from the SOL/BTC price ratio:
    z-score of log(SOL/BTC) vs its rolling mean, fades extremes of the
    RATIO with limit orders, ADX regime filter (SOL itself not strongly
    trending). Same design as the working ETH/BTC version (period=80,
    threshold=2.8, adx_max=25, exit_deadzone=0.3 -> 104 trades, Sharpe
    0.5445 on ETH/BTC) as the starting point.
    Requires a BTC-USD data route on the same exchange/timeframe.
    """

    @property
    def btc_candles(self):
        return self.get_candles(self.exchange, 'BTC-USD', self.timeframe)

    @property
    def ratio_series(self):
        n = self.hp['period'] + 5
        sol_close = self.candles[-n:, 2]
        btc_close = self.btc_candles[-n:, 2]
        m = min(len(sol_close), len(btc_close))
        return np.log(sol_close[-m:] / btc_close[-m:])

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
        return self.ratio_z < -self.hp['threshold'] and self.adx < self.hp['adx_max']

    def should_short(self) -> bool:
        return self.ratio_z > self.hp['threshold'] and self.adx < self.hp['adx_max']

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
            {'name': 'threshold', 'type': float, 'min': 2.0, 'max': 4.0, 'step': 0.1, 'default': 2.8},
            {'name': 'exit_deadzone', 'type': float, 'min': 0.0, 'max': 1.5, 'step': 0.1, 'default': 0.3},
            {'name': 'adx_period', 'type': int, 'min': 7, 'max': 30, 'default': 14},
            {'name': 'adx_max', 'type': int, 'min': 12, 'max': 45, 'default': 25},
            {'name': 'limit_offset_pct', 'type': float, 'min': 0.05, 'max': 0.5, 'step': 0.05, 'default': 0.15},
            {'name': 'atr_period', 'type': int, 'min': 5, 'max': 30, 'default': 14},
            {'name': 'atr_mult', 'type': float, 'min': 1.5, 'max': 5.0, 'step': 0.1, 'default': 3.0},
            {'name': 'risk_percent', 'type': float, 'min': 0.5, 'max': 3.0, 'step': 0.1, 'default': 1.5},
        ]
