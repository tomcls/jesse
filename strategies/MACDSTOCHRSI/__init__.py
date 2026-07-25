from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class MACDSTOCHRSI(Strategy):
    @property
    def macd(self):
        # Fast: 12, Slow: 31, Signal: 9
        return ta.macd(self.candles, fast_period=12, slow_period=31, signal_period=9)
    
    @property
    def macd_signal_seq(self):
        # Sequential signal line for crossover detection
        return ta.macd(self.candles, fast_period=12, slow_period=31, signal_period=9, sequential=True).signal
    
    @property
    def stoch(self):
        # Stochastic: K period=14, K smoothing=3, D smoothing=3
        return ta.stoch(self.candles, fastk_period=14, slowk_period=3, slowd_period=3)
    
    @property
    def rsi(self):
        return ta.rsi(self.candles, period=14)
    
    @property
    def atr(self):
        return ta.atr(self.candles, period=7)
    
    @property
    def lookback_low(self):
        # Lowest low over last 7 candles
        return min(self.candles[-7:, 4])
    
    @property
    def lookback_high(self):
        # Highest high over last 7 candles
        return max(self.candles[-7:, 3])

    def should_long(self) -> bool:
        # MACD signal line crosses above zero
        signal_cross_up = self.macd_signal_seq[-2] <= 0 and self.macd.signal > 0
        # RSI above 55 (buy range)
        rsi_condition = self.rsi > 55
        # Stochastic %D below or equal to 86 (overbought level)
        stoch_condition = self.stoch.d <= 86
        
        return signal_cross_up and rsi_condition and stoch_condition

    def should_short(self) -> bool:
        # MACD signal line crosses below zero
        signal_cross_down = self.macd_signal_seq[-2] >= 0 and self.macd.signal < 0
        # RSI below 45 (sell range)
        rsi_condition = self.rsi < 45
        # Stochastic %D above or equal to 13 (oversold level)
        stoch_condition = self.stoch.d >= 13
        
        return signal_cross_down and rsi_condition and stoch_condition
        
    def go_long(self):
        entry = self.price
        # Stop: lowest low of lookback - ATR
        stop = self.lookback_low - self.atr
        # Risk 5% of available margin per trade
        qty = utils.risk_to_qty(self.available_margin, 5, entry, stop, fee_rate=self.fee_rate)
        self.buy = qty, entry

    def go_short(self):
        entry = self.price
        # Stop: highest high of lookback + ATR
        stop = self.lookback_high + self.atr
        # Risk 5% of available margin per trade
        qty = utils.risk_to_qty(self.available_margin, 5, entry, stop, fee_rate=self.fee_rate)
        self.sell = qty, entry
    
    def should_cancel_entry(self) -> bool:
        return True
    
    def on_open_position(self, order) -> None:
        if self.is_long:
            # Calculate stop distance and apply 1:1 risk/reward
            stop_price = self.lookback_low - self.atr
            stop_distance = self.position.entry_price - stop_price
            self.stop_loss = self.position.qty, stop_price
            self.take_profit = self.position.qty, self.position.entry_price + stop_distance
        elif self.is_short:
            # Calculate stop distance and apply 1:1 risk/reward
            stop_price = self.lookback_high + self.atr
            stop_distance = stop_price - self.position.entry_price
            self.stop_loss = self.position.qty, stop_price
            self.take_profit = self.position.qty, self.position.entry_price - stop_distance
