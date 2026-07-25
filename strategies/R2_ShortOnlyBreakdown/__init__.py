from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class R2_ShortOnlyBreakdown(Strategy):
    """
    Research Run #2. Short-only structural breakdown. Enters short with a
    LIMIT order slightly above current price when price makes a new
    N-period Donchian low AND is below a longer-term trend SMA (confirms
    a genuine breakdown, not just a single-bar dip). No long side.
    Best config: SOL-USD 1h, entry_period=15, trend_period=45, offset=0.1
    -> 56 trades, Sharpe 0.40 (under the trade floor). Tried on ETH-USD
    (identical params): only 18 trades, weak Sharpe 0.16 -- ETH breaks
    down far less often than SOL in this window, confirming SOL is the
    right symbol for this mechanism (matches Research Run #1's
    observation that SOL is prone to structural downtrends).
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
        entry = self.price * (1 + self.hp['limit_offset_pct'] / 100)
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
            {'name': 'entry_period', 'type': int, 'min': 5, 'max': 60, 'default': 15},
            {'name': 'trend_period', 'type': int, 'min': 20, 'max': 150, 'default': 45},
            {'name': 'limit_offset_pct', 'type': float, 'min': 0.02, 'max': 0.8, 'step': 0.02, 'default': 0.1},
            {'name': 'atr_period', 'type': int, 'min': 5, 'max': 30, 'default': 14},
            {'name': 'atr_mult', 'type': float, 'min': 1.5, 'max': 5.0, 'step': 0.1, 'default': 2.5},
            {'name': 'risk_percent', 'type': float, 'min': 0.5, 'max': 3.0, 'step': 0.1, 'default': 1.5},
        ]
