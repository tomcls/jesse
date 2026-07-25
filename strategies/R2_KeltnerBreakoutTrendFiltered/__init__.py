from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class R2_KeltnerBreakoutTrendFiltered(Strategy):
    """
    Research Run #2. This run's best candidate (R2_KeltnerBreakoutSelective,
    4h ETH, 102 trades, Sharpe 1.3956) plus a 1D anchor-timeframe EMA
    trend filter: only take longs when the 1D trend is up, only take
    shorts when the 1D trend is down. Tests whether higher-timeframe trend
    confluence can push this mechanism past the 1.5 Sharpe bar -- flagged
    as unexplored in both this run's and Research Run #1's summaries.
    Requires a 1D data_route on the same exchange/symbol.
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

    @property
    def anchor_candles(self):
        return self.get_candles(self.exchange, self.symbol, '1D')

    @property
    def anchor_trend_up(self):
        fast = ta.ema(self.anchor_candles, self.hp['anchor_fast'])
        slow = ta.ema(self.anchor_candles, self.hp['anchor_slow'])
        return fast > slow

    def should_long(self) -> bool:
        return (self.price > self.kc.upperband
                and self.atr > self.atr_sma * self.hp['vol_expansion_mult']
                and self.anchor_trend_up)

    def should_short(self) -> bool:
        return (self.price < self.kc.lowerband
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
        if self.is_long and self.price <= self.kc.middleband:
            self.liquidate()
        if self.is_short and self.price >= self.kc.middleband:
            self.liquidate()

    def hyperparameters(self) -> list:
        return [
            {'name': 'period', 'type': int, 'min': 10, 'max': 100, 'default': 25},
            {'name': 'mult', 'type': float, 'min': 1.0, 'max': 5.0, 'step': 0.1, 'default': 2.6},
            {'name': 'atr_period', 'type': int, 'min': 5, 'max': 30, 'default': 14},
            {'name': 'atr_sma_period', 'type': int, 'min': 10, 'max': 50, 'default': 20},
            {'name': 'vol_expansion_mult', 'type': float, 'min': 0.8, 'max': 2.0, 'step': 0.05, 'default': 1.1},
            {'name': 'atr_mult', 'type': float, 'min': 1.0, 'max': 4.0, 'step': 0.1, 'default': 1.5},
            {'name': 'anchor_fast', 'type': int, 'min': 3, 'max': 20, 'default': 8},
            {'name': 'anchor_slow', 'type': int, 'min': 10, 'max': 50, 'default': 21},
            {'name': 'risk_percent', 'type': float, 'min': 0.5, 'max': 3.0, 'step': 0.1, 'default': 1.5},
        ]
