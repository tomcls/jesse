from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class R2_BTCTrendFollow(Strategy):
    """
    Research Run #2. Pure trend-following (not breakout), designed for
    BTC specifically since every mechanism reused from ETH has
    underperformed on BTC regardless of re-tuning. Wide EMA cross + ADX
    confirmation + ATR trailing stop. Round 2 (fast=55/slow=160/adx=30):
    171 trades (just over ceiling), Sharpe 0.5844, DD -24.7%. Nudging
    slightly wider to land in range.
    """

    @property
    def ema_fast(self):
        return ta.ema(self.candles, self.hp['fast_period'])

    @property
    def ema_slow(self):
        return ta.ema(self.candles, self.hp['slow_period'])

    @property
    def adx(self):
        return ta.adx(self.candles, self.hp['adx_period'])

    @property
    def atr(self):
        return ta.atr(self.candles, self.hp['atr_period'])

    def should_long(self) -> bool:
        return self.ema_fast > self.ema_slow and self.adx > self.hp['adx_min']

    def should_short(self) -> bool:
        return self.ema_fast < self.ema_slow and self.adx > self.hp['adx_min']

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
            if self.ema_fast < self.ema_slow:
                self.liquidate()
        elif self.is_short:
            self.stop_loss = self.position.qty, min(self.average_stop_loss, self.price + self.atr * self.hp['atr_mult'])
            if self.ema_fast > self.ema_slow:
                self.liquidate()

    def hyperparameters(self) -> list:
        return [
            {'name': 'fast_period', 'type': int, 'min': 10, 'max': 100, 'default': 58},
            {'name': 'slow_period', 'type': int, 'min': 30, 'max': 250, 'default': 175},
            {'name': 'adx_period', 'type': int, 'min': 7, 'max': 30, 'default': 14},
            {'name': 'adx_min', 'type': int, 'min': 15, 'max': 45, 'default': 32},
            {'name': 'atr_period', 'type': int, 'min': 5, 'max': 30, 'default': 14},
            {'name': 'atr_mult', 'type': float, 'min': 1.5, 'max': 5.0, 'step': 0.1, 'default': 3.0},
            {'name': 'risk_percent', 'type': float, 'min': 0.5, 'max': 3.0, 'step': 0.1, 'default': 1.5},
        ]
