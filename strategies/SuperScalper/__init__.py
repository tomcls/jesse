from jesse.strategies import Strategy, cached
import jesse.indicators as ta
from jesse import utils


class SuperScalper(Strategy):
    @property
    def long_term_candles(self):
        return self.get_candles(self.exchange, self.symbol, '4h')

    @property
    def long_term_ma(self):
        if self.price > ta.ema(self.long_term_candles, self.hp['long_term_ma_period']):
            return 1
        else:
            return -1

    @property
    def small_trend(self):
        t = ta.supertrend(self.candles)
        if self.price > t.trend:
            return 1
        else:
            return -1

    @property
    def big_trend(self):
        t = ta.supertrend(self.long_term_candles)
        if self.price > t.trend:
            return 1
        else:
            return -1

    @property
    def adx(self):
        return ta.adx(self.candles) > self.hp['adx_threshold']

    def should_long(self) -> bool:
        return self.small_trend == 1 and self.big_trend == 1 and self.adx and self.long_term_ma == 1

    def go_long(self):
        entry = self.price
        stop = self.price - ta.atr(self.candles) * 2.5
        qty = utils.risk_to_qty(self.available_margin, 3, entry, stop, fee_rate=self.fee_rate)
        self.buy = qty, self.price

    def should_short(self) -> bool:
        return self.small_trend == -1 and self.big_trend == -1 and self.adx and self.long_term_ma == -1

    def go_short(self):
        entry = self.price
        stop = self.price + ta.atr(self.candles) * self.hp['stop_loss']
        qty = utils.risk_to_qty(self.available_margin, 3, entry, stop, fee_rate=self.fee_rate)
        self.sell = qty, self.price

    def on_open_position(self, order) -> None:
        if self.is_long:
            self.take_profit = self.position.qty, self.price + ta.atr(self.candles) * self.hp['take_profit']
            self.stop_loss = self.position.qty, self.price - ta.atr(self.candles) * self.hp['stop_loss']
        elif self.is_short:
            self.take_profit = self.position.qty, self.price - ta.atr(self.candles) * self.hp['take_profit']
            self.stop_loss = self.position.qty, self.price + ta.atr(self.candles) * self.hp['stop_loss']

    def should_cancel_entry(self) -> bool:
        return True

    def hyperparameters(self) -> list:
        return [
            {'name': 'stop_loss', 'type': float, 'min': 1, 'max': 5, 'default': 2.5},
            {'name': 'take_profit', 'type': float, 'min': 1, 'max': 5, 'default': 3.2},
            {'name': 'adx_threshold', 'type': int, 'min': 1, 'max': 50, 'default': 30},
            {'name': 'long_term_ma_period', 'type': int, 'min': 100, 'max': 200, 'default': 200},
        ]

    def dna(self) -> str:
         # return 'CSw.'
         # return 'CMw.'
        return 'CVw1'
    
    def watch_list(self) -> list:
        return [
            ('long_term_ma', self.long_term_ma),
            ('small_trend', self.small_trend),
            ('big_trend', self.big_trend),
            ('adx', self.adx),
        ]