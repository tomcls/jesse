from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class DonchianBreakoutSimple(Strategy):
    """
    Plain Donchian channel breakout, no trend/volatility filters (unlike
    the original BreakoutDonchian stub, whose 3-way filter combination
    never triggered a single trade in 3.5 years). ATR trailing stop.
    """

    @property
    def donchian(self):
        return ta.donchian(self.candles, self.hp['period'])

    @property
    def atr(self):
        return ta.atr(self.candles, self.hp['atr_period'])

    def should_long(self) -> bool:
        # guard against a degenerate flat channel (upperband == lowerband),
        # which would otherwise make should_long/should_short true together
        return self.donchian.upperband > self.donchian.lowerband and self.price >= self.donchian.upperband

    def should_short(self) -> bool:
        return self.donchian.upperband > self.donchian.lowerband and self.price <= self.donchian.lowerband

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
        if self.is_long:
            self.stop_loss = self.position.qty, max(self.average_stop_loss, self.price - self.atr * self.hp['atr_mult'])
        elif self.is_short:
            self.stop_loss = self.position.qty, min(self.average_stop_loss, self.price + self.atr * self.hp['atr_mult'])

    def hyperparameters(self) -> list:
        return [
            {'name': 'period', 'type': int, 'min': 10, 'max': 55, 'default': 20},
            {'name': 'atr_period', 'type': int, 'min': 5, 'max': 30, 'default': 14},
            {'name': 'atr_mult', 'type': float, 'min': 1.0, 'max': 4.0, 'step': 0.1, 'default': 2.0},
            {'name': 'risk_percent', 'type': float, 'min': 0.5, 'max': 3.0, 'step': 0.1, 'default': 1.5},
        ]
