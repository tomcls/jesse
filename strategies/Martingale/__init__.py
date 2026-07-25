from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class Martingale(Strategy):

    @property
    def bb(self):
        return ta.bollinger_bands(self.candles)

    @property
    def margin(self):
        return ta.stddev(self.candles) * 2

    def should_long(self) -> bool:
        return True

    def go_long(self):
        entry = self.bb.lowerband
        qty = utils.size_to_qty(self.available_margin * 0.5, entry, fee_rate = self.fee_rate)
        self.buy = qty, entry

    def _submit_exit_orders(self):
        # take-profit
        tp = self.position.entry_price + self.margin * 2
        self.take_profit = self.position.qty, tp
        # next entry
        next_entry_price = self.price - self.margin * 2
        next_entry_qty  = self.position.qty
        self.buy = next_entry_qty, next_entry_price
        
   

    def on_open_position(self, order):

        self._submit_exit_orders()

    def on_increased_position (self, order):

        self._submit_exit_orders()

    def should_cancel_entry(self):   
        return True