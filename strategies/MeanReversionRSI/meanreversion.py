# please write a mean reversion strategy with below rules. Use the RSI on a bigger timeframe, specifically the 4h timeframe. 
# For long positions, the RSI must be above 70. For short positions, do the opposite.
# As for the trend, use the Super Trend indicator. Once it is displaying an uptrend, you want to go long. This should also use the bigger timeframe.
# For the ADX:
# - It needs to be above 40 on the bigger timeframe.
# - It needs to be above 20 on the current timeframe.
# For short positions, do the opposite.
# For entries, the entry price must be the lower band of the current bollinger_bands.
# Set the stop loss as the current price minus 6 times the current ATR values.
# Risk 3% of the account's capital per each trad.
# For take profit:
# - In long positions, close at the upperband of the current Bollinger Bands.
# - For short positions, take profit at the lowerband of the current Bollinger Bands.
# 1h leverage 5

from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class MeanReversionRSI(Strategy):
    @property
    def higher_tf_candles(self):
        return self.get_candles(self.exchange, self.symbol, '4h')
    
    @property
    def higher_tf_rsi(self):
        return ta.rsi(self.higher_tf_candles)
    
    @property
    def trend(self):
        s = ta.supertrend(self.higher_tf_candles)
        if self.price > s.trend:
            return 1
        else:
            return -1

    @property
    def higher_tf_adx(self):
        return ta.adx(self.higher_tf_candles)

    @property
    def current_tf_adx(self):
        return ta.adx(self.candles)
    
    
    
    @property
    def bb(self):
        return ta.bollinger_bands(self.candles)
    
    # @property
    # def bbw(self):
    #     return ta.bollinger_bands_width(self.candles, period=self.hp['bb_period'])
    
    @property
    def atr(self):
        return ta.atr(self.candles)
    
    def should_long(self) -> bool:
        return (
            self.higher_tf_rsi > 70 and 
            self.trend == 1 and 
            self.higher_tf_adx > 40 and 
            self.current_tf_adx > 20 
        )
    
    def should_short(self) -> bool:
        return (
            self.higher_tf_rsi < 30 and 
            self.trend == -1 and 
            self.higher_tf_adx > 40 and 
            self.current_tf_adx > 20 
        )
    
    def go_long(self):
        entry_price = self.bb.lowerband
        stop_loss_price = entry_price - (6 * self.atr)
        qty = utils.risk_to_qty(self.available_margin, 10, entry_price, stop_loss_price, fee_rate=self.fee_rate)
        self.buy = qty, entry_price
    
    def go_short(self):
        entry_price = self.bb.upperband
        stop_loss_price = entry_price + (6 * self.atr)
        qty = utils.risk_to_qty(self.available_margin, 10, entry_price, stop_loss_price, fee_rate=self.fee_rate)
        self.sell = qty, entry_price
    
    def on_open_position(self, order):
        if self.is_long:
            self.stop_loss = self.position.qty, self.position.entry_price - (6 * self.atr)
            self.take_profit = self.position.qty, self.bb.upperband
        elif self.is_short:
            self.stop_loss = self.position.qty, self.position.entry_price + (6 * self.atr)
            self.take_profit = self.position.qty, self.bb.lowerband
    
    def should_cancel_entry(self) -> bool:
        return True
        
   

    # def dna(self) -> str:
     #   return "eyJhZHhfaGlnaGVyX21pbiI6IDQ5LCAiYWR4X21pbiI6IDIwLCAiYmJfcGVyaW9kIjogMzMsICJsZXZlcmFnZSI6IDMsICJyaXNrX3BjdCI6IDMuNSwgInJzaV9vdmVyYm91Z2h0IjogNjEsICJyc2lfb3ZlcnNvbGQiOiAyNywgInJzaV9wZXJpb2QiOiAxOSwgInNsX2F0cl9tdWx0IjogMy41fQ=="
        #default is better than the one above