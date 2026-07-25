# Trending Strategy
# Directional Movement index
# Indicator
# if the oragne line is above the blue line it's a down uptrend
# if the blue line is above the oragne line it's a up trend
# Oscilator
# Willimas % range
# Write a adx strategy with those rules:
# 1 Long: di.plus > di.minus 
#    - ADX > 50
# 2 Short: di.plus < di.minus
#    - ADX > 50
# 3 Take-profit:
#    - long: Highest high of 30 candles
#    - short: Lowest low of 30 candles
   
# 4 Stop-loss:
#    - sma 50
# update position:
#     - close if entry is the opposite of the current trend

# 5 Risk management:
#     - Risk 3% of the account per trade.
#     - Use market order to enter the trade.

# 6 Entry:
# Please also use an oscilator for the entry of the strategy. If the value of the willilimas percentage 
# R is below minus 80, we want to look for the long positions, and if it's above minus 20, we want to look for short positions.

from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class ADX(Strategy):
    # =========================
    # Indicator accessors
    # =========================
    @property
    def di(self):
        return ta.di(self.candles)

    @property
    def adx_value(self):
        return ta.adx(self.candles)

    @property
    def sma_stop(self):
        # Stop anchor SMA with tunable period
        return ta.sma(self.candles, self.hp['sma_stop_period'])

    @property
    def williams_r(self):
        return ta.willr(self.candles)

    @property
    def hh_lookback(self):
        # Highest high of last N completed candles
        highs = self.candles[:-1][:, 3]
        lookback = self.hp['tp_lookback']
        if highs.size < lookback:
            return None
        return highs[-lookback:].max()

    @property
    def ll_lookback(self):
        # Lowest low of last N completed candles
        lows = self.candles[:-1][:, 4]
        lookback = self.hp['tp_lookback']
        if lows.size < lookback:
            return None
        return lows[-lookback:].min()

    def should_long(self) -> bool:
        d = self.di
        if d is None:
            return False
        w = self.williams_r
        return (
            d.plus > d.minus and
            self.adx_value > self.hp['adx_threshold'] and
            w < self.hp['wpr_long_max']
        )

    def should_short(self) -> bool:
        # For futures trading only
        d = self.di
        if d is None:
            return False
        # Respect spot exchanges: no shorts
        if self.is_spot_trading:
            return False
        w = self.williams_r
        return (
            d.plus < d.minus and
            self.adx_value > self.hp['adx_threshold'] and
            w > self.hp['wpr_short_min']
        )
        
    def go_long(self):
        entry = self.price  # market order
        # Provisional stop for sizing using SMA stop or ATR fallback
        atr = ta.atr(self.candles)
        fallback = entry - atr * self.hp['atr_fallback_mult']
        stop = self.sma_stop if self.sma_stop is not None else fallback
        qty = utils.risk_to_qty(
            self.available_margin,
          3, # self.hp['risk_percent'],
            entry,
            stop,
            fee_rate=self.fee_rate,
        )
        self.buy = qty , entry

    def go_short(self):
        # For futures trading only
        entry = self.price  # market order
        atr = ta.atr(self.candles)
        fallback = entry + atr * self.hp['atr_fallback_mult']
        stop = self.sma_stop if self.sma_stop is not None else fallback
        qty = utils.risk_to_qty(
            self.available_margin,
           3, # self.hp['risk_percent'],
            entry,
            stop,
            fee_rate=self.fee_rate,
        )
        self.sell = qty , entry

    def on_open_position(self, order) -> None:
        # Set stop-loss = SMA(stop_period) and take-profit = extremes over lookback
        if self.is_long:
            if self.sma_stop is not None:
                self.stop_loss = self.position.qty, self.sma_stop
            if self.hh_lookback is not None:
                self.take_profit = self.position.qty, self.hh_lookback
        elif self.is_short:
            if self.sma_stop is not None:
                self.stop_loss = self.position.qty, self.sma_stop
            if self.ll_lookback is not None:
                self.take_profit = self.position.qty, self.ll_lookback

    def update_position(self) -> None:
        # Close if entry is opposite of the current trend
        d = self.di
        if d is None:
            return
        if self.is_long and d.plus < d.minus and self.adx_value > self.hp['adx_threshold']:
            self.liquidate()
        elif self.is_short and d.plus > d.minus and self.adx_value > self.hp['adx_threshold']:
            self.liquidate()

    # =========================
    # Optimization
    # =========================
    def hyperparameters(self) -> list:
        return [
            {'name': 'adx_threshold', 'type': int, 'min': 20, 'max': 70, 'default': 50, 'step': 10},
            {'name': 'wpr_long_max', 'type': int, 'min': -100, 'max': -50, 'default': -80,'step': 10},
            {'name': 'wpr_short_min', 'type': int, 'min': -50, 'max': 0, 'default': -20,'step': 10},
            {'name': 'sma_stop_period', 'type': int, 'min': 20, 'max': 200, 'default': 50,'step': 10},
            {'name': 'tp_lookback', 'type': int, 'min': 10, 'max': 100, 'default': 30,'step': 10},
            {'name': 'atr_fallback_mult', 'type': float, 'min': 1.0, 'max': 4.0, 'step': 0.1, 'default': 2.0},
           # {'name': 'risk_percent', 'type': float, 'min': 0.5, 'max': 5.0, 'step': 0.5, 'default': 3.0},
            #{'name': 'size_mult', 'type': float, 'min': 0.5, 'max': 5.0, 'step': 0.5, 'default': 4.0},
        ]
    # def dna(self)->str:
    #     return 'eyJhZHhfdGhyZXNob2xkIjogNTAsICJhdHJfZmFsbGJhY2tfbXVsdCI6IDMuNywgInJpc2tfcGVyY2VudCI6IDQuNSwgInNpemVfbXVsdCI6IDQuNSwgInNtYV9zdG9wX3BlcmlvZCI6IDYwLCAidHBfbG9va2JhY2siOiA3MCwgIndwcl9sb25nX21heCI6IC03MCwgIndwcl9zaG9ydF9taW4iOiAtMzB9'
    #     return 'eyJhZHhfdGhyZXNob2xkIjogNTAsICJhdHJfZmFsbGJhY2tfbXVsdCI6IDMuOTAwMDAwMDAwMDAwMDAwNCwgInJpc2tfcGVyY2VudCI6IDEuNSwgInNpemVfbXVsdCI6IDIuMCwgInNtYV9zdG9wX3BlcmlvZCI6IDQwLCAidHBfbG9va2JhY2siOiA0MCwgIndwcl9sb25nX21heCI6IC03MCwgIndwcl9zaG9ydF9taW4iOiAtMzB9