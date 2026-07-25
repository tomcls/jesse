from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class R2_RangeFadeAdx(Strategy):
    """
    Research Run #2. Range fading, ADX-gated. Only trades when ADX is low
    (confirmed non-trending / ranging regime) - fades the Donchian channel
    edges with LIMIT orders placed further out (offering better fills on a
    slight extension past the edge), exits at the channel midline (maker).
    Best config: ETH-USD 1h, dc_period=14, adx_max=30, limit_offset_pct=0.1
    -> 33 trades, Sharpe 0.708, DD -3.09%. Capped well under the 100-trade
    floor on ETH. Tried on SOL-USD (identical params: 104 trades almost
    exactly on target, but Sharpe -0.95 despite 61.5% win rate; widened
    stop improved it to -0.75/66% win rate but never turned positive) --
    SOL does not replicate this edge. ETH remains the only symbol where
    this mechanism shows real signal, and only at low frequency.
    """

    @property
    def donchian(self):
        return ta.donchian(self.candles, self.hp['dc_period'])

    @property
    def adx(self):
        return ta.adx(self.candles, self.hp['adx_period'])

    @property
    def atr(self):
        return ta.atr(self.candles, self.hp['atr_period'])

    def should_long(self) -> bool:
        return self.adx < self.hp['adx_max'] and self.price <= self.donchian.lowerband

    def should_short(self) -> bool:
        return self.adx < self.hp['adx_max'] and self.price >= self.donchian.upperband

    def should_cancel_entry(self) -> bool:
        return True

    def go_long(self):
        entry = self.price * (1 - self.hp['limit_offset_pct'] / 100)
        stop = entry - self.atr * self.hp['atr_mult']
        qty = utils.risk_to_qty(self.available_margin, self.hp['risk_percent'], entry, stop, fee_rate=self.fee_rate)
        self.buy = qty, entry
        self.stop_loss = qty, stop
        self.take_profit = qty, self.donchian.middleband

    def go_short(self):
        entry = self.price * (1 + self.hp['limit_offset_pct'] / 100)
        stop = entry + self.atr * self.hp['atr_mult']
        qty = utils.risk_to_qty(self.available_margin, self.hp['risk_percent'], entry, stop, fee_rate=self.fee_rate)
        self.sell = qty, entry
        self.stop_loss = qty, stop
        self.take_profit = qty, self.donchian.middleband

    def update_position(self):
        if self.is_long:
            self.take_profit = self.position.qty, self.donchian.middleband
        elif self.is_short:
            self.take_profit = self.position.qty, self.donchian.middleband

    def hyperparameters(self) -> list:
        return [
            {'name': 'dc_period', 'type': int, 'min': 8, 'max': 60, 'default': 14},
            {'name': 'adx_period', 'type': int, 'min': 7, 'max': 30, 'default': 14},
            {'name': 'adx_max', 'type': int, 'min': 12, 'max': 45, 'default': 30},
            {'name': 'limit_offset_pct', 'type': float, 'min': 0.02, 'max': 1.0, 'step': 0.02, 'default': 0.1},
            {'name': 'atr_period', 'type': int, 'min': 5, 'max': 30, 'default': 14},
            {'name': 'atr_mult', 'type': float, 'min': 1.5, 'max': 6.0, 'step': 0.1, 'default': 2.5},
            {'name': 'risk_percent', 'type': float, 'min': 0.5, 'max': 3.0, 'step': 0.1, 'default': 1.5},
        ]
