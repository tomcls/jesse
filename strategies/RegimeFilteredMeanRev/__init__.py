from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class RegimeFilteredMeanRev(Strategy):
    """
    Mean reversion, regime-gated: only take RSI oversold/overbought
    reversion trades when ADX confirms the market is NOT trending
    (ranging regime). Directly addresses wave 1's finding that naked
    RSI reversion has no edge without a trend/regime filter.
    """

    @property
    def rsi(self):
        return ta.rsi(self.candles, self.hp['rsi_period'])

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
        if self.is_long and self.rsi > self.hp['exit_mid']:
            self.liquidate()
        if self.is_short and self.rsi < self.hp['exit_mid']:
            self.liquidate()

    def hyperparameters(self) -> list:
        return [
            {'name': 'rsi_period', 'type': int, 'min': 5, 'max': 30, 'default': 14},
            {'name': 'oversold', 'type': int, 'min': 10, 'max': 35, 'default': 25},
            {'name': 'overbought', 'type': int, 'min': 65, 'max': 90, 'default': 75},
            {'name': 'exit_mid', 'type': int, 'min': 45, 'max': 55, 'default': 50},
            {'name': 'adx_period', 'type': int, 'min': 7, 'max': 30, 'default': 14},
            {'name': 'adx_max', 'type': int, 'min': 15, 'max': 30, 'default': 20},
            {'name': 'atr_period', 'type': int, 'min': 5, 'max': 30, 'default': 14},
            {'name': 'atr_mult', 'type': float, 'min': 1.0, 'max': 4.0, 'step': 0.1, 'default': 2.0},
            {'name': 'risk_percent', 'type': float, 'min': 0.5, 'max': 3.0, 'step': 0.1, 'default': 1.5},
        ]
