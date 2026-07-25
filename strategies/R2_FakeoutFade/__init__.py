from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class R2_FakeoutFade(Strategy):
    """
    Research Run #2. Failed-breakout reversal. ETH 1h optimum: dc30/
    gate1.0/atr2.5 -> 103 trades, Sharpe 0.2522, DD -5.6%, winrate 66%.
    Now cross-checking the SAME params on BTC and SOL before concluding
    on the family (ETH-only testing was a gap).
    """

    @property
    def atr(self):
        return ta.atr(self.candles, self.hp['atr_period'])

    @property
    def atr_sma(self):
        return ta.sma(ta.atr(self.candles, self.hp['atr_period'], sequential=True), self.hp['atr_sma_period'])

    @property
    def low_vol(self):
        return self.atr <= self.atr_sma * self.hp['vol_gate']

    @property
    def ref_dc(self):
        return ta.donchian(self.candles[:-2], self.hp['dc_period'])

    @property
    def cur_dc(self):
        return ta.donchian(self.candles, self.hp['dc_period'])

    @property
    def fakeout_up(self):
        prev_close = self.candles[-2, 2]
        broke = prev_close > self.ref_dc.upperband
        failed = self.price < self.ref_dc.upperband
        return broke and failed and self.low_vol

    @property
    def fakeout_down(self):
        prev_close = self.candles[-2, 2]
        broke = prev_close < self.ref_dc.lowerband
        failed = self.price > self.ref_dc.lowerband
        return broke and failed and self.low_vol

    def should_long(self) -> bool:
        return self.fakeout_down

    def should_short(self) -> bool:
        return self.fakeout_up

    def should_cancel_entry(self) -> bool:
        return True

    def go_long(self):
        entry = self.price * (1 - self.hp['limit_offset_pct'] / 100)
        stop = entry - self.atr * self.hp['atr_mult']
        qty = utils.risk_to_qty(self.available_margin, self.hp['risk_percent'], entry, stop, fee_rate=self.fee_rate)
        self.buy = qty, entry
        self.stop_loss = qty, stop
        self.take_profit = qty, self.cur_dc.middleband

    def go_short(self):
        entry = self.price * (1 + self.hp['limit_offset_pct'] / 100)
        stop = entry + self.atr * self.hp['atr_mult']
        qty = utils.risk_to_qty(self.available_margin, self.hp['risk_percent'], entry, stop, fee_rate=self.fee_rate)
        self.sell = qty, entry
        self.stop_loss = qty, stop
        self.take_profit = qty, self.cur_dc.middleband

    def update_position(self):
        if self.is_long:
            self.take_profit = self.position.qty, self.cur_dc.middleband
        elif self.is_short:
            self.take_profit = self.position.qty, self.cur_dc.middleband

    def hyperparameters(self) -> list:
        return [
            {'name': 'dc_period', 'type': int, 'min': 10, 'max': 80, 'default': 30},
            {'name': 'vol_gate', 'type': float, 'min': 0.6, 'max': 1.3, 'step': 0.05, 'default': 1.0},
            {'name': 'atr_sma_period', 'type': int, 'min': 10, 'max': 50, 'default': 20},
            {'name': 'limit_offset_pct', 'type': float, 'min': 0.02, 'max': 1.0, 'step': 0.02, 'default': 0.1},
            {'name': 'atr_period', 'type': int, 'min': 5, 'max': 30, 'default': 14},
            {'name': 'atr_mult', 'type': float, 'min': 1.5, 'max': 5.0, 'step': 0.1, 'default': 2.5},
            {'name': 'risk_percent', 'type': float, 'min': 0.5, 'max': 3.0, 'step': 0.1, 'default': 1.5},
        ]
