from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils
import numpy as np


class macdbb(Strategy):
    @property
    def macd_fast_ema(self):
        return ta.ema(self.candles, self.hp['macd_fast_length'])
    
    @property
    def macd_slow_ema(self):
        return ta.ema(self.candles, self.hp['macd_slow_length'])
    
    @property
    def macd_line(self):
        return self.macd_fast_ema - self.macd_slow_ema
    
    @property
    def macd_signal(self):
        macd_line_series = ta.ema(self.candles, self.hp['macd_fast_length'], sequential=True) - ta.ema(self.candles, self.hp['macd_slow_length'], sequential=True)
        return ta.ema(macd_line_series, self.hp['signal_length'])
    
    @property
    def macd_histogram(self):
        macd_line_series = ta.ema(self.candles, self.hp['macd_fast_length'], sequential=True) - ta.ema(self.candles, self.hp['macd_slow_length'], sequential=True)
        signal_series = ta.ema(macd_line_series, self.hp['signal_length'], sequential=True)
        return macd_line_series - signal_series
    
    @property
    def lowest_histogram(self):
        hist_series = self.macd_histogram
        return np.min(hist_series[-self.hp['histogram_lookback']:])
    
    @property
    def highest_histogram(self):
        hist_series = self.macd_histogram
        return np.max(hist_series[-self.hp['histogram_lookback']:])
    
    @property
    def fast_ema(self):
        return ta.ema(self.candles, self.hp['fast_ema_length'])
    
    @property
    def slow_ema(self):
        return ta.ema(self.candles, self.hp['slow_ema_length'])
    
    @property
    def atr(self):
        return ta.atr(self.candles, self.hp['atr_length'])
    
    @property
    def rsi(self):
        return ta.rsi(self.candles, self.hp['rsi_length'])
    
    @property
    def stochastic(self):
        return ta.stoch(self.candles, fastk_period=self.hp['stoch_k_period'], slowk_period=self.hp['stoch_k_smooth'], slowd_period=self.hp['stoch_d_smooth'])
    
    @property
    def ma_filter(self):
        return self.close > self.fast_ema
    
    def should_long(self) -> bool:
        hist_series = self.macd_histogram
        current_hist = hist_series[-1]
        
        # Check if current histogram is at the lowest point in the lookback period
        is_lowest_hist = current_hist == self.lowest_histogram
        
        # Trend filter: fast EMA > slow EMA
        trend_up = self.fast_ema > self.slow_ema
        
        # Buy signal
        buy_signal = is_lowest_hist and trend_up and self.ma_filter
        
        # Optional RSI and Stochastic filter
        k, d = self.stochastic
        rsi_condition = self.rsi > self.hp['rsi_threshold'] and d <= self.hp['stoch_ob_level']
        
        return buy_signal and rsi_condition
    
    def should_short(self) -> bool:
        hist_series = self.macd_histogram
        current_hist = hist_series[-1]
        
        # Check if current histogram is at the highest point in the lookback period
        is_highest_hist = current_hist == self.highest_histogram
        
        # Trend filter: fast EMA < slow EMA
        trend_down = self.fast_ema < self.slow_ema
        
        # Sell signal
        sell_signal = is_highest_hist and trend_down and (self.close < self.fast_ema)
        
        # Optional RSI and Stochastic filter
        k, d = self.stochastic
        rsi_condition = self.rsi < (100 - self.hp['rsi_threshold']) and d >= (100 - self.hp['stoch_ob_level'])
        
        return sell_signal and rsi_condition
    
    def go_long(self):
        # Calculate stop loss based on ATR
        lowest_low = np.min(self.candles[-self.hp['stop_lookback']:, 4])
        stop_size = self.atr * self.hp['atr_multiplier']
        long_stop = lowest_low - stop_size
        
        # Calculate position size based on risk
        entry = self.price
        qty = utils.risk_to_qty(self.available_margin, 3, entry, long_stop, fee_rate=self.fee_rate) * 5
        
        self.buy = qty, entry
    
    def go_short(self):
        # Calculate stop loss based on ATR
        highest_high = np.max(self.candles[-self.hp['stop_lookback']:, 3])
        stop_size = self.atr * self.hp['atr_multiplier']
        short_stop = highest_high + stop_size
        
        # Calculate position size based on risk
        entry = self.price
        qty = utils.risk_to_qty(self.available_margin, 3, entry, short_stop, fee_rate=self.fee_rate) * 5
        
        self.sell = qty, entry
    
    def on_open_position(self, order) -> None:
        if self.is_long:
            # Calculate stop loss and take profit for long
            lowest_low = np.min(self.candles[-self.hp['stop_lookback']:, 4])
            stop_size = self.atr * self.hp['atr_multiplier']
            long_stop = lowest_low - stop_size
            
            # Calculate distance for risk:reward
            stop_distance = self.price - long_stop
            long_target = self.price + (stop_distance * self.hp['risk_reward'])
            
            self.stop_loss = self.position.qty, long_stop
            self.take_profit = self.position.qty, long_target
        
        elif self.is_short:
            # Calculate stop loss and take profit for short
            highest_high = np.max(self.candles[-self.hp['stop_lookback']:, 3])
            stop_size = self.atr * self.hp['atr_multiplier']
            short_stop = highest_high + stop_size
            
            # Calculate distance for risk:reward
            stop_distance = short_stop - self.price
            short_target = self.price - (stop_distance * self.hp['risk_reward'])
            
            self.stop_loss = self.position.qty, short_stop
            self.take_profit = self.position.qty, short_target
    
    def should_cancel_entry(self) -> bool:
        return True
    
    def hyperparameters(self) -> list:
        return [
            {'name': 'macd_fast_length', 'type': int, 'min': 5, 'max': 20, 'default': 10},
            {'name': 'macd_slow_length', 'type': int, 'min': 15, 'max': 40, 'default': 20},
            {'name': 'signal_length', 'type': int, 'min': 5, 'max': 15, 'default': 8},
            {'name': 'histogram_lookback', 'type': int, 'min': 20, 'max': 100, 'default': 48},
            {'name': 'fast_ema_length', 'type': int, 'min': 10, 'max': 50, 'default': 30},
            {'name': 'slow_ema_length', 'type': int, 'min': 100, 'max': 300, 'default': 200},
            {'name': 'atr_length', 'type': int, 'min': 5, 'max': 20, 'default': 7},
            {'name': 'atr_multiplier', 'type': float, 'min': 0.5, 'max': 3.0, 'default': 1.0},
            {'name': 'stop_lookback', 'type': int, 'min': 3, 'max': 15, 'default': 7},
            {'name': 'risk_reward', 'type': float, 'min': 0.5, 'max': 3.0, 'default': 1.0},
            {'name': 'rsi_length', 'type': int, 'min': 5, 'max': 20, 'default': 10},
            {'name': 'rsi_threshold', 'type': int, 'min': 50, 'max': 85, 'default': 74},
            {'name': 'stoch_k_period', 'type': int, 'min': 5, 'max': 21, 'default': 14},
            {'name': 'stoch_k_smooth', 'type': int, 'min': 1, 'max': 5, 'default': 3},
            {'name': 'stoch_d_smooth', 'type': int, 'min': 1, 'max': 5, 'default': 3},
            {'name': 'stoch_ob_level', 'type': int, 'min': 80, 'max': 100, 'default': 95},
        ]
    def dna(self) -> str:
        return "eyJhdHJfbGVuZ3RoIjogMTksICJhdHJfbXVsdGlwbGllciI6IDIuNjM1NDE4MzkzMTgxMzI3LCAiZmFzdF9lbWFfbGVuZ3RoIjogMzIsICJoaXN0b2dyYW1fbG9va2JhY2siOiA5NiwgIm1hY2RfZmFzdF9sZW5ndGgiOiAxMCwgIm1hY2Rfc2xvd19sZW5ndGgiOiAyMiwgInJpc2tfcmV3YXJkIjogMi4yNjkxNDc0OTI5NTk3NTE1LCAicnNpX2xlbmd0aCI6IDEyLCAicnNpX3RocmVzaG9sZCI6IDU0LCAic2lnbmFsX2xlbmd0aCI6IDUsICJzbG93X2VtYV9sZW5ndGgiOiAxNDksICJzdG9jaF9kX3Ntb290aCI6IDEsICJzdG9jaF9rX3BlcmlvZCI6IDgsICJzdG9jaF9rX3Ntb290aCI6IDUsICJzdG9jaF9vYl9sZXZlbCI6IDgzLCAic3RvcF9sb29rYmFjayI6IDh9"