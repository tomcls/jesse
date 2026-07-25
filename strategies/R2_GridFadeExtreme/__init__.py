from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class R2_GridFadeExtreme(Strategy):
    """
    Research Run #2, redesigned with an ADX regime filter (the lever that
    worked for R2_RangeFadeAdx and R2_PairsRatioZscore). Grid/multi-entry
    mean reversion, all limit orders, RSI-triggered ladder into extension
    during a confirmed non-trending regime, single take-profit at the SMA,
    single hard ATR stop. Round 1 (oversold=22/overbought=78/adx_max=25):
    only 12 trades, Sharpe -0.28. Loosening RSI thresholds and regime
    filter this round.
    """

    @property
    def rsi(self):
        return ta.rsi(self.candles, self.hp['rsi_period'])

    @property
    def sma(self):
        return ta.sma(self.candles, self.hp['sma_period'])

    @property
    def adx(self):
        return ta.adx(self.candles, self.hp['adx_period'])

    @property
    def atr(self):
        return ta.atr(self.candles, self.hp['atr_period'])

    def should_long(self) -> bool:
        return self.rsi < self.hp['oversold'] and self.adx < self.hp['adx_max']

    def should_short(self) -> bool:
        return self.rsi > self.hp['overbought'] and self.adx < self.hp['adx_max']

    def should_cancel_entry(self) -> bool:
        return True

    def _grid_qty(self, entry, stop):
        total_qty = utils.risk_to_qty(self.available_margin, self.hp['risk_percent'], entry, stop, fee_rate=self.fee_rate)
        return total_qty / self.hp['levels']

    def go_long(self):
        entry = self.price
        stop = entry - self.atr * self.hp['grid_depth_atr'] * self.hp['levels']
        qty = self._grid_qty(entry, stop)
        self.buy = [(qty, entry - i * self.hp['grid_depth_atr'] * self.atr) for i in range(1, self.hp['levels'] + 1)]

    def go_short(self):
        entry = self.price
        stop = entry + self.atr * self.hp['grid_depth_atr'] * self.hp['levels']
        qty = self._grid_qty(entry, stop)
        self.sell = [(qty, entry + i * self.hp['grid_depth_atr'] * self.atr) for i in range(1, self.hp['levels'] + 1)]

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
            {'name': 'rsi_period', 'type': int, 'min': 5, 'max': 21, 'default': 14},
            {'name': 'oversold', 'type': int, 'min': 5, 'max': 25, 'default': 32},
            {'name': 'overbought', 'type': int, 'min': 75, 'max': 95, 'default': 68},
            {'name': 'sma_period', 'type': int, 'min': 20, 'max': 100, 'default': 50},
            {'name': 'adx_period', 'type': int, 'min': 7, 'max': 30, 'default': 14},
            {'name': 'adx_max', 'type': int, 'min': 12, 'max': 45, 'default': 30},
            {'name': 'levels', 'type': int, 'min': 2, 'max': 4, 'default': 3},
            {'name': 'grid_depth_atr', 'type': float, 'min': 0.5, 'max': 2.5, 'step': 0.1, 'default': 1.2},
            {'name': 'atr_period', 'type': int, 'min': 5, 'max': 30, 'default': 14},
            {'name': 'risk_percent', 'type': float, 'min': 0.5, 'max': 3.0, 'step': 0.1, 'default': 1.5},
        ]
