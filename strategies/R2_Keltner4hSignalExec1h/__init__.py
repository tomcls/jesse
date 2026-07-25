from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class R2_Keltner4hSignalExec1h(Strategy):
    """
    Research Run #2. 4h Keltner signal executed on 1h (Tom's idea).
    Round 1 (raw intrabar): 143t/1.2306 vs 4h-native 118t/1.5004 --
    intrabar entries catch shallow pokes that reverse before the 4h
    close; the close-confirmation is part of the signal. Round 2: add a
    breakout BUFFER -- price must exceed the band by buffer_pct to
    trigger intrabar (filters shallow pokes while keeping the early-
    entry benefit on strong breaks).
    Requires a 4h data_route on the same exchange/symbol.
    """

    @property
    def c4(self):
        return self.get_candles(self.exchange, self.symbol, '4h')

    @property
    def kc_long(self):
        return ta.keltner(self.c4, self.hp['period'], self.hp['long_mult'])

    @property
    def kc_short(self):
        return ta.keltner(self.c4, self.hp['period'], self.hp['short_mult'])

    @property
    def atr4(self):
        return ta.atr(self.c4, self.hp['atr_period'])

    @property
    def atr_sma4(self):
        return ta.sma(ta.atr(self.c4, self.hp['atr_period'], sequential=True), self.hp['atr_sma_period'])

    @property
    def vol_ok(self):
        return self.atr4 > self.atr_sma4 * self.hp['vol_expansion_mult']

    def should_long(self) -> bool:
        buf = 1 + self.hp['buffer_pct'] / 100
        return self.price > self.kc_long.upperband * buf and self.vol_ok

    def should_short(self) -> bool:
        buf = 1 - self.hp['buffer_pct'] / 100
        return self.price < self.kc_short.lowerband * buf and self.vol_ok

    def should_cancel_entry(self) -> bool:
        return True

    def go_long(self):
        entry = self.price
        stop = entry - self.atr4 * self.hp['atr_mult']
        qty = utils.risk_to_qty(self.available_margin, self.hp['risk_percent'], entry, stop, fee_rate=self.fee_rate)
        self.buy = qty, entry
        self.stop_loss = qty, stop

    def go_short(self):
        entry = self.price
        stop = entry + self.atr4 * self.hp['atr_mult']
        qty = utils.risk_to_qty(self.available_margin, self.hp['risk_percent'], entry, stop, fee_rate=self.fee_rate)
        self.sell = qty, entry
        self.stop_loss = qty, stop

    def update_position(self):
        if self.is_long and self.price <= self.kc_long.middleband:
            self.liquidate()
        if self.is_short and self.price >= self.kc_short.middleband:
            self.liquidate()

    def hyperparameters(self) -> list:
        return [
            {'name': 'period', 'type': int, 'min': 10, 'max': 100, 'default': 25},
            {'name': 'long_mult', 'type': float, 'min': 1.0, 'max': 5.0, 'step': 0.1, 'default': 2.1},
            {'name': 'short_mult', 'type': float, 'min': 1.0, 'max': 6.0, 'step': 0.1, 'default': 2.8},
            {'name': 'buffer_pct', 'type': float, 'min': 0.0, 'max': 2.0, 'step': 0.1, 'default': 0.4},
            {'name': 'atr_period', 'type': int, 'min': 5, 'max': 30, 'default': 14},
            {'name': 'atr_sma_period', 'type': int, 'min': 10, 'max': 50, 'default': 20},
            {'name': 'vol_expansion_mult', 'type': float, 'min': 0.8, 'max': 2.0, 'step': 0.05, 'default': 1.0},
            {'name': 'atr_mult', 'type': float, 'min': 1.0, 'max': 4.0, 'step': 0.1, 'default': 1.35},
            {'name': 'risk_percent', 'type': float, 'min': 0.5, 'max': 3.0, 'step': 0.1, 'default': 1.5},
        ]
