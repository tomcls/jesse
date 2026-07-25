from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class R2_KeltnerLongOnlySelective(Strategy):
    """
    Research Run #2. Long-only variant of the run's best mechanism
    (R2_KeltnerBreakoutSelective, 4h ETH, Sharpe 1.3956 at 102 trades).
    Round 1 (period=18/mult=2.0/vol=1.05): 68 trades, Sharpe 1.3499.
    Round 2 (period=14/mult=1.7/vol=1.0): 87 trades, Sharpe 1.2685.
    Loosening slightly more to cross the 100 floor.
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
        return False

    def should_cancel_entry(self) -> bool:
        return True

    def go_long(self):
        entry = self.price
        stop = entry - self.atr * self.hp['atr_mult']
        qty = utils.risk_to_qty(self.available_margin, self.hp['risk_percent'], entry, stop, fee_rate=self.fee_rate)
        self.buy = qty, entry
        self.stop_loss = qty, stop

    def go_short(self):
        pass

    def update_position(self):
        if self.is_long and self.price <= self.kc.middleband:
            self.liquidate()

    def hyperparameters(self) -> list:
        return [
            {'name': 'period', 'type': int, 'min': 8, 'max': 100, 'default': 12},
            {'name': 'mult', 'type': float, 'min': 1.0, 'max': 5.0, 'step': 0.1, 'default': 1.5},
            {'name': 'atr_period', 'type': int, 'min': 5, 'max': 30, 'default': 14},
            {'name': 'atr_sma_period', 'type': int, 'min': 10, 'max': 50, 'default': 20},
            {'name': 'vol_expansion_mult', 'type': float, 'min': 0.8, 'max': 2.0, 'step': 0.05, 'default': 0.95},
            {'name': 'atr_mult', 'type': float, 'min': 1.0, 'max': 4.0, 'step': 0.1, 'default': 1.5},
            {'name': 'risk_percent', 'type': float, 'min': 0.5, 'max': 3.0, 'step': 0.1, 'default': 1.5},
        ]
