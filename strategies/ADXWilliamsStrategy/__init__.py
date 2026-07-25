from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class ADXWilliamsStrategy(Strategy):
    @property
    def adx(self):
        return ta.adx(self.candles)
    
    @property
    def di(self):
        return ta.di(self.candles)
    
    @property
    def williams_r(self):
        return ta.willr(self.candles)
    
    @property
    def sma50(self):
        return ta.sma(self.candles, 50)
    
    @property
    def highest_high(self):
        return max(self.candles[-30:, 3])
    
    @property
    def lowest_low(self):
        return min(self.candles[-30:, 4])
        
    def should_long(self) -> bool:
        # Long if DI+ > DI-, ADX > 50, and Williams %R < -80 (oversold)
        return (self.di.plus > self.di.minus and 
                self.adx > 50 and 
                self.williams_r < -80)
        
    def should_short(self) -> bool:
        # Short if DI+ < DI-, ADX > 50, and Williams %R > -20 (overbought)
        return (self.di.plus < self.di.minus and 
                self.adx > 50 and 
                self.williams_r > -20)
        
    def go_long(self):
        entry_price = self.price
        stop_loss = self.sma50
        qty = utils.risk_to_qty(self.available_margin, 3, entry_price, stop_loss, fee_rate=self.fee_rate)
        self.buy = qty*5, entry_price
        
    def go_short(self):
        entry_price = self.price
        stop_loss = self.sma50
        qty = utils.risk_to_qty(self.available_margin, 3, entry_price, stop_loss, fee_rate=self.fee_rate)
        self.sell = qty*5, entry_price
        
    def on_open_position(self, order):
        if self.is_long:
            self.stop_loss = self.position.qty, self.sma50
            self.take_profit = self.position.qty, self.highest_high
        elif self.is_short:
            self.stop_loss = self.position.qty, self.sma50
            self.take_profit = self.position.qty, self.lowest_low
            
    def update_position(self):
        if self.is_long and self.should_short():
            self.liquidate()
        elif self.is_short and self.should_long():
            self.liquidate()
    
    # def after(self):
    #     # Add SMA to candlestick chart
    #     self.add_line_to_candle_chart("SMA50", self.sma50)
        
    #     # Add ADX to a separate chart
    #     self.add_extra_line_chart("ADX", "ADX", self.adx)
    #     self.add_horizontal_line_to_extra_chart("ADX", "Threshold", 50, "red")
        
    #     # Add DI lines to a separate chart
    #     self.add_extra_line_chart("DI", "DI+", self.di.plus, "green")
    #     self.add_extra_line_chart("DI", "DI-", self.di.minus, "red")
        
    #     # Add Williams %R to a separate chart
    #     self.add_extra_line_chart("Williams %R", "Williams %R", self.williams_r, "purple")
    #     self.add_horizontal_line_to_extra_chart("Williams %R", "Overbought", -20, "red")
    #     self.add_horizontal_line_to_extra_chart("Williams %R", "Oversold", -80, "green")