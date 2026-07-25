# write me a gaussian strategy with the following rules:
# 1. Long:
#     - Price crosses above the Gaussian filter
#     - Price is above the upper band
# 2. Short:
#     - Price crosses below the Gaussian filter
#     - Price is below the lower band
# 3. Take-profit:
#     - Long: price crosses below the lower band
#     - Short: price crosses above the upper band
# 4. Stop-loss:
#     - Stop loss is the current price minus 6 times the current ATR values.
# 5. Risk management:
#     - Risk 3% of the account per trade.
#     - Use market order to enter the trade.
from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class GaussianStrategy(Strategy):
    @property
    def gauss_filter(self):
        return ta.gauss(self.candles, source_type="close", period=144, poles=4)
    
    @property
    def atr(self):
        return ta.atr(self.candles)
    
    @property
    def upper_band(self):
        return self.gauss_filter + self.atr
    
    @property
    def adx(self):
        return ta.adx(self.candles)
    @property
    def lower_band(self):
        return self.gauss_filter - self.atr

    def should_long(self) -> bool:
        # Price crosses above Gaussian filter AND price is above upper band
        if self.index == 0:
            return False
        
        prev_price = self.candles[-2, 2]
        prev_gauss = ta.gauss(self.candles[:-1], source_type="close")
        
        return prev_price <= prev_gauss and self.price > self.gauss_filter and self.price > self.upper_band

    def should_short(self) -> bool:
        # Price crosses below Gaussian filter AND price is below lower band
        if self.index == 0:
            return False
        
        prev_price = self.candles[-2, 2]
        prev_gauss = ta.gauss(self.candles[:-1], source_type="close")
        
        return prev_price >= prev_gauss and self.price < self.gauss_filter and self.price < self.lower_band
        
    def go_long(self):
        entry = self.price
        stop = entry - self.atr * 6
        qty = utils.risk_to_qty(self.available_margin, 3, entry, stop, fee_rate=self.fee_rate)
        self.buy = qty, entry

    def go_short(self):
        entry = self.price
        stop = entry + self.atr * 6
        qty = utils.risk_to_qty(self.available_margin, 3, entry, stop, fee_rate=self.fee_rate)
        self.sell = qty, entry
    
    def should_cancel_entry(self) -> bool:
        return True
    
    def on_open_position(self, order):
        if self.is_long:
            self.stop_loss = self.position.qty, self.position.entry_price - self.atr * 6
        elif self.is_short:
            self.stop_loss = self.position.qty, self.position.entry_price + self.atr * 6
    
    def update_position(self):
        if self.is_long:
            # Take profit: price crosses below lower band
            if self.price < self.lower_band:
                self.liquidate()
        elif self.is_short:
            # Take profit: price crosses above upper band
            if self.price > self.upper_band:
                self.liquidate()
    
    def after(self):
        self.add_line_to_candle_chart('Gaussian Filter', self.gauss_filter)
        self.add_line_to_candle_chart('Upper Band', self.upper_band)
        self.add_line_to_candle_chart('Lower Band', self.lower_band)
