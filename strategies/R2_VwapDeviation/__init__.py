from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class R2_VwapDeviation(Strategy):
    """
    Research Run #2. Daily-anchored VWAP deviation fade. Round 1 (dev
    3.0 ATR, adx<30): 70t, Sharpe -1.17 -- deep VWAP stretches in crypto
    CONTINUE rather than revert (fat tails). Round 2: moderate deviation
    (1.8 ATR) + tighter regime gate (adx<22) to catch routine
    oscillations instead of crash legs.
    """

    @property
    def vwap(self):
        return ta.vwap(self.candles, anchor='D')

    @property
    def adx(self):
        return ta.adx(self.candles, self.hp['adx_period'])

    @property
    def atr(self):
        return ta.atr(self.candles, self.hp['atr_period'])

    def should_long(self) -> bool:
        return (self.price < self.vwap - self.hp['dev_atr'] * self.atr
                and self.adx < self.hp['adx_max'])

    def should_short(self) -> bool:
        return (self.price > self.vwap + self.hp['dev_atr'] * self.atr
                and self.adx < self.hp['adx_max'])

    def should_cancel_entry(self) -> bool:
        return True

    def go_long(self):
        entry = self.price * (1 - self.hp['limit_offset_pct'] / 100)
        stop = entry - self.atr * self.hp['atr_mult']
        qty = utils.risk_to_qty(self.available_margin, self.hp['risk_percent'], entry, stop, fee_rate=self.fee_rate)
        self.buy = qty, entry
        self.stop_loss = qty, stop

    def go_short(self):
        entry = self.price * (1 + self.hp['limit_offset_pct'] / 100)
        stop = entry + self.atr * self.hp['atr_mult']
        qty = utils.risk_to_qty(self.available_margin, self.hp['risk_percent'], entry, stop, fee_rate=self.fee_rate)
        self.sell = qty, entry
        self.stop_loss = qty, stop

    def update_position(self):
        if self.is_long and self.price >= self.vwap:
            self.liquidate()
        elif self.is_short and self.price <= self.vwap:
            self.liquidate()

    def hyperparameters(self) -> list:
        return [
            {'name': 'dev_atr', 'type': float, 'min': 1.0, 'max': 6.0, 'step': 0.1, 'default': 1.8},
            {'name': 'adx_period', 'type': int, 'min': 7, 'max': 30, 'default': 14},
            {'name': 'adx_max', 'type': int, 'min': 12, 'max': 45, 'default': 22},
            {'name': 'limit_offset_pct', 'type': float, 'min': 0.02, 'max': 1.0, 'step': 0.02, 'default': 0.1},
            {'name': 'atr_period', 'type': int, 'min': 5, 'max': 30, 'default': 14},
            {'name': 'atr_mult', 'type': float, 'min': 1.5, 'max': 5.0, 'step': 0.1, 'default': 2.5},
            {'name': 'risk_percent', 'type': float, 'min': 0.5, 'max': 3.0, 'step': 0.1, 'default': 1.5},
        ]
