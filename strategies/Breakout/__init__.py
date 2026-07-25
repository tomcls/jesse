from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils
import numpy as np


class Breakout(Strategy):
    @property
    def donchian(self):
        return ta.donchian(self.candles[:-1], period=30)
    
    @property
    def atr(self):
        return ta.atr(self.candles)
    
    @property
    def atr_sma(self):
        atr_seq = ta.atr(self.candles, sequential=True)
        return ta.sma(atr_seq, period=20)
    @property
    def sma_4h(self):
        c = self.get_candles(self.exchange, self.symbol, '4h')
        return ta.sma(c, period=200)
    
    @property
    def volatility_condition(self):
        return self.atr > self.atr_sma

    def should_long(self) -> bool:
        return (self.price > self.donchian.upperband and 
                self.price > self.sma_4h and 
                self.volatility_condition)

    def should_short(self) -> bool:
        return (self.price < self.donchian.lowerband and 
                self.price < self.sma_4h and 
                self.volatility_condition)
        
    def go_long(self):
        entry = self.price
        stop = entry - 5 * self.atr
        qty = utils.risk_to_qty(self.available_margin, 3, entry, stop, fee_rate=self.fee_rate)
        self.buy = qty, entry

    def go_short(self):
        entry = self.price
        stop = entry + 5 * self.atr
        qty = utils.risk_to_qty(self.available_margin, 3, entry, stop, fee_rate=self.fee_rate)
        self.sell = qty, entry
    
    def should_cancel_entry(self) -> bool:
        return True
    
    def on_open_position(self, order) -> None:
        if self.is_long:
            self.stop_loss = self.position.qty, self.price - 5 * self.atr
            self.take_profit = self.position.qty, self.price + 10 * self.atr
        elif self.is_short:
            self.stop_loss = self.position.qty, self.price + 5 * self.atr
            self.take_profit = self.position.qty, self.price - 10 * self.atr
    
    def update_position(self) -> None:
        if self.is_long:
            self.stop_loss = self.position.qty, max(self.average_stop_loss, self.donchian.lowerband)
        elif self.is_short:
            self.stop_loss = self.position.qty, min(self.average_stop_loss, self.donchian.upperband)
