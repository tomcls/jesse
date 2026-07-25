"""
============================================================================
HMA TREND FOLLOWING STRATEGY WITH MULTI-INDICATOR CONFIRMATION
============================================================================

STRATEGY OVERVIEW:
------------------
A trend-following strategy that uses Hull Moving Averages (HMA) as the primary 
trend indicator, combined with multiple momentum oscillators and market state 
filters to enter high-probability trending moves. The strategy uses multi-timeframe 
analysis and risk-based position sizing.

CORE INDICATORS:
----------------
1. HMA Fast (14-50, default: 30) - Short-term trend direction
2. HMA Slow (50-200, default: 100) - Long-term trend direction
3. Trend EMA (100-300, default: 200) - Overall market trend filter
4. SMA 200 on 2h timeframe - Higher timeframe trend confirmation
5. ATR (7-28, default: 14) - Volatility measure for SL/TP placement
6. Williams %R - Overbought/oversold oscillator
7. CMO (Chande Momentum Oscillator) - Momentum strength
8. CHOP (Choppiness Index) - Market state (trending vs choppy)

ENTRY RULES:
------------
LONG ENTRY:
- HMA Fast >= HMA Slow (bullish alignment)
- Price > HMA Slow (price above slow HMA)
- Price > Trend EMA (uptrend confirmed on main timeframe)
- Price > 2h SMA 200 (higher timeframe uptrend)
- Williams %R > -20 (not oversold, showing strength)
- CMO > 40 (strong bullish momentum)
- CHOP < 40 (market is trending, not choppy)

SHORT ENTRY:
- HMA Fast <= HMA Slow (bearish alignment)
- Price < HMA Slow (price below slow HMA)
- Price < Trend EMA (downtrend confirmed on main timeframe)
- Price < 2h SMA 200 (higher timeframe downtrend)
- Williams %R < -80 (oversold, showing weakness)
- CMO < -40 (strong bearish momentum)
- CHOP < 40 (market is trending, not choppy)

EXIT RULES:
-----------
- Stop Loss: 4 * ATR from entry price
- Take Profit: 10 * ATR from entry price (Risk:Reward = 1:2.5)
- No dynamic position management (fixed SL/TP)
- Only one position at a time (no pyramiding)

POSITION SIZING:
----------------
- Risk-based sizing using risk_to_qty utility
- Risk percentage: 1-5% of available margin (default: 2%)
- Position size calculated based on entry price and ATR-based stop loss
- Accounts for exchange fees in calculations

FILTERS:
--------
- Only enters when flat (no open positions)
- Multi-timeframe trend alignment required
- Market must be trending (CHOP < 40)
- Momentum confirmation from multiple oscillators

HYPERPARAMETERS (Optimizable):
-------------------------------
- hma_fast_len: 14-50 (default: 30)
- hma_slow_len: 50-200 (default: 100)
- trend_ema_len: 100-300 (default: 200)
- atr_len: 7-28 (default: 14)
- atr_mult_sl: 0.8-2.5 (default: 5) [Note: actual code uses fixed 4]
- atr_mult_tp: 1.5-4.0 (default: 10) [Note: actual code uses fixed 10]
- risk_pct: 1.0-5.0% (default: 2.0%)
- use_trailing: 0-1 (default: 1) [Note: currently disabled in code]
- adx_min: 0-40 (default: 30) [Note: not actively used in current version]
- trailing_pad: 0.3-1.0 (default: 0.5)
- candles_between_trades: 0-50 (default: 5)

VISUAL ELEMENTS:
----------------
The strategy displays on charts:
- HMA Fast and HMA Slow lines
- Trend EMA line
- Williams %R oscillator with overbought/oversold levels
- CMO oscillator with extreme levels
- Choppiness Index with trending/choppy zones
- Take Profit levels when position is open

BEST USE CASES:
---------------
- Trending markets on medium to longer timeframes (4h, 6h, 1D)
- Assets with clear directional moves and sufficient volatility
- Markets with good trend persistence (crypto, indices, forex majors)

RISK CONSIDERATIONS:
--------------------
- No trailing stop in current version (fixed SL/TP)
- Multiple indicator confirmations may cause late entries
- Fixed R:R ratio may not suit all market conditions
- No dynamic position management once entered

============================================================================
"""

