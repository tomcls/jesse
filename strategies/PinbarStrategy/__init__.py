from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class PinbarStrategy(Strategy):
	@property
	def atr(self):
		# Use ATR(14) as per the PineScript
		return ta.atr(self.candles, 14)

	@property
	def ema_value(self):
		# EMA filter: when length == 0, treat as disabled (use length = 1 to bypass)
		length = self.hp['ema_length']
		effective_length = 1 if length == 0 else length
		return ta.ema(self.candles, effective_length)

	@property
	def _has_prev_candle(self):
		return self.candles.shape[0] >= 2

	@property
	def _prev_high(self):
		return self.candles[-2, 3] if self._has_prev_candle else self.high

	@property
	def _prev_low(self):
		return self.candles[-2, 4] if self._has_prev_candle else self.low

	

	@property
	def _ema_filter_long(self):
		# disabled if ema_length == 0
		if self.hp['ema_length'] == 0:
			return True
		return self.price > self.ema_value

	@property
	def _ema_filter_short(self):
		# disabled if ema_length == 0
		if self.hp['ema_length'] == 0:
			return True
		return self.price < self.ema_value

	@property
	def _atr_filter(self):
		# candle range within [min_mult*ATR, max_mult*ATR] if thresholds > 0
		candle_range = abs(self.high - self.low)
		min_mult = self.hp['atr_min_mult']
		max_mult = self.hp['atr_max_mult']
		min_ok = candle_range >= min_mult * self.atr if min_mult > 0 else True
		max_ok = candle_range <= max_mult * self.atr if max_mult > 0 else True
		return min_ok and max_ok and self.atr is not None

	@property
	def _fib_levels(self):
		# Compute fib thresholds for body location
		fib_level = self.hp['fib_level']
		# Upper segment threshold for bullish (close/open must be >= this)
		# Equivalent to: high - (high - low) * fib_level
		bull_fib = (self.low - self.high) * fib_level + self.high
		# Lower segment threshold for bearish (close/open must be <= this)
		# Equivalent to: low + (high - low) * fib_level
		bear_fib = (self.high - self.low) * fib_level + self.low
		return bull_fib, bear_fib

	@property
	def _valid_hammer(self):
		# Pinbar long setup similar to zen.isHammer(fibLevel)
		
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
		# Pinbar short setup similar to zen.isStar(fibLevel)
		
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
		# Only when no position and bar is confirmed (Jesse runs on bar close)
		return self.is_close and self._valid_hammer and self.is_open is False

	def should_short(self) -> bool:
		# Spot cannot short
		if self.is_spot_trading:
			return False
		return self.is_close and self._valid_star and self.is_open is False
		
	def go_long(self):
		# Entry at close, stop based on Pine logic:
		# stopSize = atr * stopMultiplier
		# base ref = low if low < low[1] else low[1]; stop = base_ref - stopSize
		stop_size = self.atr * self.hp['stop_atr_mult']
		base_stop_ref = self.low if self.low < self._prev_low else self._prev_low
		stop_price = base_stop_ref - stop_size
		entry = self.price
		if self.hp['use_fixed_fractional'] == 1:
			qty = utils.risk_to_qty(
				self.available_margin,
				self.hp['risk_percent'],
				entry,
				stop_price,
				fee_rate=self.fee_rate
			)
		else:
			# fallback: fixed size = full balance (no risk model)
			qty = utils.size_to_qty(self.balance, entry, fee_rate=self.fee_rate)
		self.buy = qty, entry

	def go_short(self):
		# For futures trading only
		stop_size = self.atr * self.hp['stop_atr_mult']
		base_stop_ref = self.high if self.high > self._prev_high else self._prev_high
		stop_price = base_stop_ref + stop_size
		entry = self.price
		if self.hp['use_fixed_fractional'] == 1:
			qty = utils.risk_to_qty(
				self.available_margin,
				self.hp['risk_percent'],
				entry,
				stop_price,
				fee_rate=self.fee_rate
			)
		else:
			qty = utils.size_to_qty(self.balance, entry, fee_rate=self.fee_rate)
		self.sell = qty, entry

	def on_open_position(self, order) -> None:
		# Set SL/TP using the same definitions as the signal bar
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
			self.add_line_to_candle_chart('PBS EMA', self.ema_value)
		# Draw current SL/TP if in a position
		if self.is_open:
			if self.average_stop_loss:
				self.add_line_to_candle_chart('PBS Stop', self.average_stop_loss)
			if self.average_take_profit:
				self.add_line_to_candle_chart('PBS Target', self.average_take_profit)

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
		# Mirrors Pine inputs as close as possible within Jesse
		return [
			{'name': 'stop_atr_mult', 'type': float, 'min': 0.5, 'max': 5.0, 'default': 1.0},   # stopMultiplier
			{'name': 'rr', 'type': float, 'min': 0.5, 'max': 5.0, 'default': 1.0},              # rr
			{'name': 'fib_level', 'type': float, 'min': 0.2, 'max': 0.8, 'default': 0.333},     # fibLevel
			{'name': 'atr_min_mult', 'type': float, 'min': 0.0, 'max': 3.0, 'default': 0.0},    # atrMinFilterSize
			{'name': 'atr_max_mult', 'type': float, 'min': 0.0, 'max': 5.0, 'default': 3.0},    # atrMaxFilterSize
			{'name': 'ema_length', 'type': int, 'min': 0, 'max': 200, 'default': 0},            # emaFilter (0 disables)
			{'name': 'use_fixed_fractional', 'type': int, 'min': 0, 'max': 1, 'default': 1},    # useFixedFractional (bool via int)
			{'name': 'risk_percent', 'type': float, 'min': 0.25, 'max': 10.0, 'default': 10},  # riskPercent
			
		]
