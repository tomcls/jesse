from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class R2_VolBreakoutTrendFiltered(Strategy):
    """
    Research Run #2. Same mechanism as R2_VolBreakoutRare's best config
    (Donchian extreme + ATR volatility-expansion gate, MARKET entry, ATR
    trailing stop) plus a 4h anchor-timeframe EMA trend filter: only take
    longs when the 4h trend is up, only take shorts when the 4h trend is
    down. Round 1 (period=5, same as unfiltered R2_VolBreakoutRare): 56
    trades (roughly half of the unfiltered 120), Sharpe 0.5337 (comparable
    to unfiltered's 0.5034) but DD improved a lot (-8.03% vs -16.31%).
    Loosening the base Donchian period this round to compensate for the
    trend filter's trade-count reduction while keeping the DD/quality
    improvement.
    Requires a 4h data_route on the same exchange/symbol.
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

    @property
    def anchor_candles(self):
        return self.get_candles(self.exchange, self.symbol, '4h')

    @property
    def anchor_trend_up(self):
        fast = ta.ema(self.anchor_candles, self.hp['anchor_fast'])
        slow = ta.ema(self.anchor_candles, self.hp['anchor_slow'])
        return fast > slow

    def should_long(self) -> bool:
        return (self.price >= self.donchian.upperband
                and self.atr > self.atr_sma * self.hp['vol_expansion_mult']
                and self.anchor_trend_up)

    def should_short(self) -> bool:
        return (self.price <= self.donchian.lowerband
                and self.atr > self.atr_sma * self.hp['vol_expansion_mult']
                and not self.anchor_trend_up)

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
            {'name': 'period', 'type': int, 'min': 3, 'max': 80, 'default': 3},
            {'name': 'atr_period', 'type': int, 'min': 5, 'max': 30, 'default': 14},
            {'name': 'atr_sma_period', 'type': int, 'min': 20, 'max': 100, 'default': 60},
            {'name': 'vol_expansion_mult', 'type': float, 'min': 0.6, 'max': 2.5, 'step': 0.02, 'default': 0.75},
            {'name': 'atr_mult', 'type': float, 'min': 1.5, 'max': 5.0, 'step': 0.1, 'default': 2.0},
            {'name': 'anchor_fast', 'type': int, 'min': 5, 'max': 30, 'default': 10},
            {'name': 'anchor_slow', 'type': int, 'min': 15, 'max': 60, 'default': 30},
            {'name': 'risk_percent', 'type': float, 'min': 0.5, 'max': 3.0, 'step': 0.1, 'default': 1.5},
        ]
