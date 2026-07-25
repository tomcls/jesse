import numpy as np
from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils





class MeanRevLogBTC(Strategy):
    def _log_bb(close: np.ndarray, period: int = 20, mult: float = 2.0):
        """
        Bollinger Bands on log(close).
        Returns (lower_price, mid_price, upper_price, zscore)
        """
        x = np.log(close.astype(float))
        # rolling mean/std (naïf, mais OK pour commencer)
        if len(x) < period:
            return np.nan, np.nan, np.nan, np.nan

        window = x[-period:]
        mu = window.mean()
        sd = window.std(ddof=0)  # population std

        lower_log = mu - mult * sd
        upper_log = mu + mult * sd

        # convert back to price space
        lower = float(np.exp(lower_log))
        mid = float(np.exp(mu))
        upper = float(np.exp(upper_log))

        z = float((x[-1] - mu) / sd) if sd > 0 else 0.0
        return lower, mid, upper, z
    @property
    def higher_tf_candles(self):
        return self.get_candles(self.exchange, self.symbol, '4h')

    @property
    def rsi_4h(self):
        return ta.rsi(self.higher_tf_candles)

    @property
    def adx_4h(self):
        return ta.adx(self.higher_tf_candles)

    @property
    def adx_1h(self):
        return ta.adx(self.candles)

    @property
    def supertrend_dir_4h(self):
        s = ta.supertrend(self.higher_tf_candles)
        return 1 if self.price > s.trend else -1

    @property
    def atr(self):
        return ta.atr(self.candles)

    @property
    def log_bb(self):
        close = self.candles[:, 2]  # close
        lower, mid, upper, z = self._log_bb(close, period=20, mult=2.0)
        return lower, mid, upper, z

    
    def should_long(self) -> bool:
        lower, mid, upper, z = self.log_bb
        return (
            self.rsi_4h > 70 and
            self.supertrend_dir_4h == 1 and
            self.adx_4h > 40 and
            self.adx_1h > 20 and
            z < -2.0  # déviation forte sous la moyenne en log
        )

    def should_short(self) -> bool:
        lower, mid, upper, z = self.log_bb
        return (
            self.rsi_4h < 30 and
            self.supertrend_dir_4h == -1 and
            self.adx_4h > 40 and
            self.adx_1h > 20 and
            z > +2.0
        )

    def go_long(self):
        lower, mid, upper, z = self.log_bb
        entry_price = lower
        stop_loss_price = entry_price - (6 * self.atr)

        qty = utils.risk_to_qty(
            self.available_margin, 10, entry_price, stop_loss_price, fee_rate=self.fee_rate
        )
        self.buy = qty, entry_price

    def go_short(self):
        lower, mid, upper, z = self.log_bb
        entry_price = upper
        stop_loss_price = entry_price + (6 * self.atr)

        qty = utils.risk_to_qty(
            self.available_margin, 10, entry_price, stop_loss_price, fee_rate=self.fee_rate
        )
        self.sell = qty, entry_price

    def on_open_position(self, order):
        lower, mid, upper, z = self.log_bb
        if self.is_long:
            self.stop_loss = self.position.qty, self.position.entry_price - (6 * self.atr)
            self.take_profit = self.position.qty, upper
        elif self.is_short:
            self.stop_loss = self.position.qty, self.position.entry_price + (6 * self.atr)
            self.take_profit = self.position.qty, lower

    def should_cancel_entry(self) -> bool:
        return True
