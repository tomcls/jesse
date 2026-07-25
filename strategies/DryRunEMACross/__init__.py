"""
Dry-run test strategy — deliberately simple, do NOT tune.
EMA(20)/EMA(50) crossover on 1h. Long on golden cross, short on death cross,
fixed position size, market orders. Used only to validate the research
pipeline's mechanics (data, backtest, walk-forward, Monte Carlo, correlation).
"""

from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class DryRunEMACross(Strategy):
    @property
    def fast_ema(self):
        return ta.ema(self.candles, 20)

    @property
    def slow_ema(self):
        return ta.ema(self.candles, 50)

    def should_long(self) -> bool:
        return self.fast_ema > self.slow_ema

    def should_short(self) -> bool:
        return self.fast_ema < self.slow_ema

    def should_cancel_entry(self) -> bool:
        return False

    def go_long(self):
        qty = utils.size_to_qty(self.balance, self.price, fee_rate=self.fee_rate)
        self.buy = qty, self.price

    def go_short(self):
        qty = utils.size_to_qty(self.balance, self.price, fee_rate=self.fee_rate)
        self.sell = qty, self.price

    def update_position(self):
        if self.is_long and self.fast_ema < self.slow_ema:
            self.liquidate()

        if self.is_short and self.fast_ema > self.slow_ema:
            self.liquidate()
