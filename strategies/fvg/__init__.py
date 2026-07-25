# please implement a fvg strategy with the following rules:
# on higher timeframe, if the price is above the fvg, we want to look for long positions.
# if the price is below the fvg, we want to look for short positions.
# Step1:
# first candles rules Strategy:
# Mark the highest high and the lowest low of the 15 minutes candles
# just one trade per day 
# on a lower timeframe 5min, wait for a displacement break
# Step 2:
# confirm direction
# we need to confirm the direction with a fair value gap (fvg) on 5 minutes timeframe
# Step 3:
# we put the stop loss on candle one just before the the fvg on the lowest low for long and the highest high for short
# Step 4:
# we set a limit order at the top of the fvg for long and reverse for short
# Step 5:
# the risk reward is 1:2


from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils
import numpy as np
from datetime import datetime


class fvg(Strategy):
    def before(self) -> None:
        if self.index == 0:
            self.vars['traded_date'] = None  # ISO date string of last opened position
            self.vars['entry_submitted_date'] = None  # ISO date when entry was submitted

    # ------------- Multi-timeframe data -------------
    @property
    def candles_15m(self):
        return self.get_candles(self.exchange, self.symbol, '15m')

    def _today_iso(self) -> str:
        ts_ms = int(self.current_candle[0])
        return datetime.utcfromtimestamp(ts_ms / 1000).date().isoformat()

    def _one_trade_per_day_allowed(self) -> bool:
        today = self._today_iso()
        traded_date = self.vars.get('traded_date')
        return traded_date != today

    # ------------- FVG detection on 15m (Higher timeframe bias) -------------
    def _latest_bullish_fvg_15m(self):
        c = self.candles_15m
        if c is None or len(c) < 3:
            return None
        # iterate from the most recent closed bar backwards
        for i in range(len(c) - 1, 1, -1):
            j = i - 2
            mid = i - 1
            high_j = c[j, 3]
            low_i = c[i, 4]
            # Bullish FVG when high[j] < low[i]
            if high_j < low_i:
                lower = high_j
                upper = low_i
                stop_ref = c[j, 4]  # low of candle one before the FVG
                return {
                    'type': 'bullish',
                    'i': i,
                    'lower': float(lower),
                    'upper': float(upper),
                    'stop_ref': float(stop_ref),
                }
        return None

    def _latest_bearish_fvg_15m(self):
        c = self.candles_15m
        if c is None or len(c) < 3:
            return None
        for i in range(len(c) - 1, 1, -1):
            j = i - 2
            mid = i - 1
            low_j = c[j, 4]
            high_i = c[i, 3]
            # Bearish FVG when low[j] > high[i]
            if low_j > high_i:
                lower = high_i
                upper = low_j
                stop_ref = c[j, 3]  # high of candle one before the FVG
                return {
                    'type': 'bearish',
                    'i': i,
                    'lower': float(lower),
                    'upper': float(upper),
                    'stop_ref': float(stop_ref),
                }
        return None

    # ------------- FVG detection on 5m (Confirmation and entry) -------------
    def _latest_bullish_fvg_5m(self):
        c = self.candles
        if c is None or len(c) < 3:
            return None
        for i in range(len(c) - 1, 1, -1):
            j = i - 2
            mid = i - 1
            high_j = c[j, 3]
            low_i = c[i, 4]
            if high_j < low_i:
                lower = high_j
                upper = low_i
                stop_ref = c[j, 4]
                return {
                    'type': 'bullish',
                    'i': i,
                    'lower': float(lower),
                    'upper': float(upper),
                    'stop_ref': float(stop_ref),
                }
        return None

    def _latest_bearish_fvg_5m(self):
        c = self.candles
        if c is None or len(c) < 3:
            return None
        for i in range(len(c) - 1, 1, -1):
            j = i - 2
            mid = i - 1
            low_j = c[j, 4]
            high_i = c[i, 3]
            if low_j > high_i:
                lower = high_i
                upper = low_j
                stop_ref = c[j, 3]
                return {
                    'type': 'bearish',
                    'i': i,
                    'lower': float(lower),
                    'upper': float(upper),
                    'stop_ref': float(stop_ref),
                }
        return None

    # ------------- Displacement confirmation on 5m -------------
    def _bullish_displacement(self) -> bool:
        c = self.candles
        if c is None or len(c) < 7:
            return False
        prior_high = np.max(c[-6:-1, 3])
        last_close = c[-1, 2]
        return last_close > prior_high

    def _bearish_displacement(self) -> bool:
        c = self.candles
        if c is None or len(c) < 7:
            return False
        prior_low = np.min(c[-6:-1, 4])
        last_close = c[-1, 2]
        return last_close < prior_low

    # ------------- Bias from 5m FVG -------------
    @property
    def bias_long(self) -> bool:
        b = self._latest_bullish_fvg_5m()
        return b is not None and self.price > b['upper']

    @property
    def bias_short(self) -> bool:
        b = self._latest_bearish_fvg_5m()
        return b is not None and self.price < b['lower']

    # ------------- Entry checks -------------
    def _entry_window_ok(self) -> bool:
        return self._one_trade_per_day_allowed()

    def _no_pending_orders(self) -> bool:
        return len(self.orders) == 0

    def should_long(self) -> bool:
        if not self._entry_window_ok() or not self._no_pending_orders() or not self.is_close:
            return False
        if not self.bias_long:
            return False
        if not self._bullish_displacement():
            return False
        # Require a valid 5m bullish FVG present
        return self._latest_bullish_fvg_5m() is not None

    def should_short(self) -> bool:
        if self.is_spot_trading:
            return False
        if not self._entry_window_ok() or not self._no_pending_orders() or not self.is_close:
            return False
        if not self.bias_short:
            return False
        if not self._bearish_displacement():
            return False
        return self._latest_bearish_fvg_5m() is not None

    # ------------- Orders -------------
    def go_long(self):
        fvg = self._latest_bullish_fvg_5m()
        if not fvg:
            return
        entry = fvg['upper']  # limit at top of bullish FVG
        stop = fvg['stop_ref']  # low of candle before FVG
        if stop >= entry:  # invalid risk
            return
        qty = utils.risk_to_qty(
            self.available_margin,
            self.hp.get('risk_pct', 1.5),
            entry,
            stop,
            fee_rate=self.fee_rate,
        )
        if qty <= 0:
            return
        self.buy = qty, entry
        self.vars['entry_submitted_date'] = self._today_iso()

    def go_short(self):
        if self.is_spot_trading:
            return
        fvg = self._latest_bearish_fvg_5m()
        if not fvg:
            return
        entry = fvg['lower']  # reverse for short: limit at bottom of bearish FVG
        stop = fvg['stop_ref']  # high of candle before FVG
        if stop <= entry:  # invalid risk
            return
        qty = utils.risk_to_qty(
            self.available_margin,
            self.hp.get('risk_pct', 1.5),
            entry,
            stop,
            fee_rate=self.fee_rate,
        )
        if qty <= 0:
            return
        self.sell = qty, entry
        self.vars['entry_submitted_date'] = self._today_iso()

    def on_open_position(self, order) -> None:
        # Set SL and TP with RR = 1:2
        if self.is_long:
            fvg = self._latest_bullish_fvg_5m()
            if not fvg:
                return
            entry = self.position.entry_price
            stop = fvg['stop_ref']
            risk = entry - stop
            if risk <= 0:
                return
            tp = entry + 2 * risk
            self.stop_loss = self.position.qty, stop
            self.take_profit = self.position.qty, tp
        elif self.is_short:
            fvg = self._latest_bearish_fvg_5m()
            if not fvg:
                return
            entry = self.position.entry_price
            stop = fvg['stop_ref']
            risk = stop - entry
            if risk <= 0:
                return
            tp = entry - 2 * risk
            self.stop_loss = self.position.qty, stop
            self.take_profit = self.position.qty, tp

        # mark traded today when position opens
        self.vars['traded_date'] = self._today_iso()

    def should_cancel_entry(self) -> bool:
        # Cancel if bias invalidates or time/day window closed (next day)
        if self.is_close:
            return False
        if self.is_long:
            return False
        if self.is_short:
            return False
        # No open position: check pending entries invalidation
        if len(self.orders) == 0:
            return False
        # Invalidate if opposite bias now
        # If bullish order exists but bias lost, cancel
        has_buy = any(o.side == 'buy' for o in self.orders)
        has_sell = any(o.side == 'sell' for o in self.orders)
        if has_buy and not self.bias_long:
            return True
        if has_sell and not self.bias_short:
            return True
        return False

    # ------------- Visualization and monitoring -------------
    def after(self) -> None:
        b5 = self._latest_bullish_fvg_5m()
        s5 = self._latest_bearish_fvg_5m()
        if b5:
            self.add_horizontal_line_to_candle_chart('5m_bull_fvg_low', b5['lower'], 'green')
            self.add_horizontal_line_to_candle_chart('5m_bull_fvg_top', b5['upper'], 'green')
        if s5:
            self.add_horizontal_line_to_candle_chart('5m_bear_fvg_bottom', s5['lower'], 'red')
            self.add_horizontal_line_to_candle_chart('5m_bear_fvg_top', s5['upper'], 'red')

        # Mark the highest high and lowest low of today's 15m candles (Step 1)
        hhll = self._hh_ll_15m_today()
        if hhll is not None:
            hh, ll = hhll
            self.add_horizontal_line_to_candle_chart('15m_today_HH', hh, 'orange')
            self.add_horizontal_line_to_candle_chart('15m_today_LL', ll, 'orange')

    def watch_list(self) -> list:
        return [
            ('bias_long', 1 if self.bias_long else 0),
            ('bias_short', 1 if self.bias_short else 0),
            ('traded_today', 0 if self._one_trade_per_day_allowed() else 1),
        ]

    # Highest high and lowest low of today's 15m candles
    def _hh_ll_15m_today(self):
        c = self.candles_15m
        if c is None or len(c) == 0:
            return None
        ts_today = datetime.utcfromtimestamp(int(self.current_candle[0]) / 1000).date()
        mask = [datetime.utcfromtimestamp(int(ts) / 1000).date() == ts_today for ts in c[:, 0]]
        if not any(mask):
            return None
        filtered = c[np.array(mask)]
        hh = float(np.max(filtered[:, 3]))
        ll = float(np.min(filtered[:, 4]))
        return hh, ll

    # ------------- Hyperparameters for optimization -------------
    def hyperparameters(self) -> list:
        return [
            {'name': 'risk_pct', 'type': float, 'min': 0.5, 'max': 5.0, 'step': 0.5, 'default': 1.5},
        ]
