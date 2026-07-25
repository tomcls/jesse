from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class R2_KeltnerBreakoutSelectiveTrail(Strategy):
    """
    Research Run #2. Same entry mechanism as R2_KeltnerBreakoutSelective's
    best (stable) 4h ETH config -- wide Keltner channel + volatility-
    expansion gate -- but with an ATR trailing stop instead of exit-at-
    midline, to test whether letting winners run further pushes Sharpe
    past 1.5 without needing to touch the entry frequency (which is
    already in-range and stable at the parent's settings).
    """

    @property
    def kc(self):
        return ta.keltner(self.candles, self.hp['period'], self.hp['mult'])

    @property
    def atr(self):
        return ta.atr(self.candles, self.hp['atr_period'])

    @property
    def atr_sma(self):
        return ta.sma(ta.atr(self.candles, self.hp['atr_period'], sequential=True), self.hp['atr_sma_period'])

    def should_long(self) -> bool:
        return self.price > self.kc.upperband and self.atr > self.atr_sma * self.hp['vol_expansion_mult']

    def should_short(self) -> bool:
        return self.price < self.kc.lowerband and self.atr > self.atr_sma * self.hp['vol_expansion_mult']

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
            {'name': 'period', 'type': int, 'min': 10, 'max': 100, 'default': 25},
            {'name': 'mult', 'type': float, 'min': 1.0, 'max': 5.0, 'step': 0.1, 'default': 2.6},
            {'name': 'atr_period', 'type': int, 'min': 5, 'max': 30, 'default': 14},
            {'name': 'atr_sma_period', 'type': int, 'min': 10, 'max': 50, 'default': 20},
            {'name': 'vol_expansion_mult', 'type': float, 'min': 0.8, 'max': 2.0, 'step': 0.05, 'default': 1.1},
            {'name': 'atr_mult', 'type': float, 'min': 1.0, 'max': 4.0, 'step': 0.1, 'default': 1.5},
            {'name': 'risk_percent', 'type': float, 'min': 0.5, 'max': 3.0, 'step': 0.1, 'default': 1.5},
        ]
