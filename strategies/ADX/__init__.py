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
    @property
    def di(self):
        return ta.di(self.candles)

    @property
    def adx_value(self):
        return ta.adx(self.candles)

    @property
    def sma50(self):
        return ta.sma(self.candles, self.hp['sma_period'])

    @property
    def williams_r(self):
        return ta.willr(self.candles)

    @property
    def hh30(self):
        # Highest high of last N completed candles
        highs = self.candles[:-1][:, 3]
        if highs.size < self.hp['extreme_period']:
            return None
        return highs[-self.hp['extreme_period']:].max()

    @property
    def ll30(self):
        # Lowest low of last N completed candles
        lows = self.candles[:-1][:, 4]
        if lows.size < self.hp['extreme_period']:
            return None
        return lows[-self.hp['extreme_period']:].min()

    def should_long(self) -> bool:
        d = self.di
        if d is None:
            return False
        w = self.williams_r
        return d.plus > d.minus and self.adx_value > self.hp['adx_threshold'] and w < self.hp['willr_long_threshold']

    def should_short(self) -> bool:
        # For futures trading only
        d = self.di
        if d is None:
            return False
        w = self.williams_r
        return d.plus < d.minus and self.adx_value > self.hp['adx_threshold'] and w > self.hp['willr_short_threshold']
        
    def go_long(self):
        entry = self.price  # market order
        # place a provisional stop for position sizing using SMA50 as intended SL anchor
        stop = self.sma50 if self.sma50 is not None else (entry - ta.atr(self.candles) * 2)
        qty = utils.risk_to_qty(self.leveraged_available_margin, 3, entry, stop, fee_rate=self.fee_rate)
        self.buy = qty , entry

    def go_short(self):
        # For futures trading only
        entry = self.price  # market order
        stop = self.sma50 if self.sma50 is not None else (entry + ta.atr(self.candles) * 2)
        qty = utils.risk_to_qty(self.leveraged_available_margin, 3, entry, stop, fee_rate=self.fee_rate)
        self.sell = qty, entry

    def on_open_position(self, order) -> None:
        # Set stop-loss = SMA50 and take-profit = 30-candle extremes
        if self.is_long:
            if self.sma50 is not None:
                self.stop_loss = self.position.qty, self.sma50
            if self.hh30 is not None:
                self.take_profit = self.position.qty, self.hh30
        elif self.is_short:
            if self.sma50 is not None:
                self.stop_loss = self.position.qty, self.sma50
            if self.ll30 is not None:
                self.take_profit = self.position.qty, self.ll30

    def update_position(self) -> None:
        # Close if entry is opposite of the current trend
        d = self.di
        if d is None:
            return
        if self.is_long and d.plus < d.minus and self.adx_value > self.hp['adx_threshold']:
            self.liquidate()
        elif self.is_short and d.plus > d.minus and self.adx_value > self.hp['adx_threshold']:
            self.liquidate()

    def hyperparameters(self) -> list:
        return [
            {'name': 'adx_threshold', 'type': int, 'min': 40, 'max': 60, 'default': 50, 'step': 1 },
            {'name': 'sma_period', 'type': int, 'min': 20, 'max': 200, 'default': 50, 'step': 1},
            {'name': 'extreme_period', 'type': int, 'min': 40, 'max': 50, 'default': 30, 'step': 1},
            {'name': 'willr_long_threshold', 'type': int, 'min': -90, 'max': -70, 'default': -80, 'step': 1},
            {'name': 'willr_short_threshold', 'type': int, 'min': -30, 'max': -10, 'default': -20, 'step': 1},
        ]
    def dna(self)->str:
        return 'eyJhZHhfdGhyZXNob2xkIjogNDgsICJleHRyZW1lX3BlcmlvZCI6IDg3LCAicmlza19wY3QiOiAzLjAsICJzbWFfcGVyaW9kIjogNDksICJ3aWxscl9sb25nX3RocmVzaG9sZCI6IC02NSwgIndpbGxyX3Nob3J0X3RocmVzaG9sZCI6IC0zfQ=='