# write me a macd strategy for ranging markets with the following rules:
# divergence + support/resistance + adx
# step 1: identify the support/resistance on higher timeframe
# step 2: wait for Divergence on lower timeframe
# for sell trade: identify the lowest point between the tops on the MACD
# for buy trade: identify the highest point between the bottoms on the MACD
# Set the stop loss as the current price minus 6 times the current ATR values.
# Risk 3% of the account's capital per each trad.
# take profit is 5 times the stop loss.

from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils
import numpy as np


class MACDStrategy(Strategy):
    def __init__(self):
        super().__init__()
        self.last_trade_index = 0
    
    @property
    def higher_tf_candles(self):
        """Get higher timeframe candles for support/resistance"""
        if self.timeframe == '15m':
            return self.get_candles(self.exchange, self.symbol, '1h')
        elif self.timeframe == '1h':
            return self.get_candles(self.exchange, self.symbol, '4h')
        else:
            return self.get_candles(self.exchange, self.symbol, '1D')
    
    @property
    def htf_ema(self):
        """EMA on higher timeframe to gate trade direction"""
        return ta.ema(self.higher_tf_candles)
    
    @property
    def htf_trend(self):
        """Directional filter from HTF EMA"""
        if self.price > self.htf_ema:
            return 1
        elif self.price < self.htf_ema:
            return -1
        return 0
    
    @property
    def macd(self):
        """MACD indicator for divergence detection"""
        return ta.macd(self.candles, sequential=True)
    
    @property
    def adx(self):
        """ADX to confirm ranging market (low ADX = ranging)"""
        return ta.adx(self.candles)
    
    @property
    def atr(self):
        """ATR for stop loss calculation"""
        return ta.atr(self.candles)
    
    @property
    def is_ranging(self):
        """Ranging market when ADX is below 25"""
        return self.adx < 25
    
    @property
    def support_level(self):
        """Calculate support from higher timeframe"""
        lows = self.higher_tf_candles[-20:, 4]  # Last 20 lows
        return np.min(lows)
    
    @property
    def resistance_level(self):
        """Calculate resistance from higher timeframe"""
        highs = self.higher_tf_candles[-20:, 3]  # Last 20 highs
        return np.max(highs)
    
    def detect_bullish_divergence(self):
        """Detect bullish divergence: price makes lower low, MACD makes higher low"""
        if len(self.candles) < 30:
            return False
        
        # Get recent price lows and MACD histogram values
        price_lows = self.candles[-30:, 4]  # Low prices
        macd_hist = self.macd.hist[-30:]
        
        # Find local minimums
        price_min_indices = []
        macd_min_indices = []
        
        for i in range(5, 25):
            # Price local minimum
            if price_lows[i] < price_lows[i-1] and price_lows[i] < price_lows[i+1]:
                price_min_indices.append(i)
            # MACD local minimum
            if macd_hist[i] < macd_hist[i-1] and macd_hist[i] < macd_hist[i+1]:
                macd_min_indices.append(i)
        
        # Need at least 2 minimums to compare
        if len(price_min_indices) < 2 or len(macd_min_indices) < 2:
            return False
        
        # Compare last two minimums
        price_last_two = [price_lows[i] for i in price_min_indices[-2:]]
        macd_last_two = [macd_hist[i] for i in macd_min_indices[-2:]]
        
        # Bullish divergence: price lower low, MACD higher low
        return price_last_two[1] < price_last_two[0] and macd_last_two[1] > macd_last_two[0]
    
    def detect_bearish_divergence(self):
        """Detect bearish divergence: price makes higher high, MACD makes lower high"""
        if len(self.candles) < 30:
            return False
        
        # Get recent price highs and MACD histogram values
        price_highs = self.candles[-30:, 3]  # High prices
        macd_hist = self.macd.hist[-30:]
        
        # Find local maximums
        price_max_indices = []
        macd_max_indices = []
        
        for i in range(5, 25):
            # Price local maximum
            if price_highs[i] > price_highs[i-1] and price_highs[i] > price_highs[i+1]:
                price_max_indices.append(i)
            # MACD local maximum
            if macd_hist[i] > macd_hist[i-1] and macd_hist[i] > macd_hist[i+1]:
                macd_max_indices.append(i)
        
        # Need at least 2 maximums to compare
        if len(price_max_indices) < 2 or len(macd_max_indices) < 2:
            return False
        
        # Compare last two maximums
        price_last_two = [price_highs[i] for i in price_max_indices[-2:]]
        macd_last_two = [macd_hist[i] for i in macd_max_indices[-2:]]
        
        # Bearish divergence: price higher high, MACD lower high
        return price_last_two[1] > price_last_two[0] and macd_last_two[1] < macd_last_two[0]
    
    @property
    def near_support(self):
        """Check if price is near support level"""
        return abs(self.price - self.support_level) / self.price < 0.02  # Within 2%
    
    @property
    def near_resistance(self):
        """Check if price is near resistance level"""
        return abs(self.price - self.resistance_level) / self.price < 0.02  # Within 2%
    
    def should_long(self) -> bool:
        """Enter long when bullish divergence at support in ranging market"""
        return ( 
                self.near_support and 
                self.detect_bullish_divergence() and
                
                self.index - self.last_trade_index > 10)
    
    def should_short(self) -> bool:
        """Enter short when bearish divergence at resistance in ranging market"""
        
        return ( 
                self.near_resistance and 
                self.detect_bearish_divergence() and
                
                self.index - self.last_trade_index > 10)
    
    def go_long(self):
        """Execute long trade with 3% risk"""
        entry = self.price
        stop = entry - (self.atr * 3)
        qty = utils.risk_to_qty(self.available_margin, 3, entry, stop, fee_rate=self.fee_rate)
        self.buy = qty, entry
    
    def go_short(self):
        """Execute short trade with 3% risk"""
        entry = self.price
        stop = entry + (self.atr * 3)
        qty = utils.risk_to_qty(self.available_margin, 3, entry, stop, fee_rate=self.fee_rate)
        self.sell = qty, entry
    
    def should_cancel_entry(self) -> bool:
        return True
    
    def on_open_position(self, order) -> None:
        """Set stop loss and take profit when position opens"""
        if self.is_long:
            stop_distance = self.atr * 3
            self.stop_loss = self.position.qty, self.price - stop_distance
            self.take_profit = self.position.qty, self.price + (stop_distance * 5)
        elif self.is_short:
            stop_distance = self.atr * 3
            self.stop_loss = self.position.qty, self.price + stop_distance
            self.take_profit = self.position.qty, self.price - (stop_distance * 5)
    
    def on_close_position(self, order) -> None:
        """Track last trade to prevent overtrading"""
        self.last_trade_index = self.index
    
    def after(self) -> None:
        """Add MACD and visual markers to charts"""
        # Add MACD indicator to extra chart
        # Get non-sequential MACD for proper chart display
        macd_current = ta.macd(self.candles)
        self.add_extra_line_chart('MACD', 'MACD Line', macd_current.macd)
        self.add_extra_line_chart('MACD', 'Signal Line', macd_current.signal)
        # Plot histogram as two colored series to emulate bars
        self.add_extra_line_chart('MACD', 'Histogram+', macd_current.hist if macd_current.hist > 0 else 0, 'green')
        self.add_extra_line_chart('MACD', 'Histogram-', macd_current.hist if macd_current.hist < 0 else 0, 'red')
        self.add_horizontal_line_to_extra_chart('MACD', 'Zero', 0)

        # Add ATR on its own extra chart
        self.add_extra_line_chart('ATR', 'ATR', self.atr)
        
        # Add support and resistance levels to main chart
        self.add_horizontal_line_to_candle_chart('Support', self.support_level, 'green')
        self.add_horizontal_line_to_candle_chart('Resistance', self.resistance_level, 'red')
        
        # Mark divergence detection on the chart
        if self.detect_bullish_divergence():
            # Store bullish divergence signal
            if not hasattr(self, 'vars') or 'last_bullish_div' not in self.vars:
                if not hasattr(self, 'vars'):
                    self.vars = {}
                self.vars['last_bullish_div'] = self.index
        
        if self.detect_bearish_divergence():
            # Store bearish divergence signal
            if not hasattr(self, 'vars') or 'last_bearish_div' not in self.vars:
                if not hasattr(self, 'vars'):
                    self.vars = {}
                self.vars['last_bearish_div'] = self.index
    
    def watch_list(self) -> list:
        """Values to monitor during live trading"""
        return [
            ('ADX', round(self.adx, 2)),
            ('Ranging Market', self.is_ranging),
            ('Bullish Divergence', self.detect_bullish_divergence()),
            ('Bearish Divergence', self.detect_bearish_divergence()),
            ('Near Support', self.near_support),
            ('Near Resistance', self.near_resistance),
            ('Support Level', round(self.support_level, 2)),
            ('Resistance Level', round(self.resistance_level, 2)),
            ('HTF EMA', round(self.htf_ema, 2)),
            ('HTF Trend', self.htf_trend),
            ('MACD Histogram', round(self.macd.hist[-1], 4)),
        ]