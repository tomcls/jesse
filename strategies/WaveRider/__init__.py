from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class WaveRider(Strategy):
    
    @property 
    def trend(self):

        di = ta.di(self.candles)
        adx = ta.adx(self.candles)

        if di.plus > di.minus and adx > 50:
            return 1
        elif di.plus < di.minus and adx > 50:
            return -1
        else:
            return 0

    @property
    def ma_trend(self):
        fast_ma = ta.sma(self.candles, 25)
        slow_ma = ta.sma(self.candles, 50)
        if fast_ma > slow_ma:
            return 1
        elif fast_ma < slow_ma:
            return -1
        else:
            return 0

    @property
    def cci(self):
        c= ta.cci(self.candles)
        if c > 100:
            return -1
        elif c < -100:
            return 1
        else:
            return 0

    @property
    def atr(self):
        return ta.atr(self.candles)

       
    def should_long(self) -> bool:
        return self.trend == 1 and self.cci == 1 and self.ma_trend == 1 

    def should_short(self) -> bool:
        # For futures trading only
        return self.trend == -1 and self.cci == -1 and self.ma_trend == -1 
        
    def go_long(self):
        entry = self.price
        stop = self.price - self.atr * 3.5
        qty = utils.risk_to_qty(self.available_margin, 5, entry, stop, fee_rate=self.fee_rate)
        self.buy = qty*5, entry

    def go_short(self):
        # For futures trading only
        entry = self.price
        stop = self.price + self.atr * 3.5
        qty = utils.risk_to_qty(self.available_margin, 5, entry, stop, fee_rate=self.fee_rate)
        self.sell = qty*5, entry

    def on_open_position(self, order) -> None:
        if self.is_long:
            self.stop_loss = self.position.qty, self.price - self.atr * 3,5
            self.take_profit = self.position.qty, self.price + self.atr * 3,5
        elif self.is_short:
            self.stop_loss = self.position.qty, self.price + self.atr * 3,5
            self.take_profit = self.position.qty, self.price - self.atr * 3,5