import numpy as np
from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class HMAtrend(Strategy):
    
    def before(self):
        if self.index == 0:
            self.vars['exit_type'] = 0  # 0 = none, 1 = TP, -1 = SL
            self.vars['sl_progression'] = 0  # To track SL progression
            self.vars['last_trade_index'] = -100  # To space out trades

    def hyperparameters(self):
        return [
            {"name": "hma_fast_len", "type": int, "min": 14, "max": 50, "default": 30},
            {"name": "hma_slow_len", "type": int, "min": 50, "max": 200, "default": 100},
            {"name": "trend_ema_len", "type": int, "min": 100, "max": 300, "default": 200},
            {"name": "atr_len", "type": int, "min": 7, "max": 28, "default": 14},
            {"name": "atr_mult_sl", "type": float, "min": 0.8, "max": 2.5, "default": 5},
            {"name": "atr_mult_tp", "type": float, "min": 1.5, "max": 4.0, "default": 10},
            {"name": "risk_pct", "type": float, "min": 1.0, "max": 5.0, "default": 2.0, "step": 0.5},
            {"name": "use_trailing", "type": int, "min": 0, "max": 1, "default": 1},
            {"name": "adx_min", "type": int, "min": 0, "max": 40, "default": 30},
            {"name": "trailing_pad", "type": float, "min": 0.3, "max": 1.0, "default": 0.5, "step": 0.1},
            {"name": "candles_between_trades", "type": int, "min": 0, "max": 50, "default": 5},
        ]

    # ========== Properties ==========
    @property
    def long_term_candles(self):
        return self.get_candles(self.exchange, self.symbol, '4h')
    @property
    def hma_fast(self):
        return ta.hma(self.candles, period=int(self.hp['hma_fast_len']), sequential=True)

    @property
    def sma_4h(self):
        return ta.sma(self.long_term_candles, 200)
    
    @property
    def trend(self):
        if self.price > self.sma_4h:
            return 1
        elif self.price < self.sma_4h:
            return -1
        return 0
    @property
    def hma_slow(self):
        return ta.hma(self.candles, period=int(self.hp['hma_slow_len']), sequential=True)
    @property
    def williams_r(self):
        return ta.willr(self.candles)

    @property
    def cmo(self):
        return ta.cmo(self.candles, period=14)

    @property
    def chop(self):
        return ta.chop(self.candles, period=14)

    @property
    def trend_ema(self):
        return ta.ema(self.candles, period=int(self.hp['trend_ema_len']))

    @property
    def trend(self):
        """Determines the overall trend: 1 = uptrend, -1 = downtrend, 0 = neutral"""
        if self.price > self.trend_ema:
            return 1  # Uptrend
        elif self.price < self.trend_ema:
            return -1  # Downtrend
        else:
            return 0  # Neutral

    @property
    def atr(self) -> float:
        return float(ta.atr(self.candles, period=int(self.hp['atr_len'])))

    @property
    def adx(self) -> float:
        try:
            return float(ta.adx(self.candles, period=14))
        except Exception:
            return 0.0

    @property
    def short_term_trend(self):
        # Determine short-term trend using TEMA crossover
        # TEMA 10 above TEMA 80 indicates uptrend (1)
        # TEMA 10 below TEMA 80 indicates downtrend (-1)
        tema_10 = ta.hma(self.candles, 10)
        tema_80 = ta.hma(self.candles, 80)
        if tema_10 > tema_80:
            return 1
        else:
            return -1
    
    @property
    def long_term_trend(self):
        # Determine long-term trend using 4h timeframe TEMA crossover
        # TEMA 20 above TEMA 70 indicates uptrend (1)
        # TEMA 20 below TEMA 70 indicates downtrend (-1)
        tema_20 = ta.hma(self.long_term_candles, 20)
        tema_70 = ta.hma(self.long_term_candles, 70)
        if tema_20 > tema_70:
            return 1
        else:
            return -1
    @property
    def donchian(self):
        return ta.donchian(self.candles[:-1], period=30)
   
    def filters(self):
        return [self._flat_only]

    def _flat_only(self):
        # true only if no position is open
        return not (self.is_long or self.is_short)

    def should_add_position(self) -> bool:
        # disable pyramiding / DCA
        return False

    def should_long(self) -> bool:
        if self.is_long or self.is_short:
            return False

        if np.isnan(self.hma_fast[-1]) or np.isnan(self.hma_slow[-1]):
            return False
        w = self.williams_r
        
        price_above_slow = self.price > self.hma_slow[-1]
        
        #return self.hma_fast[-1] >= self.hma_slow[-1] and price_above_slow  and self.trend == 1 and  w > -20 and self.cmo > 40 and self.chop < 40 
        return self.short_term_trend == 1 and self.long_term_trend == 1 and self.adx > 40 and self.cmo > 40 and self.chop < 40
    def should_short(self) -> bool:
        if self.is_long or self.is_short:
            return False

        if np.isnan(self.hma_fast[-1]) or np.isnan(self.hma_slow[-1]):
            return False
        w = self.williams_r
        price_below_slow = self.price < self.hma_slow[-1]
        
        return self.short_term_trend == -1 and self.long_term_trend == -1 and self.adx > 40 and self.cmo < -40 and self.chop < 40
    # def should_long(self) -> bool:
    #     if self.is_long or self.is_short:
    #         return False

    #     if np.isnan(self.hma_fast[-1]) or np.isnan(self.hma_slow[-1]):
    #         return False
    #     w = self.williams_r
        
    #     price_above_slow = self.price > self.hma_slow[-1]
        
    #     return self.hma_fast[-1] >= self.hma_slow[-1] and price_above_slow  and self.trend == 1 and  w > -20 and self.cmo > 40 and self.chop < 40 

    def should_short(self) -> bool:
        if self.is_long or self.is_short:
            return False

        if np.isnan(self.hma_fast[-1]) or np.isnan(self.hma_slow[-1]):
            return False
        w = self.williams_r
        price_below_slow = self.price < self.hma_slow[-1]
        
        return self.hma_fast[-1] <= self.hma_slow[-1] and self.trend == -1 and price_below_slow and w < -80 and self.cmo < -40 and self.chop < 40 

    def go_long(self):
        entry = self.price
        sl = entry - float(self.hp['atr_mult_sl']) * self.atr
        qty = utils.risk_to_qty(
            self.available_margin,
            self.hp['risk_pct'],
            entry,
            sl,
            fee_rate=self.fee_rate
        )
        self.buy = qty, entry

    def go_short(self):
        entry = self.price
        sl = entry + float(self.hp['atr_mult_sl']) * self.atr
        qty = utils.risk_to_qty(
            self.available_margin,
            self.hp['risk_pct'],
            entry,
            sl,
            fee_rate=self.fee_rate
        )
        self.sell = qty, entry

    def should_cancel_entry(self) -> bool:
        return True

    def on_open_position(self, order) -> None:
        if self.is_long:
            self.stop_loss = self.position.qty, self.position.entry_price - float(self.hp['atr_mult_sl']) * self.atr
            self.take_profit = self.position.qty, self.position.entry_price + 10 * self.atr
        elif self.is_short:
            self.stop_loss = self.position.qty, self.position.entry_price + float(self.hp['atr_mult_sl']) * self.atr
            self.take_profit = self.position.qty, self.position.entry_price - 10 * self.atr

    # def on_open_position(self, order) -> None:
    #     if self.is_long:
    #         sl = self.position.entry_price - self.atr * self.hp['atr_mult_sl']
    #         self.stop_loss = self.position.qty, sl
    #         tp = self.price + float(self.hp['atr_mult_tp']) * self.atr
    #         self.take_profit = self.position.qty, tp
    #         self.vars['sl_progression'] = sl
    #     elif self.is_short:
    #         tp = self.price - float(self.hp['atr_mult_tp']) * self.atr
    #         sl = self.position.entry_price + self.atr * self.hp['atr_mult_sl']
    #         self.stop_loss = self.position.qty, sl
    #         self.take_profit = self.position.qty, tp
    #         self.vars['sl_progression'] = sl

    # def update_position(self) -> None:
    #     if self.is_long:
    #         self.stop_loss = self.position.qty, max(self.average_stop_loss, self.donchian.lowerband)
    #     elif self.is_short:
    #         self.stop_loss = self.position.qty, min(self.average_stop_loss, self.donchian.upperband)


    # def update_position(self):
    #     """Optional trailing stop based on HMA_fast"""
    #     # Reset exit type when position is open
    #     self.vars['exit_type'] = 0
        
    #     # Update sl_progression with current stop loss
    #     if self.is_open:
    #         self.vars['sl_progression'] = self.average_stop_loss
        
    #     if int(self.hp['use_trailing']) != 1:
    #         return

    #     atr = self.atr
    #     pad = float(self.hp['trailing_pad']) * atr
    #     hf = self.hma_fast[-1]

    #     if self.is_long:
    #         new_sl = hf - pad
    #         if new_sl > self.average_stop_loss:
    #             #self.stop_loss = self.position.qty, new_sl
    #             self.vars['sl_progression'] = new_sl

    #     elif self.is_short:
    #         new_sl = hf + pad
    #         if new_sl < self.average_stop_loss:
    #             #self.stop_loss = self.position.qty, new_sl
    #             self.vars['sl_progression'] = new_sl

    # def on_reduced_position(self, order):
    #     """Detects if TP was hit (partial reduction)"""
    #     self.vars['exit_type'] = 1  # Take Profit
    #     self.log(f"✅ Take Profit executed at {order.price}", 'info')

    # def on_close_position(self, order):
    #     """Detects complete closure and determines if it's TP or SL"""
    #     # Record the index of the last trade to space out trades
    #     self.vars['last_trade_index'] = self.index
        
    #     # Reset sl_progression to 0
    #     self.vars['sl_progression'] = 0
        
    #     # If the position closes in profit, it's probably the TP
    #     if self.position.pnl > 0:
    #         self.vars['exit_type'] = 1  # Take Profit
    #         self.log(f"✅ Position closed by Take Profit at {order.price} | PnL: {self.position.pnl:.2f}", 'info')
    #     else:
    #         # If at a loss, it's the stop loss
    #         self.vars['exit_type'] = -1  # Stop Loss
    #         self.log(f"❌ Position closed by Stop Loss at {order.price} | PnL: {self.position.pnl:.2f}", 'info')

    def after(self):
        """Display indicators and levels on the chart"""
        # Display HMA and trend EMA
        self.add_line_to_candle_chart('HMA Fast', self.hma_fast[-1], color='blue')
        self.add_line_to_candle_chart('HMA Slow', self.hma_slow[-1], color='orange')
        self.add_line_to_candle_chart('Trend EMA', self.trend_ema, color='purple')
        
        # Display stop loss progression (continuous line)
        sl_value = self.vars.get('sl_progression', 0)
        if sl_value != 0:
            self.add_line_to_candle_chart('SL Progression', sl_value, color='red')
        
        # Display SL and TP if position is open
        if self.is_open:
            if self.average_take_profit:
                self.add_horizontal_line_to_candle_chart(
                    'Take Profit', 
                    self.average_take_profit, 
                    color='green',
                    line_width=2
                )
        
        # Graphique Williams %R
        self.add_extra_line_chart('Williams %R', 'Williams %R', self.williams_r, color='blue')
        self.add_horizontal_line_to_extra_chart('Williams %R', 'Overbought', -20, color='red')
        self.add_horizontal_line_to_extra_chart('Williams %R', 'Oversold', -80, color='green')
        self.add_horizontal_line_to_extra_chart('Williams %R', 'Middle', -50, color='gray')
        
        # Graphique CMO
        self.add_extra_line_chart('CMO', 'CMO', self.cmo, color='purple')
        self.add_horizontal_line_to_extra_chart('CMO', 'Overbought', 50, color='red')
        self.add_horizontal_line_to_extra_chart('CMO', 'Oversold', -50, color='green')
        self.add_horizontal_line_to_extra_chart('CMO', 'Zero', 0, color='gray')
        
        # Graphique Choppiness Oscillator
        self.add_extra_line_chart('CHOP', 'Choppiness', self.chop, color='orange')
        self.add_horizontal_line_to_extra_chart('CHOP', 'Choppy Zone', 61.8, color='red')
        self.add_horizontal_line_to_extra_chart('CHOP', 'Trending Zone', 38.2, color='green')
        self.add_horizontal_line_to_extra_chart('CHOP', 'Middle', 50, color='gray')
        
        # Additional chart to show TP/SL exits
        # 1 = Take Profit (green), -1 = Stop Loss (red), 0 = none
        exit_type = self.vars.get('exit_type', 0)
        color = 'green' if exit_type == 1 else 'red' if exit_type == -1 else 'gray'
        self.add_extra_line_chart('Exit Type', 'TP/SL', exit_type, color=color)
        
        # Reference lines
        self.add_horizontal_line_to_extra_chart('Exit Type', 'TP Level', 1, color='green')
        self.add_horizontal_line_to_extra_chart('Exit Type', 'SL Level', -1, color='red')
        self.add_horizontal_line_to_extra_chart('Exit Type', 'Neutral', 0, color='gray')
        

