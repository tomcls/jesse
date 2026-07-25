from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class R2_VolBreakoutRare(Strategy):
    """
    Research Run #2. Volatility breakout, rare/extreme trigger. Enters
    MARKET (must chase price - this family accepts taker fees by design)
    when price closes beyond N-period Donchian extreme AND ATR is at a
    multi-month high relative to its own rolling percentile-like average.
    ATR trailing stop lets winners run so few, large trades can carry the
    Sharpe despite taker fees on entry.
    """

    @property
    def donchian(self):
        return ta.donchian(self.candles, self.hp['period'])

    @property
    def atr(self):
        return ta.atr(self.candles, self.hp['atr_period'])

    @property
    def atr_sma(self):
        return ta.sma(ta.atr(self.candles, self.hp['atr_period'], sequential=True), self.hp['atr_sma_period'])

    def should_long(self) -> bool:
        return self.price >= self.donchian.upperband and self.atr > self.atr_sma * self.hp['vol_expansion_mult']

    def should_short(self) -> bool:
        return self.price <= self.donchian.lowerband and self.atr > self.atr_sma * self.hp['vol_expansion_mult']

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
            {'name': 'period', 'type': int, 'min': 5, 'max': 80, 'default': 5},
            {'name': 'atr_period', 'type': int, 'min': 5, 'max': 30, 'default': 14},
            {'name': 'atr_sma_period', 'type': int, 'min': 20, 'max': 100, 'default': 60},
            {'name': 'vol_expansion_mult', 'type': float, 'min': 0.7, 'max': 2.5, 'step': 0.02, 'default': 0.85},
            {'name': 'atr_mult', 'type': float, 'min': 1.5, 'max': 5.0, 'step': 0.1, 'default': 1.5},
            {'name': 'risk_percent', 'type': float, 'min': 0.5, 'max': 3.0, 'step': 0.1, 'default': 1.5},
        ]
