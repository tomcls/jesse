from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils
import numpy as np

# https://www.youtube.com/watch?v=wdsiZBIhAFw
# https://github.com/neurotrader888/VolatilityHawkes/blob/main/hawkes.py

class hawkes(Strategy):
    def __init__(self):
        super().__init__()
        self.last_below_index = -1
        self.current_signal = 0

    def hawkes_process(self, data: np.ndarray, kappa: float) -> np.ndarray:
        """Apply Hawkes process with exponential decay"""
        alpha = np.exp(-kappa)
        output = np.zeros(len(data))
        output[0] = data[0]
        
        for i in range(1, len(data)):
            output[i] = output[i - 1] * alpha + data[i]
        
        return output * kappa

    @property
    def norm_range(self):
        """Calculate normalized range using log prices"""
        high = self.candles[:, 3]
        low = self.candles[:, 4]
        close = self.candles[:, 2]
        
        # ATR on log prices
        log_high = np.log(high)
        log_low = np.log(low)
        log_close = np.log(close)
        atr_val = ta.atr(self.candles, period=336, sequential=True)
        
        # Normalized range
        norm_range = (log_high - log_low) / atr_val
        return norm_range

    @property
    def vol_hawkes(self):
        """Apply Hawkes process to normalized range"""
        norm_r = self.norm_range
        return self.hawkes_process(norm_r, kappa=0.1)

    @property
    def signal(self):
        """Generate trading signal based on volatility patterns"""
        vol_hawk = self.vol_hawkes
        lookback = 168
        
        # Calculate rolling quantiles
        q05 = np.zeros(len(vol_hawk))
        q95 = np.zeros(len(vol_hawk))
        
        for i in range(lookback, len(vol_hawk)):
            window = vol_hawk[i-lookback:i]
            q05[i] = np.percentile(window, 5)
            q95[i] = np.percentile(window, 95)
        
        # Generate signal
        signal = np.zeros(len(vol_hawk))
        last_below = -1
        curr_sig = 0
        close_prices = self.candles[:, 2]
        
        for i in range(lookback, len(vol_hawk)):
            # Track when below 5th percentile
            if vol_hawk[i] < q05[i]:
                last_below = i
                curr_sig = 0
            
            # Signal when breaks above 95th percentile after being below 5th
            if (vol_hawk[i] > q95[i] and 
                vol_hawk[i-1] <= q95[i-1] and 
                last_below > 0):
                
                price_change = close_prices[i] - close_prices[last_below]
                if price_change > 0:
                    curr_sig = 1  # Long
                else:
                    curr_sig = -1  # Short
            
            signal[i] = curr_sig
        
        return signal[-1]

    def should_long(self) -> bool:
        return self.signal == 1

    def should_short(self) -> bool:
        return self.signal == -1
        
    def go_long(self):
        qty = utils.size_to_qty(self.available_margin * 0.5, self.price, fee_rate=self.fee_rate)
        self.buy = qty, self.price

    def go_short(self):
        qty = utils.size_to_qty(self.available_margin * 0.5, self.price, fee_rate=self.fee_rate)
        self.sell = qty, self.price

    def update_position(self):
        # Exit when signal becomes neutral
        if self.signal == 0:
            self.liquidate()

    def should_cancel_entry(self) -> bool:
        return True
