from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class R2_ShortOnlyRallyFade(Strategy):
    """
    Research Run #2. Short-only, structural-downtrend rally fade. Only
    shorts: requires price below a long-term SMA (downtrend regime
    confirmed) AND RSI reaching an overbought extreme (a sharp relief
    rally within the downtrend) - fades the rally with a LIMIT sell
    placed above current price, take-profit back at the short-term SMA.
    No long side at all, per the brief's short-only suggestion for
    structurally weak alts.
    """

    @property
    def trend_sma(self):
        return ta.sma(self.candles, self.hp['trend_period'])

    @property
    def fast_sma(self):
        return ta.sma(self.candles, self.hp['fast_period'])

    @property
    def rsi(self):
        return ta.rsi(self.candles, self.hp['rsi_period'])

    @property
    def atr(self):
        return ta.atr(self.candles, self.hp['atr_period'])

    def should_long(self) -> bool:
        return False

    def should_short(self) -> bool:
        return self.price < self.trend_sma and self.rsi > self.hp['overbought']

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
        self.take_profit = qty, self.fast_sma

    def update_position(self):
        if self.is_short:
            self.take_profit = self.position.qty, self.fast_sma
            if self.price > self.trend_sma:
                self.liquidate()

    def hyperparameters(self) -> list:
        return [
            {'name': 'trend_period', 'type': int, 'min': 20, 'max': 200, 'default': 30},
            {'name': 'fast_period', 'type': int, 'min': 10, 'max': 40, 'default': 20},
            {'name': 'rsi_period', 'type': int, 'min': 5, 'max': 21, 'default': 14},
            {'name': 'overbought', 'type': int, 'min': 50, 'max': 85, 'default': 55},
            {'name': 'limit_offset_pct', 'type': float, 'min': 0.05, 'max': 0.8, 'step': 0.05, 'default': 0.15},
            {'name': 'atr_period', 'type': int, 'min': 5, 'max': 30, 'default': 14},
            {'name': 'atr_mult', 'type': float, 'min': 1.5, 'max': 5.0, 'step': 0.1, 'default': 2.5},
            {'name': 'risk_percent', 'type': float, 'min': 0.5, 'max': 3.0, 'step': 0.1, 'default': 1.5},
        ]
