from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class RangeAdxRsiBb(Strategy):
    """
    Simplified range mean-reversion for Jesse:
    - Enter when price touches Bollinger band with RSI confirmation and low ADX
    - SL = ATR * multiplier
    - TP1 = BB middle (partial), TP2 = opposite band (optional)
    """

    # defaults (also exposed via hyperparameters)
    adx_max = 25
    bb_length = 20
    bb_std = 2.0
    rsi_length = 14
    rsi_long_max = 45
    rsi_short_min = 55
    atr_length = 14
    atr_mult = 1.6
    risk_pct = 0.5  # percent of available_margin
    use_tp2_default = 1  # 1=true, 0=false
    reduce_pos_at_tp1 = 0.5
    bb_touch_buffer = 0.001

    # ------------- indicators as properties -------------
    @property
    def bb(self):
        # returns namedtuple(upperband, middleband, lowerband)
        return ta.bollinger_bands(self.candles, self.hp.get('bb_length', self.bb_length), self.hp.get('bb_std', self.bb_std))

    @property
    def rsi(self):
        return ta.rsi(self.candles, self.hp.get('rsi_length', self.rsi_length))

    @property
    def adx(self):
        return ta.adx(self.candles)

    @property
    def atr(self):
        return ta.atr(self.candles, self.hp.get('atr_length', self.atr_length))

    # ------------- entry logic -------------
    def should_long(self) -> bool:
        if self.is_open:
            return False
        adx_ok = self.adx < self.hp.get('adx_max', self.adx_max)
        touch_lower = self.price <= self.bb.lowerband * (1 + self.hp.get('bb_touch_buffer', self.bb_touch_buffer))
        rsi_ok = self.rsi < self.hp.get('rsi_long_max', self.rsi_long_max)
        return adx_ok and touch_lower and rsi_ok

    def should_short(self) -> bool:
        if self.is_open:
            return False
        adx_ok = self.adx < self.hp.get('adx_max', self.adx_max)
        touch_upper = self.price >= self.bb.upperband * (1 - self.hp.get('bb_touch_buffer', self.bb_touch_buffer))
        rsi_ok = self.rsi > self.hp.get('rsi_short_min', self.rsi_short_min)
        return adx_ok and touch_upper and rsi_ok

    def should_cancel_entry(self) -> bool:
        return self.adx >= self.hp.get('adx_max', self.adx_max)

    # ------------- execution -------------
    def go_long(self):
        entry = self.price
        stop = entry - self.atr * self.hp.get('atr_mult', self.atr_mult)
        qty = utils.risk_to_qty(
            self.available_margin,
            self.hp.get('risk_pct', self.risk_pct),
            entry,
            stop,
            fee_rate=self.fee_rate,
        )
        if qty <= 0:
            return
        self.buy = qty, entry

    def go_short(self):
        entry = self.price
        stop = entry + self.atr * self.hp.get('atr_mult', self.atr_mult)
        qty = utils.risk_to_qty(
            self.available_margin,
            self.hp.get('risk_pct', self.risk_pct),
            entry,
            stop,
            fee_rate=self.fee_rate,
        )
        if qty <= 0:
            return
        self.sell = qty, entry

    def on_open_position(self, order) -> None:
        # set SL/TPs after entry opens
        use_tp2 = self.hp.get('use_tp2', self.use_tp2_default) == 1
        tp1_ratio = self.hp.get('reduce_pos_at_tp1', self.reduce_pos_at_tp1)
        atr_mult = self.hp.get('atr_mult', self.atr_mult)

        if self.is_long:
            sl = self.position.entry_price - self.atr * atr_mult
            tp1 = self.bb.middleband
            tp2 = self.bb.upperband if use_tp2 else None
            self.stop_loss = self.position.qty, sl
            tp1_qty = self.position.qty * tp1_ratio
            self.take_profit = tp1_qty, tp1
            if tp2 is not None:
                self.take_profit = self.position.qty - tp1_qty, tp2
        elif self.is_short:
            sl = self.position.entry_price + self.atr * atr_mult
            tp1 = self.bb.middleband
            tp2 = self.bb.lowerband if use_tp2 else None
            self.stop_loss = self.position.qty, sl
            tp1_qty = self.position.qty * tp1_ratio
            self.take_profit = tp1_qty, tp1
            if tp2 is not None:
                self.take_profit = self.position.qty - tp1_qty, tp2

    def update_position(self) -> None:
        # optional safety: exit if market starts trending strongly
        if self.is_open and self.adx >= self.hp.get('adx_max', self.adx_max):
            self.liquidate()

    # ------------- optimization params -------------
    def hyperparameters(self) -> list:
        return [
            {'name': 'adx_max', 'type': int, 'min': 15, 'max': 40, 'default': self.adx_max},
            {'name': 'bb_length', 'type': int, 'min': 10, 'max': 40, 'default': self.bb_length},
            {'name': 'bb_std', 'type': float, 'min': 1.5, 'max': 2.5, 'default': self.bb_std},
            {'name': 'rsi_length', 'type': int, 'min': 7, 'max': 28, 'default': self.rsi_length},
            {'name': 'rsi_long_max', 'type': int, 'min': 30, 'max': 55, 'default': self.rsi_long_max},
            {'name': 'rsi_short_min', 'type': int, 'min': 50, 'max': 70, 'default': self.rsi_short_min},
            {'name': 'atr_length', 'type': int, 'min': 7, 'max': 28, 'default': self.atr_length},
            {'name': 'atr_mult', 'type': float, 'min': 1.2, 'max': 2.5, 'default': self.atr_mult},
            {'name': 'risk_pct', 'type': float, 'min': 0.1, 'max': 2.0, 'default': self.risk_pct},
            {'name': 'use_tp2', 'type': int, 'min': 0, 'max': 1, 'default': self.use_tp2_default},
            {'name': 'reduce_pos_at_tp1', 'type': float, 'min': 0.25, 'max': 0.9, 'default': self.reduce_pos_at_tp1},
            {'name': 'bb_touch_buffer', 'type': float, 'min': 0.0, 'max': 0.004, 'default': self.bb_touch_buffer},
        ]
