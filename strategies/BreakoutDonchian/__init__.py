# write a breakout strategy with the following rules:
# - use a donchian channel with a perod of 30
# - Use atr for volatility and also a 20-period SMA of atr. only take trades when atr is above 20 period sma
# - use a long term 4 hour SMA to define trend.
# - Go long when price is above the donchian upperband and the tprice is above the 4h sma and volatility condition( ATR > ATR SMA) is met.
# - Do the opposite for short trades.
# - Enter at current price.
# - Risk 3% of the account per trade.
# - on position open set stop loss = entry - 5*ATR and take profit = entry + 10*ATR for longs and stop loss = entry + 5*ATR and take profit = entry - 10*ATR for shorts.
# - After opening a position, trail the stop loss using donchian channel: for longs move the stop toward the donchian
# lowerband and for shorts move the stop toward the donchian upperband but dont widen it beyond the prior/average stop. for shorts, do the opposite.

from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class BreakoutDonchian(Strategy):
    @property
    def donchian(self):
        return ta.donchian(self.candles, 30)

    @property
    def atr(self):
        return ta.atr(self.candles, 14)

    @property
    def atr_sma(self):
        return ta.sma(ta.atr(self.candles, 14, sequential=True), 20)

    @property
    def anchor_candles(self):
        return self.get_candles(self.exchange, self.symbol, '4h')

    @property
    def anchor_sma(self):
        return ta.sma(self.anchor_candles, 50)

    @property
    def volatility_ok(self):
        return self.atr > self.atr_sma

    def should_long(self) -> bool:
        return (
            self.price > self.donchian.upperband
            and self.price > self.anchor_sma
            and self.volatility_ok
        )

    def should_short(self) -> bool:
        return (
            self.price < self.donchian.lowerband
            and self.price < self.anchor_sma
            and self.volatility_ok
        )

    def should_cancel_entry(self) -> bool:
        return True

    def go_long(self):
        entry = self.price
        qty = utils.risk_to_qty(self.available_margin, 3, entry, entry - 5 * self.atr, fee_rate=self.fee_rate)
        self.buy = qty, entry

    def go_short(self):
        entry = self.price
        qty = utils.risk_to_qty(self.available_margin, 3, entry, entry + 5 * self.atr, fee_rate=self.fee_rate)
        self.sell = qty, entry

    def on_open_position(self, order) -> None:
        if self.is_long:
            self.stop_loss = self.position.qty, self.position.entry_price - 5 * self.atr
            self.take_profit = self.position.qty, self.position.entry_price + 10 * self.atr
        elif self.is_short:
            self.stop_loss = self.position.qty, self.position.entry_price + 5 * self.atr
            self.take_profit = self.position.qty, self.position.entry_price - 10 * self.atr

    def update_position(self):
        if self.is_long:
            self.stop_loss = self.position.qty, max(self.average_stop_loss, self.donchian.lowerband)
        elif self.is_short:
            self.stop_loss = self.position.qty, min(self.average_stop_loss, self.donchian.upperband)
