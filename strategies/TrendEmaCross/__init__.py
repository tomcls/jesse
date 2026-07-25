from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class TrendEmaCross(Strategy):
    """
    Trend following: EMA(fast)/EMA(slow) crossover on the trading timeframe.
    Enters on crossover, ATR-based stop-loss, exits on opposite crossover.
    """

    @property
    def fast_ema(self):
        return ta.ema(self.candles, self.hp['fast_period'])

    @property
    def slow_ema(self):
        return ta.ema(self.candles, self.hp['slow_period'])

    @property
    def atr(self):
        return ta.atr(self.candles, self.hp['atr_period'])

    def should_long(self) -> bool:
        return self.fast_ema > self.slow_ema

    def should_short(self) -> bool:
        return self.fast_ema < self.slow_ema

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
        if self.is_long and self.fast_ema < self.slow_ema:
            self.liquidate()
        if self.is_short and self.fast_ema > self.slow_ema:
            self.liquidate()

    def hyperparameters(self) -> list:
        return [
            {'name': 'fast_period', 'type': int, 'min': 5, 'max': 30, 'default': 9},
            {'name': 'slow_period', 'type': int, 'min': 20, 'max': 80, 'default': 21},
            {'name': 'atr_period', 'type': int, 'min': 5, 'max': 30, 'default': 14},
            {'name': 'atr_mult', 'type': float, 'min': 1.0, 'max': 5.0, 'step': 0.1, 'default': 2.5},
            {'name': 'risk_percent', 'type': float, 'min': 0.5, 'max': 3.0, 'step': 0.1, 'default': 1.5},
        ]
