from typing import List
import numpy as np

from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class Crypto5MinPro(Strategy):

    """
    Crypto 5 Min Pro Strategy
    Write me a strategy with the following rules:
    - if we are in a up trend market, we want to look for long positions:
        -- take a long position when the price is below the vwap and touch the bolinger bands lower band.
    - if the market is in a down trend, we want to look for short positions:
        -- take a short position when the price is above the vwap and touch the bolinger bands upper band.
    - we have a stop loss of 2 * ATR.
    - we have a take profit of 4 * ATR.
    - we have a risk management of 3% of the account per trade.
    - we want to use market order to enter the trade.
    """

    def __init__(self):
        super().__init__()
        self.initial_stop_loss = None
    @property
    def bb(self):
        """Bollinger Bands"""
        return ta.bollinger_bands(self.candles[:-1],30,4)
    @property
    def atr(self):
        """Average True Range"""
        return ta.atr(self.candles)
    @property
    def atr_sma(self):
        """Average True Range"""
        atr_seq = ta.atr(self.candles, sequential=True)
        return ta.sma(atr_seq, 20)

    @property
    def sma_4h(self):
        c = self.get_candles(self.exchange, self.symbol, '4h')
        return ta.sma(c, 200)
   
    @property
    def donchian(self):
        return ta.donchian(self.candles[:-1], 30)
    

   
    @property
    def adx(self):
        return ta.adx(self.candles)

    @property
    def chop(self):
        return ta.chop(self.candles)
   

    def should_long(self) -> bool:
        """ """
        return (self.atr > self.atr_sma and
                self.price > self.sma_4h and
                self.low <= self.bb.lowerband)

    def should_short(self) -> bool:
        """ """
        return (self.atr > self.atr_sma and
                self.price < self.sma_4h and
                self.high >= self.bb.upperband)

    def go_long(self):
        """Execute long position with market order and 3% risk management"""
        entry_price = self.price
        stop_loss = entry_price - (self.atr * 5)
        qty = utils.risk_to_qty(self.available_margin, 3, entry_price, stop_loss, fee_rate=self.fee_rate)
        self.buy = qty, entry_price  # Market order

    def go_short(self):
        """Execute short position with market order and 3% risk management"""
        entry_price = self.price
        stop_loss = entry_price + (self.atr * 5)
        qty = utils.risk_to_qty(self.available_margin, 3, entry_price, stop_loss, fee_rate=self.fee_rate)
        self.sell = qty, entry_price  # Market order

    def on_open_position(self, order):
        """Set stop loss and take profit when position opens"""
        if self.is_long:
            sl = self.position.entry_price - (self.atr * 5)
            self.stop_loss = self.position.qty, sl
        elif self.is_short:
            sl = self.position.entry_price + (self.atr * 5)
            self.stop_loss = self.position.qty, sl

    def update_position(self) -> None:
        """Take profit when price touches Bollinger Bands"""
        if self.is_long and self.high >= self.bb.upperband:
            self.liquidate()

        elif self.is_short and self.low <= self.bb.lowerband:
            self.liquidate()

    

    def after(self) -> None:
        """Add indicators to chart for visualization"""
        # self.add_line_to_candle_chart('VWAP', self.vwap)
        self.add_line_to_candle_chart('BB_Upper', self.bb.upperband, 'green')
        self.add_line_to_candle_chart('BB_Lower', self.bb.lowerband, 'red')
        self.add_line_to_candle_chart('SMA200', self.sma_4h, 'white')

        