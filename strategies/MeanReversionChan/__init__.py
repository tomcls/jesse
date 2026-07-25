from jesse.strategies import Strategy
import jesse.indicators as ta
import numpy as np


class MeanReversionChan(Strategy):

    # =========================
    # Parameters (align Pine)
    # =========================
    @property
    def z_len(self): return 20

    @property
    def z_entry(self): return 3.5

    @property
    def z_exit_band(self): return 0.25

    @property
    def atr_period(self): return 14

    @property
    def atr_mult(self): return 3

    @property
    def max_bars_in_trade(self): return 0  # 0 = disabled

    @property
    def capital_pct(self): return 300.0

    @property
    def risk_pct(self): return 0.5

    # =========================
    # Indicators
    # =========================
    @property
    def atr(self):
        return ta.atr(self.candles, self.atr_period)

    def _zscore(self, closes):
        if len(closes) < self.z_len:
            return 0
        window = closes[-self.z_len:]
        sd = np.std(window, ddof=1)
        if sd == 0:
            return 0
        return (window[-1] - np.mean(window)) / sd

    @property
    def z(self):
        return self._zscore(self.candles[:, 2])

    @property
    def z_prev(self):
        return self._zscore(self.candles[:-1, 2])

    # =========================
    # Conditions
    # =========================
    def should_long(self):
        return (not self.position.is_open) and self.z_prev <= -self.z_entry and ta.adx(self.candles) < 25

    def should_short(self):
        return (not self.position.is_open) and self.z_prev >= self.z_entry and ta.adx(self.candles) < 25

    # =========================
    # Position sizing (CORE)
    # =========================
    def _equity(self):
        return float(self.balance)

    def _qty(self):
        equity = self._equity()
        stop_dist = self.atr * self.atr_mult

        notional_target = equity * (self.capital_pct / 100)
        qty_notional = notional_target / self.price

        risk_usd = equity * (self.risk_pct / 100)
        qty_risk = risk_usd / stop_dist if stop_dist > 0 else qty_notional

        return max(min(qty_notional, qty_risk), 0)

    # =========================
    # Entries
    # =========================
    def go_long(self):
        qty = float(self._qty())
        self.buy = (qty, float(self.price))

    def go_short(self):
        qty = float(self._qty())
        self.sell = (qty, float(self.price))

    # =========================
    # Stop
    # =========================
    def on_open_position(self, order):
        sl_dist = self.atr * self.atr_mult

        if self.is_long:
            self.stop_loss = self.position.qty, self.position.entry_price - sl_dist
        else:
            self.stop_loss = abs(self.position.qty), self.position.entry_price + sl_dist

    # =========================
    # Exits
    # =========================
    def update_position(self):
        if abs(self.z) <= self.z_exit_band:
            self.liquidate()
            return

        if self.max_bars_in_trade > 0:
            self.position_age += 1
            if self.position_age >= self.max_bars_in_trade:
                self.liquidate()

    def should_cancel_entry(self):
        return False

    def after(self) -> None:
        """Add Z-score bands to chart"""
        if len(self.candles) >= self.z_len:
            prices = self.candles[:, 2]
            mean = np.mean(prices[-self.z_len:])
            std = np.std(prices[-self.z_len:], ddof=1)

            # Plot mean line
            self.add_line_to_candle_chart('Mean', mean)

            # Plot Z-score entry bands
            upper_band = mean + self.z_entry * std
            lower_band = mean - self.z_entry * std

            self.add_line_to_candle_chart('Upper Band', upper_band, color='red')
            self.add_line_to_candle_chart('Lower Band', lower_band, color='red')

            # Plot Z-score exit bands
            upper_exit = mean + self.z_exit_band * std
            lower_exit = mean - self.z_exit_band * std

            self.add_line_to_candle_chart('Upper Exit', upper_exit, color='green')
            self.add_line_to_candle_chart('Lower Exit', lower_exit, color='green')

        # Add ADX and Directional Indicators to separate chart
        adx_value = ta.adx(self.candles)
        self.add_extra_line_chart('ADX', 'ADX', adx_value)

        # Add +DI and -DI to the same chart
        di_values = ta.di(self.candles)
        self.add_extra_line_chart('ADX', '+DI', di_values.plus, color='green')
        self.add_extra_line_chart('ADX', '-DI', di_values.minus, color='red')

        # Add horizontal reference lines for ADX levels
        self.add_horizontal_line_to_extra_chart('ADX', 'Trend Threshold', 25, 'orange')
