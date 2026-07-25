from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils
from typing import Optional


class BreakoutFader(Strategy):
    # =========================
    # Data and helper properties
    # =========================
    @property
    def atr(self) -> float:
        return ta.atr(self.candles)

    @property
    def htf_candles(self):
        # Higher timeframe candles for HTF high/low/EMA/volatility
        return self.get_candles(self.exchange, self.symbol, self.hp['htf_tf'])

    def _ensure_state(self) -> None:
        if self.index == 0:
            self.vars['last_htf_ts'] = None
            self.vars['orders_placed_for_htf_bar'] = False

    def _htf_prev_closed_candle(self):
        c = self.htf_candles
        if c.shape[0] < 2:
            return None
        return c[-2]

    def _htf_last_closed_ts(self) -> Optional[float]:
        prev_candle = self._htf_prev_closed_candle()
        if prev_candle is None:
            return None
        return float(prev_candle[0])

    @property
    def is_new_htf_bar(self) -> bool:
        ts = self._htf_last_closed_ts()
        last = self.vars.get('last_htf_ts')
        return ts is not None and ts != last

    @property
    def htf_prev_high(self) -> Optional[float]:
        pc = self._htf_prev_closed_candle()
        if pc is None:
            return None
        # Jesse candle: [timestamp, open, close, high, low, volume]
        return float(pc[3])

    @property
    def htf_prev_low(self) -> Optional[float]:
        pc = self._htf_prev_closed_candle()
        if pc is None:
            return None
        return float(pc[4])

    @property
    def htf_prev_close(self) -> Optional[float]:
        pc = self._htf_prev_closed_candle()
        if pc is None:
            return None
        return float(pc[2])

    @property
    def htf_ema(self) -> Optional[float]:
        # No need to over-handle lookahead; Jesse manages it. Use default EMA params.
        if self.htf_candles.shape[0] < max(2, int(self.hp['ema_len']) + 1):
            return None
        return float(ta.ema(self.htf_candles, int(self.hp['ema_len'])))

    @property
    def avg_volatility(self) -> float:
        """
        Average HTF volatility over lookback:
        ((high - low) / ((high + low) / 2)) * 100
        Computed on last N closed HTF candles.
        """
        hc = self.htf_candles
        lookback = int(self.hp['vola_lookback'])
        if hc.shape[0] < lookback + 1:
            return 0.0
        closed = hc[:-1][-lookback:]
        highs = closed[:, 3]
        lows = closed[:, 4]
        denom = (highs + lows) / 2.0
        # Guard against division by zero
        denom = utils.np.where(denom == 0, 1e-9, denom)
        vola = ((highs - lows) / denom) * 100.0
        return float(vola.mean())

    # =========================
    # Setup and filters
    # =========================
    def _general_filters_ok(self) -> bool:
        if self.atr is None:
            return False
        if self.avg_volatility <= float(self.hp['vola_threshold']):
            return False
        # Require we have a previous closed HTF candle available
        if self._htf_prev_closed_candle() is None:
            return False
        return True

    def _long_setup_ok(self) -> bool:
        if not self._general_filters_ok():
            return False
        if int(self.hp['use_ema_filter']) == 1:
            hema = self.htf_ema
            hclose = self.htf_prev_close
            if hema is None or hclose is None:
                return False
            if hclose <= hema:
                return False
        return True

    def _short_setup_ok(self) -> bool:
        if not self._general_filters_ok():
            return False
        if self.is_spot_trading:
            return False
        if int(self.hp['use_ema_filter']) == 1:
            hema = self.htf_ema
            hclose = self.htf_prev_close
            if hema is None or hclose is None:
                return False
            if hclose >= hema:
                return False
        return True

    # =========================
    # Planned levels (for entries/targets)
    # =========================
    @property
    def planned_long_entry(self) -> Optional[float]:
        if self.htf_prev_low is None:
            return None
        return float(self.htf_prev_low - self.atr * float(self.hp['stretch']))

    @property
    def planned_short_entry(self) -> Optional[float]:
        if self.htf_prev_high is None:
            return None
        return float(self.htf_prev_high + self.atr * float(self.hp['stretch']))

    def _stop_and_target(self, entry: float, direction: str) -> (float, Optional[float]):
        sl_mult = float(self.hp['sl_mult'])
        rr = float(self.hp['rr'])
        use_trailing = int(self.hp['use_trailing']) == 1
        if direction == 'long':
            stop = entry - self.atr * sl_mult
            if use_trailing:
                return stop, None
            target = entry + (abs(entry - stop) * rr)
            return stop, target
        else:
            stop = entry + self.atr * sl_mult
            if use_trailing:
                return stop, None
            target = entry - (abs(entry - stop) * rr)
            return stop, target

    # =========================
    # Lifecycle
    # =========================
    def before(self) -> None:
        self._ensure_state()
        # Reset ability to place new orders on new HTF bar
        if not self.is_open and self.is_new_htf_bar:
            self.vars['orders_placed_for_htf_bar'] = False

    def should_long(self) -> bool:
        if self.is_open:
            return False
        # Only place fresh orders on start of a new HTF bar and avoid duplicates
        if not self.is_new_htf_bar or self.vars.get('orders_placed_for_htf_bar'):
            return False
        return self._long_setup_ok()
    
    def should_short(self) -> bool:
        if self.is_open:
            return False
        if not self.is_new_htf_bar or self.vars.get('orders_placed_for_htf_bar'):
            return False
        return self._short_setup_ok()
        
    def go_long(self):
        entry = self.planned_long_entry
        if entry is None:
            return
        stop, _ = self._stop_and_target(entry, 'long')
        qty = utils.risk_to_qty(
            capital=self.available_margin,
            risk_per_capital=float(self.hp['risk_per_trade']),
            entry_price=entry,
            stop_loss_price=stop,
            fee_rate=self.fee_rate
        )
        if qty <= 0:
            return
        self.buy = qty, entry
        self.vars['orders_placed_for_htf_bar'] = True
        self.vars['last_htf_ts'] = self._htf_last_closed_ts()

    def go_short(self):
        entry = self.planned_short_entry
        if entry is None:
            return
        stop, _ = self._stop_and_target(entry, 'short')
        qty = utils.risk_to_qty(
            capital=self.available_margin,
            risk_per_capital=float(self.hp['risk_per_trade']),
            entry_price=entry,
            stop_loss_price=stop,
            fee_rate=self.fee_rate
        )
        if qty <= 0:
            return
        self.sell = qty, entry
        self.vars['orders_placed_for_htf_bar'] = True
        self.vars['last_htf_ts'] = self._htf_last_closed_ts()

    def should_cancel_entry(self) -> bool:
        # Cancel stale pending entries when a new HTF bar starts (fresh levels)
        return not self.is_open and self.is_new_htf_bar

    def on_open_position(self, order) -> None:
        # Set SL/TP or SL-only depending on trailing config
        if self.is_long:
            entry = self.position.entry_price
            stop, target = self._stop_and_target(entry, 'long')
            self.stop_loss = self.position.qty, stop
            if target is not None:
                self.take_profit = self.position.qty, target
            # Optionally cancel opposite side if both sides were ever allowed (best-effort)
            if int(self.hp['cancel_after_fill']) == 1:
                # Jesse cannot cancel while position is open; we avoid placing both sides by default via EMA filter
                pass
        elif self.is_short:
            entry = self.position.entry_price
            stop, target = self._stop_and_target(entry, 'short')
            self.stop_loss = self.position.qty, stop
            if target is not None:
                self.take_profit = self.position.qty, target

    def update_position(self) -> None:
        # ATR trailing stop (if enabled)
        if int(self.hp['use_trailing']) != 1:
            return
        sl_mult = float(self.hp['sl_mult'])
        if self.is_long:
            new_stop = self.low - self.atr * sl_mult
            # Only tighten upwards
            self.stop_loss = self.position.qty, max(self.average_stop_loss, new_stop)
        elif self.is_short:
            new_stop = self.high + self.atr * sl_mult
            # Only tighten downwards
            self.stop_loss = self.position.qty, min(self.average_stop_loss, new_stop)

    # =========================
    # Visualization
    # =========================
    def after(self) -> None:
        # HTF EMA and HTF levels
        hema = self.htf_ema
        if hema is not None:
            self.add_line_to_candle_chart('HTF EMA', hema)
        if self.htf_prev_high is not None:
            self.add_horizontal_line_to_candle_chart('HTF High', self.htf_prev_high, 'yellow')
        if self.htf_prev_low is not None:
            self.add_horizontal_line_to_candle_chart('HTF Low', self.htf_prev_low, 'blue')

        # Planned entries (for the current HTF bar)
        if not self.is_open and not self.vars.get('orders_placed_for_htf_bar', False):
            if self._long_setup_ok() and self.planned_long_entry is not None:
                self.add_horizontal_line_to_candle_chart('Planned Long Entry', self.planned_long_entry, 'gray')
            if self._short_setup_ok() and self.planned_short_entry is not None:
                self.add_horizontal_line_to_candle_chart('Planned Short Entry', self.planned_short_entry, 'gray')

        # Active position SL/TP
        if self.is_long:
            self.add_horizontal_line_to_candle_chart('Long Stop', self.average_stop_loss, 'red')
            if self.average_take_profit:
                self.add_horizontal_line_to_candle_chart('Long Target', self.average_take_profit, 'green')
        elif self.is_short:
            self.add_horizontal_line_to_candle_chart('Short Stop', self.average_stop_loss, 'red')
            if self.average_take_profit:
                self.add_horizontal_line_to_candle_chart('Short Target', self.average_take_profit, 'green')

        # Volatility panel
        self.add_extra_line_chart('Vola', 'Avg HTF Vola %', self.avg_volatility)
        self.add_horizontal_line_to_extra_chart('Vola', 'Vola Threshold', float(self.hp['vola_threshold']))

    # =========================
    # Monitoring (live/paper)
    # =========================
    def watch_list(self) -> list:
        return [
            ('htf_tf', self.hp['htf_tf']),
            ('avg_vola_%', round(self.avg_volatility, 2)),
            ('ema_filter', int(self.hp['use_ema_filter'])),
            ('use_trailing', int(self.hp['use_trailing'])),
            ('risk_%', float(self.hp['risk_per_trade'])),
        ]

    # =========================
    # Hyperparameters
    # =========================
    def hyperparameters(self) -> list:
        return [
            {'name': 'htf_tf', 'type': 'categorical', 'options': ['1D', '4h', '1h'], 'default': '1D'},
            {'name': 'stretch', 'type': float, 'min': 0.1, 'max': 5.0, 'step': 0.1, 'default': 1.0},
            {'name': 'rr', 'type': float, 'min': 0.2, 'max': 5.0, 'step': 0.1, 'default': 1.0},
            {'name': 'sl_mult', 'type': float, 'min': 0.5, 'max': 5.0, 'step': 0.1, 'default': 2.0},
            {'name': 'cancel_after_fill', 'type': int, 'min': 0, 'max': 1, 'default': 1},
            {'name': 'use_trailing', 'type': int, 'min': 0, 'max': 1, 'default': 1},
            {'name': 'use_ema_filter', 'type': int, 'min': 0, 'max': 1, 'default': 1},
            {'name': 'ema_len', 'type': int, 'min': 5, 'max': 200, 'default': 20},
            {'name': 'vola_lookback', 'type': int, 'min': 5, 'max': 300, 'default': 52},
            {'name': 'vola_threshold', 'type': float, 'min': 0.0, 'max': 5.0, 'step': 0.1, 'default': 0.0},
            {'name': 'risk_per_trade', 'type': float, 'min': 0.1, 'max': 10.0, 'step': 0.1, 'default': 3.0},
        ]
