from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class ichimoku_trend(Strategy):
     def __init__(self):
        super().__init__()
        self.lookback_window = 10
        self.min_confirm = 5
        self.back_candles_ema = 7

    @property
    def ichimoku(self):
        return ta.ichimoku_cloud(self.candles)

    @property
    def ema(self):
        return ta.ema(self.candles, 100)

    @property
    def atr(self):
        return ta.atr(self.candles, 14)

    @property
    def cloud_top(self):
        return max(self.ichimoku.span_a, self.ichimoku.span_b)

    @property
    def cloud_bottom(self):
        return min(self.ichimoku.span_a, self.ichimoku.span_b)

    def ema_trend(self):
        """Check if price is consistently above/below EMA for last N candles"""
        candles = self.candles[-self.back_candles_ema - 1:]
        
        # Check all candles have open & close above EMA
        above_ema = all(
            candle[1] > ema and candle[2] > ema
            for candle, ema in zip(candles, ta.ema(self.candles, 100, sequential=True)[-self.back_candles_ema - 1:])
        )
        
        # Check all candles have open & close below EMA
        below_ema = all(
            candle[1] < ema and candle[2] < ema
            for candle, ema in zip(candles, ta.ema(self.candles, 100, sequential=True)[-self.back_candles_ema - 1:])
        )
        
        if above_ema:
            return 1
        elif below_ema:
            return -1
        return 0

    def cloud_position_check(self, direction):
        """Check if enough recent bars were above/below cloud"""
        candles = self.candles[-self.lookback_window:]
        ichimoku_seq = ta.ichimoku_cloud_seq(self.candles, sequential=True)
        
        count = 0
        for i in range(-self.lookback_window, 0):
            cloud_top = max(ichimoku_seq.span_a[i], ichimoku_seq.span_b[i])
            cloud_bottom = min(ichimoku_seq.span_a[i], ichimoku_seq.span_b[i])
            
            candle = self.candles[i]
            if direction == 'long':
                if candle[1] > cloud_top and candle[2] > cloud_top:
                    count += 1
            else:  # short
                if candle[1] < cloud_bottom and candle[2] < cloud_bottom:
                    count += 1
        
        return count >= self.min_confirm

    def should_long(self) -> bool:
        # Pierce up through cloud
        prev_close = self.candles[-2][2]
        prev_cloud_top = max(
            ta.ichimoku_cloud_seq(self.candles, sequential=True).span_a[-2],
            ta.ichimoku_cloud_seq(self.candles, sequential=True).span_b[-2]
        )
        
        pierce_up = (self.open < self.cloud_top) and (self.close > self.cloud_top)
        
        # Check conditions
        return (
            pierce_up and
            self.cloud_position_check('long') and
            self.ema_trend() == 1
        )

    def should_short(self) -> bool:
        # Pierce down through cloud
        pierce_down = (self.open > self.cloud_bottom) and (self.close < self.cloud_bottom)
        
        # Check conditions
        return (
            pierce_down and
            self.cloud_position_check('short') and
            self.ema_trend() == -1
        )

    def go_long(self):
        entry = self.price
        stop = entry - self.atr * 2.0
        qty = utils.risk_to_qty(self.available_margin, 3, entry, stop, fee_rate=self.fee_rate)
        self.buy = qty, entry

    def go_short(self):
        entry = self.price
        stop = entry + self.atr * 2.0
        qty = utils.risk_to_qty(self.available_margin, 3, entry, stop, fee_rate=self.fee_rate)
        self.sell = qty, entry

    def should_cancel_entry(self) -> bool:
        return True

    def on_open_position(self, order) -> None:
        if self.is_long:
            self.stop_loss = self.position.qty, self.price - self.atr * 2.0
            self.take_profit = self.position.qty, self.price + self.atr * 4.0
        elif self.is_short:
            self.stop_loss = self.position.qty, self.price + self.atr * 2.0
            self.take_profit = self.position.qty, self.price - self.atr * 4.0

    def hyperparameters(self) -> list:
        return [
            {'name': 'atr_mult_sl', 'type': float, 'min': 1.0, 'max': 2.5, 'default': 2.0},
            {'name': 'rr_mult_tp', 'type': float, 'min': 1.0, 'max': 3.0, 'default': 2.0},
            {'name': 'min_confirm', 'type': int, 'min': 3, 'max': 8, 'default': 5},
            {'name': 'back_candles_ema', 'type': int, 'min': 5, 'max': 12, 'default': 7}
        ]