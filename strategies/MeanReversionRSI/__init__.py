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
        qty = utils.risk_to_qty(self.leveraged_available_margin, 10, entry_price, stop_loss_price, fee_rate=self.fee_rate)
        self.buy = qty, entry_price
    
    def go_short(self):
        entry_price = self.bb.upperband
        stop_loss_price = entry_price + (6 * self.atr)
        qty = utils.risk_to_qty(self.leveraged_available_margin, 10, entry_price, stop_loss_price, fee_rate=self.fee_rate)
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
    def after(self) -> None:
        # Add Bollinger Bands to main chart
        self.add_line_to_candle_chart('BB Upper', self.bb.upperband, color='blue')
        self.add_line_to_candle_chart('BB Lower', self.bb.lowerband, color='blue')
        self.add_line_to_candle_chart('BB Middle', self.bb.middleband, color='gray')

        # Add SuperTrend to main chart
        st_color = 'green' if self.trend == 1 else 'red'
        self.add_line_to_candle_chart('SuperTrend 4H', ta.supertrend(self.higher_tf_candles, period=10, factor=3).trend, color=st_color)

        # Add RSI to separate chart
        self.add_extra_line_chart('RSI 4H', 'RSI 4H', self.higher_tf_rsi)
        self.add_horizontal_line_to_extra_chart('RSI 4H', 'Overbought', 70, color='red')
        self.add_horizontal_line_to_extra_chart('RSI 4H', 'Oversold', 30, color='green')

        # Add ADX indicators to separate charts
        self.add_extra_line_chart('ADX HTF', 'ADX 4H', self.higher_tf_adx)
        self.add_horizontal_line_to_extra_chart('ADX HTF', 'ADX Min', 40, color='gray')

        self.add_extra_line_chart('ADX Current', 'ADX Current TF', self.current_tf_adx)
        self.add_horizontal_line_to_extra_chart('ADX Current', 'ADX Min', 20, color='gray')

        # Add ATR to separate chart for reference
        self.add_extra_line_chart('ATR', 'ATR', self.atr)    
    # def watch_list(self) -> list:
    #     return [
    #         ('RSI 4H', self.rsi_higher),
    #         ('Trend', self.trend),
    #         ('ADX', self.adx),
    #         ('ADX 4H', self.adx_higher),
    #         ('BB Upper', self.bb.upperband),
    #         ('BB Middle', self.bb.middleband),
    #         ('BB Lower', self.bb.lowerband),
    #         ('BBW', self.bbw * 100),
    #         ('ATR', self.atr),
    #         ('Long Signal', self.should_long()),
    #         ('Short Signal', self.should_short()),
    #     ]

    # def hyperparameters(self) -> list:
    #     return [
    #         {'name': 'rsi_period', 'type': int, 'min': 8, 'max': 21, 'default': 14},
    #         {'name': 'rsi_overbought', 'type': int, 'min': 60, 'max': 80, 'default': 70},
    #         {'name': 'rsi_oversold', 'type': int, 'min': 20, 'max': 40, 'default': 30},
    #         {'name': 'adx_min', 'type': int, 'min': 15, 'max': 30, 'default': 20},
    #         {'name': 'adx_higher_min', 'type': int, 'min': 30, 'max': 50, 'default': 40},
    #         {'name': 'bb_period', 'type': int, 'min': 14, 'max': 40, 'default': 20},
    #         {'name': 'sl_atr_mult', 'type': float, 'min': 3.0, 'max': 8.0, 'step': 0.5, 'default': 6.0},
    #         {'name': 'risk_pct', 'type': float, 'min': 1.0, 'max': 5.0, 'step': 0.5, 'default': 3.0},
    #         {'name': 'leverage', 'type': int, 'min': 1, 'max': 10, 'default': 1},
    #     ]

    # def dna(self) -> str:
     #   return "eyJhZHhfaGlnaGVyX21pbiI6IDQ5LCAiYWR4X21pbiI6IDIwLCAiYmJfcGVyaW9kIjogMzMsICJsZXZlcmFnZSI6IDMsICJyaXNrX3BjdCI6IDMuNSwgInJzaV9vdmVyYm91Z2h0IjogNjEsICJyc2lfb3ZlcnNvbGQiOiAyNywgInJzaV9wZXJpb2QiOiAxOSwgInNsX2F0cl9tdWx0IjogMy41fQ=="
        #default is better than the one above