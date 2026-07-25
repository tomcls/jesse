from typing import List
import numpy as np

from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class VWAP(Strategy):
    """
    VWAP Bollinger Bands RSI Strategy

    Idée:
      - For the uptrend: the candles must be above the vwap and close above the vwap.
      - For the downtrend: the candles must be below the vwap and close below the vwap.
      if im in a uptrend i should long and at the same time i have a candles that closes below the lower bolinger bands curve and the rsi is below 45 in this case i have a buy signals
      if im in a downtrend i should short and at the same time i have a candles that closes above the upper bolinger bands curve and the rsi is above 55 in this case i have a sell signals.
      i have a stop-loss: 1.2 *ATR.
      i have a take-profit: 1.5 * ATR from entry price (Risk:Reward = 1:1.5)
      i have a risk management: utils.risk_to_qty (le param risque est un POURCENT: 3 = 3%).
     

      iflong position and the rsi is crossing above 90 i should close the position.
      ifshort position and the rsi is crossing below 10 i should close the position.
      only one position at a time.
    """

    @property
    def vwap(self):
        return ta.vwap(self.candles, anchor="D")
    # @property
    # def trend(self):
    #     """Determine trend based on VWAP and Bollinger Bands"""

    #     # Uptrend: BB upper and lower bands above VWAP + closes above VWAP for past 15 candles
    #     if np.all(self.bb.upperband > self.vwap) and np.all(self.bb.lowerband > self.vwap) and np.all(self.close > self.vwap):
    #         return 1
    #     # Downtrend: BB upper and lower bands below VWAP + closes below VWAP for past 15 candles
    #     elif np.all(self.bb.upperband < self.vwap) and np.all(self.bb.lowerband < self.vwap) and np.all(self.close < self.vwap):
    #         return -1
        
    #     return 0  # No clear trend
    
    @property
    def trend(self):
        """Determine trend based on VWAP"""
        if self.price > self.vwap and self.close > self.vwap:
            return 1  # Uptrend
        elif self.price < self.vwap and self.close < self.vwap:
            return -1  # Downtrend
        return 0  # No clear trend

    @property
    def bb(self):
        return ta.bollinger_bands(self.candles, self.hp['bb_period'], self.hp['bb_std'])

    @property
    def rsi(self):
        return ta.rsi(self.candles)

    @property
    def atr(self):
        return ta.atr(self.candles, self.hp['atr_period'], sequential=False)

    @property
    def trend_strength(self):
        """Only trade strong trends"""
        # Use ATR ratio or ADX to confirm trend strength
        adx = ta.adx(self.candles)
        return adx > 30  # Only trade when trend is established
    @property
    def volatility_filter(self):
        """Avoid trading in low volatility conditions"""
        atr_ratio = self.atr / ta.sma(self.candles, 20)  # ATR relative to price
        return atr_ratio > 0.004  # Minimum volatility threshold
    # ========= Signaux =========

    def should_long(self) -> bool:
        if self.position.is_open:
            return False
        # Long signal: uptrend + candle closes below lower Bollinger Band + RSI below threshold
        return (self.trend == 1 and
                self.trend_strength and
                self.volatility_filter and
                self.close < self.bb.lowerband and
                self.rsi < self.hp['rsi_long_threshold'])

    def should_short(self) -> bool:
        if self.position.is_open:
            return False
        # Short signal: downtrend + candle closes above upper Bollinger Band + RSI above threshold
        return (self.trend == -1 and
                self.trend_strength and
                self.volatility_filter and
                self.close > self.bb.upperband and
                self.rsi > self.hp['rsi_short_threshold'])

    def should_cancel_entry(self) -> bool:
        return False

    # ========= Exécution =========

    def go_long(self):
        entry_price = self.price
        stop_loss_price = entry_price - (self.atr * self.hp['stop_loss_multiplier'])
        # Risk percentage from hyperparameters
        qty = utils.risk_to_qty(self.available_margin, self.hp['risk_percentage'], entry_price, stop_loss_price, fee_rate=self.fee_rate)
        self.buy = qty , entry_price

    def go_short(self):
        entry_price = self.price
        stop_loss_price = entry_price + (self.atr * self.hp['stop_loss_multiplier'])
        # Risk percentage from hyperparameters
        qty = utils.risk_to_qty(self.available_margin, self.hp['risk_percentage'], entry_price, stop_loss_price, fee_rate=self.fee_rate)
        self.sell = qty , entry_price

    def on_open_position(self, order):
        if self.is_long:
            self.stop_loss = self.position.qty, self.position.entry_price - (self.atr * self.hp['stop_loss_multiplier'])
            # Take profit: ATR multiplier from entry price
            take_profit_price = self.position.entry_price + (self.atr * self.hp['take_profit_multiplier'])
            self.take_profit = self.position.qty, take_profit_price
        elif self.is_short:
            self.stop_loss = self.position.qty, self.position.entry_price + (self.atr * self.hp['stop_loss_multiplier'])
            # Take profit: ATR multiplier from entry price
            take_profit_price = self.position.entry_price - (self.atr * self.hp['take_profit_multiplier'])
            self.take_profit = self.position.qty, take_profit_price

    def update_position(self):
        if self.is_long:
            # Exit if trend reverses
            if self.trend != 1:
                self.liquidate()
            # Close position if RSI crosses above 90
            if self.rsi > 90:
                self.liquidate()

        elif self.is_short:
            # Exit if trend reverses
            if self.trend != -1:
                self.liquidate()
            # Close position if RSI crosses below 10
            if self.rsi < 10:
                self.liquidate()

    def after(self) -> None:
        # Add VWAP to main candle chart
        self.add_line_to_candle_chart('VWAP', self.vwap, color='yellow')

        # Add Bollinger Bands to main candle chart
        self.add_line_to_candle_chart('BB_Upper', self.bb.upperband, color='red')
        self.add_line_to_candle_chart('BB_Middle', self.bb.middleband, color='blue')
        self.add_line_to_candle_chart('BB_Lower', self.bb.lowerband, color='green')

        # Add RSI as extra chart with overbought/oversold levels
        self.add_extra_line_chart('RSI', 'RSI', self.rsi, color='purple')
        self.add_horizontal_line_to_extra_chart('RSI', 'Overbought', 70, color='red')
        self.add_horizontal_line_to_extra_chart('RSI', 'Oversold', 30, color='green')
        self.add_horizontal_line_to_extra_chart('RSI', 'Exit_Long', 90, color='darkred')
        self.add_horizontal_line_to_extra_chart('RSI', 'Exit_Short', 10, color='darkgreen')

        # Add ATR as extra chart
        self.add_extra_line_chart('ATR', 'ATR', self.atr, color='orange')

    # ========= Dashboard / Optim =========

    def hyperparameters(self) -> List[dict]:
        """
        On garde volontairement peu de paramètres: robustesse > tuning.
        """
        return [
            {'name': 'atr_period', 'type': int, 'min': 10, 'max': 50, 'default': 14},
            {'name': 'risk_percentage', 'type': float, 'min': 1, 'max': 5, 'step': 0.5, 'default': 3},
            {'name': 'rsi_long_threshold', 'type': int, 'min': 20, 'max': 80, 'default': 40},
            {'name': 'rsi_short_threshold', 'type': int, 'min': 50, 'max': 80, 'default': 60},
            {'name': 'stop_loss_multiplier', 'type': float, 'min': 0.5, 'max': 3.0, 'step': 0.1, 'default': 2.5},
            {'name': 'take_profit_multiplier', 'type': float, 'min': 1.0, 'max': 5.0, 'step': 0.1, 'default': 4},
            {'name': 'bb_period', 'type': int, 'min': 10, 'max': 50, 'default': 20},
            {'name': 'bb_std', 'type': float, 'min': 1.0, 'max': 3.0, 'step': 0.1, 'default': 2.0},
        ]

    def watch_list(self) -> list:
        return [
            ('trend', self.trend),
            ('vwap', self.vwap),
            ('rsi', self.rsi),
            ('bb_upper', self.bb.upperband),
            ('bb_lower', self.bb.lowerband),
        ]

   
