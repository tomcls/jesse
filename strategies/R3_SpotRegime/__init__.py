from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class R3_SpotRegime(Strategy):
    """
    Run #3 -- SPOT defensive regime overlay (long-only, no leverage) + band rebalancing.
    CANONICAL CONFIG (frozen): sma_period=200, ema_fast=50, ema_slow=200,
    alloc_pct=26 (x3 routes = 78% cap, 22% stable pocket), rebalance_band_pct=20.

    Prices: Binance Spot data as proxy; fees set to Kraken taker 0.4% in config;
    real execution will be a custom Kraken executor (Jesse doesn't support Kraken Spot).

    Portfolio backtest (3 routes, 2022-04-25 -> 2025-12-31, id 6aee5f66):
    Sharpe 0.7343, +21.1%/yr, MaxDD -27.58%, 26 trades, PF 3.08
    vs buy-and-hold +16%/yr, MaxDD -73%.

    - Invested when price > SMA200(1D) OR EMA50 > EMA200; both bearish = exit to stable.
    - Regime flips execute IMMEDIATELY; band 20% only for rebalancing trims
      (monthly/quarterly rebalancing of exits is catastrophic: -36/-46% DD).
    - Band rebalancing via Jesse API: trim = self.take_profit at market price,
      add = self.buy while long. (reduce_position/increase_position DO NOT exist.)
    - Robustness: Python grid = all 35 filter configs keep DD -33..-43 vs B&H -73;
      engine-level sma175 variant degrades (+13.8%/yr, DD -32) -- sma200 is the
      pre-registered classic default, not a post-hoc optimization.
    - A5 dip-buying tested and REJECTED (worsens Calmar). Euphoria brake kept
      for the executor layer, not in this strategy.
    Holdout 2026 RESERVED -- never backtest past 2025-12-31 on this strategy.
    """

    @property
    def sma200(self):
        return ta.sma(self.candles, self.hp['sma_period'])

    @property
    def ema_fast(self):
        return ta.ema(self.candles, self.hp['ema_fast'])

    @property
    def ema_slow(self):
        return ta.ema(self.candles, self.hp['ema_slow'])

    @property
    def regime_bull(self):
        return self.price > self.sma200 or self.ema_fast > self.ema_slow

    @property
    def target_value(self):
        return self.portfolio_value * (self.hp['alloc_pct'] / 100.0)

    def should_long(self) -> bool:
        return self.regime_bull

    def should_cancel_entry(self) -> bool:
        return True

    def go_long(self):
        cash = min(self.available_margin, self.target_value)
        qty = utils.size_to_qty(cash, self.price, fee_rate=self.fee_rate)
        self.buy = qty, self.price

    def update_position(self):
        if not self.regime_bull:
            self.liquidate()
            return
        band = self.hp['rebalance_band_pct'] / 100.0
        value = self.position.value
        target = self.target_value
        if value > target * (1 + band):
            excess_qty = utils.size_to_qty(value - target, self.price, fee_rate=self.fee_rate)
            if excess_qty > 0:
                self.take_profit = excess_qty, self.price
        elif value < target * (1 - band):
            deficit = min(target - value, self.available_margin)
            add_qty = utils.size_to_qty(deficit, self.price, fee_rate=self.fee_rate)
            if deficit > target * 0.05 and add_qty > 0:
                self.buy = add_qty, self.price

    def hyperparameters(self) -> list:
        return [
            {'name': 'sma_period', 'type': int, 'min': 150, 'max': 250, 'default': 200},
            {'name': 'ema_fast', 'type': int, 'min': 30, 'max': 70, 'default': 50},
            {'name': 'ema_slow', 'type': int, 'min': 150, 'max': 250, 'default': 200},
            {'name': 'alloc_pct', 'type': int, 'min': 10, 'max': 100, 'default': 26},
            {'name': 'rebalance_band_pct', 'type': int, 'min': 5, 'max': 50, 'default': 20},
        ]
