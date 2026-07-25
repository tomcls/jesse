from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils

class KAMA_TrendFollowing(Strategy):
    last_trade_index = 0  # Track the last index where a trade was executed

    @property
    def kama(self):
        return ta.kama(self.candles)

    @property
    def atr(self):
        return ta.atr(self.candles)

    @property
    def adx(self):
        return ta.adx(self.candles)

    @property
    def chop(self):
        return ta.chop(self.candles)

    @property
    def bb_width(self):
        # Use the built-in Bollinger Bands Width indicator
        return ta.bollinger_bands_width(self.candles)

    @property
    def long_term_candles(self):
        # Get candles for a larger timeframe (4h or 6h if current is 4h)
        big_tf = '4h'
        if self.timeframe == '4h':
            big_tf = '6h'
        return self.get_candles(self.exchange, self.symbol, big_tf)

    @property
    def long_term_kama(self):
        return ta.kama(self.long_term_candles)

    def should_long(self) -> bool:
        # Enter long if the price is above KAMA, ADX is above 50, long-term KAMA indicates an uptrend,
        # Choppiness Index is below 50, Bollinger Band width < 7, and at least 10 candles have passed since the last trade
        return (self.price > self.kama and
                self.adx > 50 and
                self.price > self.long_term_kama and
                self.chop < 50 and
                self.bb_width * 100 < 7 and
                self.index - self.last_trade_index >= 10)

    def should_short(self) -> bool:
        # Enter short if the price is below KAMA, ADX is above 50, long-term KAMA indicates a downtrend,
        # Choppiness Index is below 50, Bollinger Band width < 7, and at least 10 candles have passed since the last trade
        return (self.price < self.kama and
                self.adx > 50 and
                self.price < self.long_term_kama and
                self.chop < 50 and
                self.bb_width * 100 < 7 and
                self.index - self.last_trade_index >= 10)

    def go_long(self):
        entry_price = self.price
        stop_loss = entry_price - (self.atr * 2.5)
        qty = utils.risk_to_qty(self.available_margin, 3, entry_price, stop_loss, fee_rate=self.fee_rate)
        self.buy = qty, entry_price

    def go_short(self):
        entry_price = self.price
        stop_loss = entry_price + (self.atr * 2.5)
        qty = utils.risk_to_qty(self.available_margin, 3, entry_price, stop_loss, fee_rate=self.fee_rate)
        self.sell = qty, entry_price

    def on_open_position(self, order):
        if self.is_long:
            self.stop_loss = self.position.qty, self.price - (self.atr * 2.5)
            self.take_profit = self.position.qty, self.price + (self.atr * 2.5)
        elif self.is_short:
            self.stop_loss = self.position.qty, self.price + (self.atr * 2.5)
            self.take_profit = self.position.qty, self.price - (self.atr * 2.5)

    def on_close_position(self, order):
        # Update last trade index when a position is closed
        self.last_trade_index = self.index