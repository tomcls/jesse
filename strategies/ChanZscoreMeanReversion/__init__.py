from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils
import numpy as np


class ChanZscoreMeanReversion(Strategy):
    def __init__(self):
        super().__init__()
        self.bars_in_position = 0
        self.last_entry_index = -1

    @property
    def z_len(self):
        return 20  # Z-score length (MA & StDev)

    @property
    def z_entry_threshold(self):
        return 2.0  # Entry threshold |z| ≥

    @property
    def z_exit_band(self):
        return 0.2  # Exit band (|z| ≤)

    @property
    def use_atr_stop(self):
        return True  # Use ATR safety stop

    @property
    def atr_period(self):
        return 14  # ATR period

    @property
    def atr_multiplier(self):
        return 2.5  # ATR stop multiplier

    @property
    def max_bars_in_trade(self):
        return 0  # Max bars in trade (0=disable)

    @property
    def capital_percentage(self):
        return 300.0  # Target notional (% of equity)

    @property
    def risk_percentage(self):
        return 2  # Risk cap (% equity per trade

    @property
    def z_score(self):
        """Calculate Z-score: (price - SMA) / StdDev"""
        if len(self.candles) < self.z_len:
            return 0.0

        # Use closing prices for calculation
        prices = self.candles[:, 2]  # close prices
        mean = np.mean(prices[-self.z_len:])
        std = np.std(prices[-self.z_len:], ddof=1)  # sample standard deviation

        if std == 0:
            return 0.0

        return (self.price - mean) / std

    @property
    def prev_z_score(self):
        """Get previous bar's Z-score"""
        if len(self.candles) < self.z_len + 1:
            return 0.0

        # Use closing prices for calculation
        prices = self.candles[:, 2]  # close prices
        mean = np.mean(prices[-self.z_len-1:-1])  # previous period
        std = np.std(prices[-self.z_len-1:-1], ddof=1)

        if std == 0:
            return 0.0

        prev_price = self.candles[-2, 2]  # previous close
        return (prev_price - mean) / std

    @property
    def atr(self):
        return ta.atr(self.candles, self.atr_period)

    def should_long(self) -> bool:
        # Long when previous Z-score <= -entry_threshold
        return self.prev_z_score <= -self.z_entry_threshold

    def should_short(self) -> bool:
        # Short when previous Z-score >= entry_threshold
        return self.prev_z_score >= self.z_entry_threshold

    def go_long(self):
        # Calculate position size
        qty = utils.risk_to_qty(self.available_margin, 3, self.price, self.price - self.atr * 2.5, fee_rate=self.fee_rate)
        self.buy = qty, self.price

    def go_short(self):
        # Calculate position size
        qty = utils.risk_to_qty(self.available_margin, 3, self.price, self.price + self.atr * 2.5, fee_rate=self.fee_rate)
        self.sell = qty, self.price

    def calculate_position_size(self):
        """Calculate position size based on notional target and risk cap"""
        equity = self.balance

        # Target notional sizing (leveraged notional)
        notional_target = equity * (self.capital_percentage / 100.0)
        qty_notional = notional_target / self.price

        # Risk cap sizing: limit loss at safety stop to riskPct% of equity
        risk_usd = equity * (self.risk_percentage / 100.0)

        # Stop distance using ATR
        stop_distance = self.atr_multiplier * self.atr
        qty_risk = risk_usd / stop_distance if stop_distance > 0 else qty_notional

        # Final qty = min(target notional qty, risk-capped qty)
        qty = min(qty_notional, qty_risk)

        # Ensure minimum quantity (avoid very small positions)
        qty = max(qty, 0.001)

        return qty

    def on_open_position(self, order):
        """Set safety stops when position is opened"""
        if self.use_atr_stop:
            if self.is_long:
                stop_price = self.price - (2.5 * self.atr)
                self.stop_loss = self.position.qty, stop_price
            elif self.is_short:
                stop_price = self.price + (2.5 * self.atr)
                self.stop_loss = self.position.qty, stop_price

        # Reset bars counter
        self.bars_in_position = 0
        self.last_entry_index = self.index

    def update_position(self):
        """Update position: check for exits"""
        self.bars_in_position += 1

        # Time stop
        if self.max_bars_in_trade > 0 and self.bars_in_position >= self.max_bars_in_trade:
            self.liquidate()
            return

        # Z-score exit: close when back near mean
        if abs(self.z_score) <= self.z_exit_band:
            self.liquidate()

    def should_cancel_entry(self) -> bool:
        return False

    def after(self) -> None:
        """Add visualization lines"""
        # Plot mean line
        mean_price = np.mean(self.candles[:, 2][-self.z_len:]) if len(self.candles) >= self.z_len else self.price
        self.add_line_to_candle_chart('Mean', mean_price)

        # Plot Z-score bands
        if len(self.candles) >= self.z_len:
            prices = self.candles[:, 2]
            mean = np.mean(prices[-self.z_len:])
            std = np.std(prices[-self.z_len:], ddof=1)

            upper_band = mean + self.z_entry_threshold * std
            lower_band = mean - self.z_entry_threshold * std

            self.add_line_to_candle_chart('Upper Band', upper_band)
            self.add_line_to_candle_chart('Lower Band', lower_band)

    def watch_list(self):
        """Monitor key indicators"""
        return [
            ('Z-Score', self.z_score),
            ('Prev Z-Score', self.prev_z_score),
            ('ATR', self.atr),
            ('Bars in Position', self.bars_in_position),
        ]
