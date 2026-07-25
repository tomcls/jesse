from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class SwingTrading(Strategy):

    @property
    def trend(self):

        e1 = ta.ema(self.candles, 21)
        e2 = ta.ema(self.candles, 50)
        e3 = ta.ema(self.candles, 100)
        if e3 < e2 < e1 < self.price:
            return 1
        elif e3 > e2 > e1 > self.price:
            return -1
        else:
            return 0
    @property
    def adx(self):
        return ta.adx(self.candles) > 25

   
    
    def should_long(self) -> bool:
        return self.trend == 1 and self.adx

    def should_short(self) -> bool:
        return self.trend == -1 and self.adx
        
    def go_long(self):
        entry = self.price
        stop = entry - ta.atr(self.candles) * 2
        #qty = utils.size_to_qty(self.balance, entry, fee_rate=self.fee_rate) 
        qty = utils.risk_to_qty(self.available_margin, 3, entry, stop, fee_rate=self.fee_rate)
        self.buy = qty*1.5, entry

    def go_short(self):
        entry = self.price
        stop = entry + ta.atr(self.candles) * 2
        # qty = utils.size_to_qty(self.balance, entry, fee_rate=self.fee_rate) 
        qty = utils.risk_to_qty(self.available_margin, 3, entry, stop, fee_rate=self.fee_rate)
        self.sell = qty*1.5, entry

    def on_open_position(self, order) -> None:
        if self.is_long:
            self.stop_loss = self.position.qty, self.price - ta.atr(self.candles) * 2
            self.take_profit = self.position.qty/2, self.price + 3 * ta.atr(self.candles)
        elif self.is_short:
            self.stop_loss = self.position.qty, self.price + ta.atr(self.candles) * 2
            self.take_profit = self.position.qty/2, self.price - 3 * ta.atr(self.candles)

    def on_reduced_position(self, order) -> None:
        if self.is_long:
            self.stop_loss = self.position.qty, self.position.entry_price
        elif self.is_short:
            self.stop_loss = self.position.qty, self.position.entry_price

    def update_position(self) -> None:
        if self.reduced_count == 1:
            if self.is_long:
                self.stop_loss = self.position.qty, max(self.price - 2 * ta.atr(self.candles), self.position.entry_price)
            elif self.is_short:
                self.stop_loss = self.position.qty, min(self.price + 2 * ta.atr(self.candles), self.position.entry_price)

    def should_cancel_entry(self) -> bool:
        return True