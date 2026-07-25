from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class HammersAndStars(Strategy):
    @property
    def atr(self):
        return ta.atr(self.candles)

    @property
    def ema_value(self):
        length = self.hp['ema_length']
        effective_length = 1 if length == 0 else length
        return ta.ema(self.candles, effective_length)

    @property
    def _has_prev_candle(self):
        return self.candles.shape[0] >= 2

    @property
    def _prev_high(self):
        return self.candles[-2, 3]

    @property
    def _prev_low(self):
        return self.candles[-2, 4]

    @property
    def _ema_filter_long(self):
        if self.hp['ema_length'] == 0:
            return True
        return self.price > self.ema_value

    @property
    def _ema_filter_short(self):
        if self.hp['ema_length'] == 0:
            return True
        return self.price < self.ema_value

    @property
    def _atr_filter(self):
        candle_range = abs(self.high - self.low)
        min_mult = self.hp['atr_min_mult']
        max_mult = self.hp['atr_max_mult']
        min_ok = candle_range >= min_mult * self.atr if min_mult > 0 else True
        max_ok = candle_range <= max_mult * self.atr if max_mult > 0 else True
        return min_ok and max_ok

    @property
    def _fib_levels(self):
        # bullFib and bearFib based on current candle (close of bar logic)
        fib_level = self.hp['fib_level']
        bull_fib = (self.low - self.high) * fib_level + self.high
        bear_fib = (self.high - self.low) * fib_level + self.low
        return bull_fib, bear_fib

    @property
    def _valid_hammer(self):
        if not self._has_prev_candle:
            return False
        bull_fib, _ = self._fib_levels
        lowest_body = min(self.price, self.open)
        return (
            lowest_body >= bull_fib
            and self.price != self.open
            and self._atr_filter
            and self._ema_filter_long
        )

    @property
    def _valid_star(self):
        if not self._has_prev_candle:
            return False
        _, bear_fib = self._fib_levels
        highest_body = max(self.price, self.open)
        return (
            highest_body <= bear_fib
            and self.price != self.open
            and self._atr_filter
            and self._ema_filter_short
        )

    def should_long(self) -> bool:
        return self._valid_hammer

    def should_short(self) -> bool:
        if self.is_spot_trading:
            return False
        return self._valid_star
        
    def go_long(self):
        # Replicate Pine logic for stop sizing
        stop_size = self.atr * self.hp['stop_atr_mult']
        base_stop_ref = self.low if self.low < self._prev_low else self._prev_low
        stop_price = base_stop_ref - stop_size
        entry = self.price
        qty = utils.risk_to_qty(
            self.available_margin, 
            self.hp['risk_percent'], 
            entry, 
            stop_price, 
            fee_rate=self.fee_rate
        )
        self.buy = qty, entry

    def go_short(self):
        # For futures trading only
        stop_size = self.atr * self.hp['stop_atr_mult']
        base_stop_ref = self.high if self.high > self._prev_high else self._prev_high
        stop_price = base_stop_ref + stop_size
        entry = self.price
        qty = utils.risk_to_qty(
            self.available_margin, 
            self.hp['risk_percent'], 
            entry, 
            stop_price, 
            fee_rate=self.fee_rate
        )
        self.sell = qty, entry

    def on_open_position(self, order) -> None:
        # Set SL/TP using same definitions as the signal candle
        stop_size = self.atr * self.hp['stop_atr_mult']
        rr = self.hp['rr']

        if self.is_long:
            base_stop_ref = self.low if self.low < self._prev_low else self._prev_low
            stop_price = base_stop_ref - stop_size
            distance = self.position.entry_price - stop_price
            target_price = self.position.entry_price + distance * rr
            self.stop_loss = self.position.qty, stop_price
            self.take_profit = self.position.qty, target_price
        elif self.is_short:
            base_stop_ref = self.high if self.high > self._prev_high else self._prev_high
            stop_price = base_stop_ref + stop_size
            distance = stop_price - self.position.entry_price
            target_price = self.position.entry_price - distance * rr
            self.stop_loss = self.position.qty, stop_price
            self.take_profit = self.position.qty, target_price

    def after(self) -> None:
        # Draw EMA if enabled
        if self.hp['ema_length'] != 0:
            self.add_line_to_candle_chart('HSS EMA', self.ema_value)
        # Draw current SL/TP if in a position
        if self.is_open:
            if self.average_stop_loss:
                self.add_line_to_candle_chart('HSS Stop', self.average_stop_loss)
            if self.average_take_profit:
                self.add_line_to_candle_chart('HSS Target', self.average_take_profit)

    def should_cancel_entry(self) -> bool:
        return False

    def watch_list(self) -> list:
        return [
            ('ema_len', self.hp['ema_length']),
            ('ema', self.ema_value),
            ('atr', self.atr),
            ('valid_hammer', 1 if self._valid_hammer else 0),
            ('valid_star', 1 if self._valid_star else 0),
        ]

    def hyperparameters(self) -> list:
        return [
            {'name': 'ema_length', 'type': int, 'min': 0, 'max': 200, 'default': 50},
            {'name': 'atr_min_mult', 'type': float, 'min': 0.0, 'max': 3.0, 'default': 0.0},
            {'name': 'atr_max_mult', 'type': float, 'min': 0.0, 'max': 5.0, 'default': 3.0},
            {'name': 'stop_atr_mult', 'type': float, 'min': 0.5, 'max': 5.0, 'default': 1},
            {'name': 'rr', 'type': float, 'min': 0.5, 'max': 5.0, 'default': 1.0},
            {'name': 'fib_level', 'type': float, 'min': 0.2, 'max': 0.8, 'default': 0.333},
            {'name': 'risk_percent', 'type': float, 'min': 0.25, 'max': 5.0, 'default': 5.0},
        ]
