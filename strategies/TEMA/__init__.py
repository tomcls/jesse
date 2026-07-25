
# Write a trend-following strategy:
# The short-term trend must be 1, representing and uptrend. To determine this, use the TEMA indicator with a period of 10, which should be above the TEMA with a period of 80. If it is vice versa, the trend is down.
# For the long-term trend, use the same indicator but with periods of 20 and 70. except to use the 4h timeframe.
# For volatility filter, use the ADX indicator. Its value must be above 40 to take any trades.
# Also, use the Chande Momentum Indicator as an oscillator. For long trades, its value must be above 40.
# For short trades, do the exact opposite of the above conditions.
# For position sizing, risk 3% of the available margin per trade.
# For the entry price of the trades, use a limit order 1 ATR below the entry price.
# For the stop loss, use 4 times the current ATR below the entry price.
# For exiting the trade, the stop loss must be as described above, and the take profit must be 3 times the ATR indicator.

# i need to add value for the charts so i can debug the strategy

# works fine for 30min/4h timeframe

from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class TEMA(Strategy):
    @property
    def candles_4h(self):
        # Get 4-hour candles for long-term trend analysis
        return self.get_candles(self.exchange, self.symbol, '4h')
    
    @property
    def short_term_trend(self):
        # Determine short-term trend using TEMA crossover
        # TEMA 10 above TEMA 80 indicates uptrend (1)
        # TEMA 10 below TEMA 80 indicates downtrend (-1)
        tema_10 = ta.tema(self.candles, 10)
        tema_80 = ta.tema(self.candles, 80)
        if tema_10 > tema_80:
            return 1
        else:
            return -1
    
    @property
    def long_term_trend(self):
        # Determine long-term trend using 4h timeframe TEMA crossover
        # TEMA 20 above TEMA 70 indicates uptrend (1)
        # TEMA 20 below TEMA 70 indicates downtrend (-1)
        tema_20 = ta.tema(self.candles_4h, 20)
        tema_70 = ta.tema(self.candles_4h, 70)
        if tema_20 > tema_70:
            return 1
        else:
            return -1
    
    @property
    def atr(self):
        # Average True Range - measures volatility for position sizing and stops
        return ta.atr(self.candles)
    
    @property
    def adx(self):
        # Average Directional Index - measures trend strength
        return ta.adx(self.candles)
    
    @property
    def cmo(self):
        # Chande Momentum Oscillator - momentum indicator
        return ta.cmo(self.candles)

    def should_long(self) -> bool:
        # Enter long when:
        # - Both short-term and long-term trends are bullish
        # - ADX above 40 (strong trend)
        # - CMO above 40 (positive momentum)
        return (self.short_term_trend == 1 and 
                self.long_term_trend == 1 and 
                self.adx > 40 and 
                self.cmo > 40)

    def should_short(self) -> bool:
        # Enter short when:
        # - Both short-term and long-term trends are bearish
        # - ADX above 40 (strong trend)
        # - CMO below -40 (negative momentum)
        return (self.short_term_trend == -1 and 
                self.long_term_trend == -1 and 
                self.adx > 40 and 
                self.cmo < -40)
        
    def go_long(self):
        # Set entry 1 ATR below current price (limit order)
        entry = self.price - self.atr
        # Set stop loss 4 ATR below entry
        stop = entry - (self.atr * 4)
        # Calculate position size risking 3% of available margin
        qty = utils.risk_to_qty(self.available_margin, 3, entry, stop, fee_rate=self.fee_rate)
        # Place buy order
        self.buy = qty*2, entry

    def go_short(self):
        # Set entry 1 ATR above current price (limit order)
        entry = self.price + self.atr
        # Set stop loss 4 ATR above entry
        stop = entry + (self.atr * 4)
        # Calculate position size risking 3% of available margin
        qty = utils.risk_to_qty(self.available_margin, 3, entry, stop, fee_rate=self.fee_rate)
        # Place sell order
        self.sell = qty*2, entry
    
    def should_cancel_entry(self) -> bool:
        # Cancel pending orders if conditions change
        return True
    
    def on_open_position(self, order) -> None:
        # Set stop loss and take profit when position opens
        if self.is_long:
            # For long positions: stop 4 ATR below entry, take profit 3 ATR above entry
            self.stop_loss = self.position.qty, self.position.entry_price - self.atr * 4
            self.take_profit = self.position.qty, self.position.entry_price + self.atr * 3
        elif self.is_short:
            # For short positions: stop 4 ATR above entry, take profit 3 ATR below entry
            self.stop_loss = self.position.qty, self.position.entry_price + self.atr * 4
            self.take_profit = self.position.qty, self.position.entry_price - self.atr * 3
    
    # def after(self) -> None:
    #     # Add TEMA indicators to the main candlestick chart
    #     self.add_line_to_candle_chart('TEMA 10', ta.tema(self.candles, 10), 'blue')
    #     self.add_line_to_candle_chart('TEMA 80', ta.tema(self.candles, 80), 'orange')
    #     self.add_line_to_candle_chart('TEMA 20 (4h)', ta.tema(self.candles_4h, 20), 'green')
    #     self.add_line_to_candle_chart('TEMA 70 (4h)', ta.tema(self.candles_4h, 70), 'red')
        
    #     # Add ADX indicator to separate chart with threshold line
    #     self.add_extra_line_chart('ADX', 'ADX', self.adx, 'purple')
    #     self.add_horizontal_line_to_extra_chart('ADX', 'Threshold', 40, 'gray')
        
    #     # Add CMO indicator to separate chart with threshold lines
    #     self.add_extra_line_chart('CMO', 'CMO', self.cmo, 'cyan')
    #     self.add_horizontal_line_to_extra_chart('CMO', 'Upper Threshold', 40, 'green')
    #     self.add_horizontal_line_to_extra_chart('CMO', 'Lower Threshold', -40, 'red')
