from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class MomentumWillrExtreme(Strategy):
    """
    Mean-reversion momentum: enter when Williams %R reaches an extreme
    (oversold/overbought) reading, exit when it reverts past the midline.
    """

    @property
    def willr(self):
        return ta.willr(self.candles, self.hp['period'])

    @property
    def atr(self):
        return ta.atr(self.candles, self.hp['atr_period'])

    def should_long(self) -> bool:
        return self.willr < self.hp['oversold']

    def should_short(self) -> bool:
        return self.willr > self.hp['overbought']

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
        if self.is_long and self.willr > self.hp['exit_mid']:
            self.liquidate()
        if self.is_short and self.willr < self.hp['exit_mid']:
            self.liquidate()

    def hyperparameters(self) -> list:
        return [
            {'name': 'period', 'type': int, 'min': 5, 'max': 30, 'default': 14},
            {'name': 'oversold', 'type': int, 'min': -95, 'max': -70, 'default': -85},
            {'name': 'overbought', 'type': int, 'min': -30, 'max': -5, 'default': -15},
            {'name': 'exit_mid', 'type': int, 'min': -60, 'max': -40, 'default': -50},
            {'name': 'atr_period', 'type': int, 'min': 5, 'max': 30, 'default': 14},
            {'name': 'atr_mult', 'type': float, 'min': 1.0, 'max': 4.0, 'step': 0.1, 'default': 2.0},
            {'name': 'risk_percent', 'type': float, 'min': 0.5, 'max': 3.0, 'step': 0.1, 'default': 1.5},
        ]
