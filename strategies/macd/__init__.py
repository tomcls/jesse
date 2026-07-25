from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class macd(Strategy):
    @property
    def macd(self):
        return ta.macd(self.candles, sequential=True)
    
    @property
    def ema20(self):
        return ta.ema(self.candles, 20)
    @property
    def cmo(self):
        return ta.cmo(self.candles, 14)
    @property
    def adx(self):
        return ta.adx(self.candles)
    @property
    def atr(self,period=14):
        return ta.atr(self.candles)
    @property
    def williams_r(self):
        return ta.willr(self.candles)
    @property
    def higher_tf_candles(self):
        # Get higher timeframe candles based on current timeframe
        if self.timeframe == '5m':
            htf = '30m'
        elif self.timeframe == '15m':
            htf = '1h'
        elif self.timeframe == '30m':
            htf = '4h'
        elif self.timeframe == '4h':
            htf = '1D'
        else:
            htf = '1D'
        return self.get_candles(self.exchange, self.symbol, htf)
    
    @property
    def higher_tf_trend(self):
        # Determine trend using EMA 50 and 200 on higher timeframe
        ema50 = ta.ema(self.higher_tf_candles, 50)
        ema200 = ta.ema(self.higher_tf_candles, 200)
        
        if ema50 > ema200 and self.price > ema50:
            return 1  # Bullish trend
        elif ema50 < ema200 and self.price < ema50:
            return -1  # Bearish trend
        else:
            return 0  # No clear trend
    
    def should_long(self) -> bool:
        # MACD line crossed above signal line (previous bar)
        macd_cross = self.macd.macd[-2] <= self.macd.signal[-2] and self.macd.macd[-1] > self.macd.signal[-1]
        
        # Histogram is green and above zero
        histogram_green = self.macd.hist[-1] > 0
        
        # Price moved above 20 EMA
        price_above_ema = self.price > self.ema20
        
        # Higher timeframe trend is bullish
        htf_bullish = self.higher_tf_trend == 1
        
        return macd_cross and histogram_green and price_above_ema   and self.williams_r < -60
    
    def should_short(self) -> bool:
        # MACD line crossed below signal line (previous bar)
        macd_cross = self.macd.macd[-2] >= self.macd.signal[-2] and self.macd.macd[-1] < self.macd.signal[-1]
        
        # Histogram is red and below zero
        histogram_red = self.macd.hist[-1] < 0
        
        # Price moved below 20 EMA
        price_below_ema = self.price < self.ema20
        
        # Higher timeframe trend is bearish
        htf_bearish = self.higher_tf_trend == -1
        
        return macd_cross and histogram_red and price_below_ema  and self.williams_r > -40
    
    def go_long(self):
        entry = self.price
        stop = entry - self.atr * 3
        qty = utils.risk_to_qty(self.available_margin, 3, entry, stop, fee_rate=self.fee_rate)
        self.buy = qty, entry
    
    def go_short(self):
        entry = self.price
        stop = entry + self.atr * 3
        qty = utils.risk_to_qty(self.available_margin, 3, entry, stop, fee_rate=self.fee_rate)
        self.sell = qty, entry
    
    def on_open_position(self, order) -> None:
        if self.is_long:
            self.stop_loss = self.position.qty, self.position.entry_price - self.atr * 3
        elif self.is_short:
            self.stop_loss = self.position.qty, self.position.entry_price + self.atr * 3
    
    def update_position(self) -> None:
        # Exit long positions when trend reverses
        if self.is_long:
            if (self.macd.macd[-1] < self.macd.signal[-1] or 
                self.macd.hist[-1] < 0 or 
                self.price < self.ema20):
                self.liquidate()
        
        # Exit short positions when trend reverses
        elif self.is_short:
            if (self.macd.macd[-1] > self.macd.signal[-1] or 
                self.macd.hist[-1] > 0 or 
                self.price > self.ema20):
                self.liquidate()
   
    def should_cancel_entry(self) -> bool:
        return True
    
    def after(self) -> None:
        # Add EMA 20 to main chart
        self.add_line_to_candle_chart('EMA 20', self.ema20)
        
        # Add higher timeframe EMAs to main chart
        htf_ema50 = ta.ema(self.higher_tf_candles, 50)
        htf_ema200 = ta.ema(self.higher_tf_candles, 200)
        self.add_line_to_candle_chart('HTF EMA 50', htf_ema50, 'orange')
        self.add_line_to_candle_chart('HTF EMA 200', htf_ema200, 'purple')
        
        # Add stop loss to main chart when position is open
        if self.is_open:
            self.add_line_to_candle_chart('Stop Loss', self.average_stop_loss, 'red')
        
        # Add MACD lines to separate chart (access current values with [-1])
        self.add_extra_line_chart('MACD', 'MACD Line', self.macd.macd[-1])
        self.add_extra_line_chart('MACD', 'Signal Line', self.macd.signal[-1])
        self.add_extra_line_chart('MACD', 'Histogram', self.macd.hist[-1])
        
        # Add zero line to MACD chart
        self.add_horizontal_line_to_extra_chart('MACD', 'Zero', 0, 'gray')
        
        # Add Williams %R to separate chart
        self.add_extra_line_chart('Williams %R', 'Williams %R', self.williams_r)
        
        # Add reference lines to Williams %R chart
        self.add_horizontal_line_to_extra_chart('Williams %R', 'Oversold -80', -80, 'green')
        self.add_horizontal_line_to_extra_chart('Williams %R', 'Overbought -20', -20, 'red')
