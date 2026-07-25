from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class IchimokuCloud(Strategy):
    
    # === Core indicators / helpers ===
    @property
    def small_trend(self):
        c = ta.ichimoku_cloud(self.candles)
        if c.conversion_line > c.base_line:
            return 1
        else:
            return -1

    @property
    def big_trend(self):
        c = ta.ichimoku_cloud(self.candles)
        if c.span_a > c.span_b:
            return 1
        else:
            return -1
    @property
    def adx(self):
        return ta.adx(self.candles) > 50
    @property
    def chop(self):
        return ta.chop(self.candles) < 50

    def should_long(self) -> bool:
        return self.small_trend == 1 and self.big_trend == 1 and self.adx and self.chop

    def should_short(self) -> bool:
        return self.small_trend == -1 and self.big_trend == -1 and self.adx and self.chop

    def go_long(self):
        entry = self.price - ta.atr(self.candles)
        stop = entry - ta.atr(self.candles) * 2.5
        qty = utils.risk_to_qty(self.available_margin, 3, entry, stop, fee_rate=self.fee_rate)
        self.buy =  qty *5, entry

    def go_short(self):
        entry = self.price + ta.atr(self.candles)
        stop = entry + ta.atr(self.candles) * 2.5
        qty = utils.risk_to_qty(self.available_margin, 3, entry, stop, fee_rate=self.fee_rate)
        self.sell = qty *5, entry

    def should_cancel_entry(self) -> bool:
        return True

    def on_open_position(self, order) -> None:
        if self.is_long:
            self.stop_loss = self.position.qty, self.position.entry_price - ta.atr(self.candles) * 2.5
        elif self.is_short:
            self.stop_loss = self.position.qty, self.position.entry_price + ta.atr(self.candles) * 2.5

    def update_position(self) -> None:
        if self.is_long:
            if self.small_trend == -1:
                self.liquidate()
        elif self.is_short:
            if self.small_trend == 1:
                self.liquidate()