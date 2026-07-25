from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class ShortOnlyBreakdown(Strategy):
    """
    Short-only breakdown: enter short when price makes a new N-period
    low AND is below a longer-term moving average (confirms downtrend
    regime, not just a single-bar dip). ATR trailing stop, no long side
    - for a volatile alt where the data may justify a short bias.
    """

    @property
    def donchian(self):
        return ta.donchian(self.candles, self.hp['entry_period'])

    @property
    def trend_sma(self):
        return ta.sma(self.candles, self.hp['trend_period'])

    @property
    def atr(self):
        return ta.atr(self.candles, self.hp['atr_period'])

    def should_long(self) -> bool:
        return False

    def should_short(self) -> bool:
        return self.price <= self.donchian.lowerband and self.price < self.trend_sma

    def should_cancel_entry(self) -> bool:
        return True

    def go_long(self):
        pass

    def go_short(self):
        entry = self.price
        stop = entry + self.atr * self.hp['atr_mult']
        qty = utils.risk_to_qty(self.available_margin, self.hp['risk_percent'], entry, stop, fee_rate=self.fee_rate)
        self.sell = qty, entry
        self.stop_loss = qty, stop

    def update_position(self):
        if self.is_short:
            self.stop_loss = self.position.qty, min(self.average_stop_loss, self.price + self.atr * self.hp['atr_mult'])
            if self.price > self.trend_sma:
                self.liquidate()

    def hyperparameters(self) -> list:
        return [
            {'name': 'entry_period', 'type': int, 'min': 10, 'max': 40, 'default': 20},
            {'name': 'trend_period', 'type': int, 'min': 30, 'max': 100, 'default': 50},
            {'name': 'atr_period', 'type': int, 'min': 5, 'max': 30, 'default': 14},
            {'name': 'atr_mult', 'type': float, 'min': 1.0, 'max': 4.0, 'step': 0.1, 'default': 2.5},
            {'name': 'risk_percent', 'type': float, 'min': 0.5, 'max': 3.0, 'step': 0.1, 'default': 1.5},
        ]
