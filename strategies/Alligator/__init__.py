from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class Alligator(Strategy):
    @property
    def alligator(self):
        return ta.alligator(self.candles)

    @property
    def trend(self):
        if self.price > self.alligator.lips > self.alligator.teeth > self.alligator.jaw:
            return 1
        if self.price < self.alligator.lips < self.alligator.teeth < self.alligator.jaw:
            return -1
        return 0

    @property
    def long_term_candles(self):
        big_tf = '4h'
        if self.timeframe == '4h':
            big_tf = '6h'
        return self.get_candles(self.exchange, self.symbol, big_tf)

    @property
    def adx(self):
        return ta.adx(self.candles) > 30

    

    @property
    def big_alligator(self):
        return ta.alligator(self.long_term_candles)

    
    @property
    def cmo(self):
        return ta.cmo(self.candles, 14) 
    @property
    def srsi(self):
        return ta.srsi(self.candles).k

    @property
    def big_trend(self):
        if self.price > self.big_alligator.lips > self.big_alligator.teeth > self.big_alligator.jaw:
            return 1
        if self.price < self.big_alligator.lips < self.big_alligator.teeth < self.big_alligator.jaw:
            return -1
        return 0

    @property 
    def long_term_ma(self):
        e= ta.ema(self.long_term_candles, 100)
        if self.price > e:
            return 1
        if self.price < e:
            return -1
    
    def should_long(self) -> bool:
        return self.trend == 1 and self.adx and self.big_trend == 1 and self.long_term_ma == 1 and self.cmo > 30 and self.srsi < 20

    def should_short(self) -> bool:
        # For futures trading only
        return self.trend == -1 and self.adx and self.big_trend == -1 and self.long_term_ma == -1 and self.cmo < -30 and self.srsi > 80
        
    def go_long(self):
        entry = self.price
        stop = entry - ta.atr(self.candles) * 2
        qty = utils.risk_to_qty(self.available_margin, 3, entry, stop, fee_rate=self.fee_rate)
        self.buy = qty*5, entry

    def go_short(self):
        entry = self.price
        stop = entry + ta.atr(self.candles) * 2
        qty = utils.risk_to_qty(self.available_margin, 3, entry, stop, fee_rate=self.fee_rate)
        self.sell = qty*5, entry


    # def update_position(self) -> None:
    #     if self.is_long and self.trend != 1:
    #         self.liquidate()
    #     elif self.is_short and self.trend != -1:
    #         self.liquidate()

    def on_open_position(self, order) -> None:
        if self.is_long:
            self.stop_loss = self.position.qty, self.price - ta.atr(self.candles) * 2
            self.take_profit = self.position.qty, self.price + 2 * ta.atr(self.candles)
        elif self.is_short:
            self.stop_loss = self.position.qty, self.price + ta.atr(self.candles) * 2
            self.take_profit = self.position.qty, self.price - 2 * ta.atr(self.candles)

    def should_cancel_entry(self) -> bool:
        return True