from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class GridMeanReversion(Strategy):
    """
    Grid mean reversion: on a z-score extreme, lay down a multi-level grid
    of limit entries at increasing distance from price (scaling in as the
    move extends), single take-profit back at the mean, single hard stop
    below/above the deepest grid level. Multi-entry, multi-exit by
    construction - genuinely different mechanism from single-shot entries.
    """

    @property
    def sma(self):
        return ta.sma(self.candles, self.hp['sma_period'])

    @property
    def z(self):
        return ta.zscore(self.candles, self.hp['sma_period'])

    @property
    def atr(self):
        return ta.atr(self.candles, self.hp['atr_period'])

    def should_long(self) -> bool:
        return self.z < -self.hp['threshold']

    def should_short(self) -> bool:
        return self.z > self.hp['threshold']

    def should_cancel_entry(self) -> bool:
        return True

    def _grid_qty(self, entry, stop):
        total_qty = utils.risk_to_qty(self.available_margin, self.hp['risk_percent'], entry, stop, fee_rate=self.fee_rate)
        return total_qty / self.hp['levels']

    def go_long(self):
        entry = self.price
        stop = entry - self.atr * self.hp['grid_depth_atr'] * self.hp['levels']
        qty = self._grid_qty(entry, stop)
        self.buy = [(qty, entry - i * self.hp['grid_depth_atr'] * self.atr) for i in range(self.hp['levels'])]

    def go_short(self):
        entry = self.price
        stop = entry + self.atr * self.hp['grid_depth_atr'] * self.hp['levels']
        qty = self._grid_qty(entry, stop)
        self.sell = [(qty, entry + i * self.hp['grid_depth_atr'] * self.atr) for i in range(self.hp['levels'])]

    def on_open_position(self, order) -> None:
        if self.is_long:
            self.stop_loss = self.position.qty, self.position.entry_price - self.atr * self.hp['grid_depth_atr'] * self.hp['levels']
            self.take_profit = self.position.qty, self.sma
        elif self.is_short:
            self.stop_loss = self.position.qty, self.position.entry_price + self.atr * self.hp['grid_depth_atr'] * self.hp['levels']
            self.take_profit = self.position.qty, self.sma

    def update_position(self):
        if self.is_long:
            self.take_profit = self.position.qty, self.sma
        elif self.is_short:
            self.take_profit = self.position.qty, self.sma

    def hyperparameters(self) -> list:
        return [
            {'name': 'sma_period', 'type': int, 'min': 20, 'max': 60, 'default': 30},
            {'name': 'threshold', 'type': float, 'min': 1.5, 'max': 3.5, 'step': 0.1, 'default': 2.0},
            {'name': 'levels', 'type': int, 'min': 2, 'max': 4, 'default': 3},
            {'name': 'grid_depth_atr', 'type': float, 'min': 0.5, 'max': 2.0, 'step': 0.1, 'default': 1.0},
            {'name': 'atr_period', 'type': int, 'min': 5, 'max': 30, 'default': 14},
            {'name': 'risk_percent', 'type': float, 'min': 0.5, 'max': 3.0, 'step': 0.1, 'default': 1.5},
        ]
