from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class R4_SOLTrendFollow(Strategy):
    """
    Research Run #4 -- SOL CANDIDATE (night shift 2026-07-26). CONFIG FROZEN.

    Trend-following with ratcheting ATR trailing stop, SOL-USD 4h,
    Kraken Pro Futures, leverage 3. Long: EMA12>EMA44 and price>EMA12;
    short symmetric. Exit: trailing stop only.
    CONFIG: ema_fast=12, ema_slow=44, atr_period=14, atr_mult=3.5,
    trail_mult=5.0, risk_percent=2.5, allow_shorts=1.

    Full window 2022-05-15 -> 2026-07-21 (holdout 2026 INCLUDED at Tom's
    explicit request -- no virgin holdout remains; paper trading is the
    out-of-sample test): Sharpe 1.3221, +42.3%/yr, max DD -18.63%, PF 2.09,
    107 trades. Tom's hard criteria (annual>=20%, DD<=25%): PASSED.

    Neighborhood: EMA 13/48@5.0=1.26; trail 4.5=0.84, 5.5=1.10 (all pass
    criteria). ⚠️ trail<=4.0 collapses to 0.47 -- do NOT reduce trail below
    4.5. Shorts contribute (long-only variant loses ~0.05 Sharpe).
    Keltner family was tried first on SOL and plateaued at 0.54 (rejected).
    Correlations: vs R4_BTC -0.03, vs R2_ETH_1h 0.01, vs R2_ETH_4h -0.01.
    Backtest id: fa9eb6d7-c17f-4d88-a732-a559e0db632a.
    """

    @property
    def ema_f(self):
        return ta.ema(self.candles, self.hp['ema_fast'])

    @property
    def ema_s(self):
        return ta.ema(self.candles, self.hp['ema_slow'])

    @property
    def atr(self):
        return ta.atr(self.candles, self.hp['atr_period'])

    def should_long(self) -> bool:
        return self.ema_f > self.ema_s and self.price > self.ema_f

    def should_short(self) -> bool:
        return self.hp['allow_shorts'] == 1 and self.ema_f < self.ema_s and self.price < self.ema_f

    def should_cancel_entry(self) -> bool:
        return True

    def go_long(self):
        entry = self.price
        stop = entry - self.atr * self.hp['atr_mult']
        qty = utils.risk_to_qty(self.available_margin, self.hp['risk_percent'], entry, stop, fee_rate=self.fee_rate)
        self.buy = qty, entry
        self.stop_loss = qty, stop

    def go_short(self):
        entry = self.price
        stop = entry + self.atr * self.hp['atr_mult']
        qty = utils.risk_to_qty(self.available_margin, self.hp['risk_percent'], entry, stop, fee_rate=self.fee_rate)
        self.sell = qty, entry
        self.stop_loss = qty, stop

    def update_position(self):
        qty = abs(self.position.qty)
        if self.is_long:
            new_stop = self.price - self.atr * self.hp['trail_mult']
            if self.average_stop_loss is None or new_stop > self.average_stop_loss:
                self.stop_loss = qty, new_stop
        elif self.is_short:
            new_stop = self.price + self.atr * self.hp['trail_mult']
            if self.average_stop_loss is None or new_stop < self.average_stop_loss:
                self.stop_loss = qty, new_stop

    def hyperparameters(self) -> list:
        return [
            {'name': 'ema_fast', 'type': int, 'min': 8, 'max': 40, 'default': 12},
            {'name': 'ema_slow', 'type': int, 'min': 30, 'max': 120, 'default': 44},
            {'name': 'atr_period', 'type': int, 'min': 10, 'max': 20, 'default': 14},
            {'name': 'atr_mult', 'type': float, 'min': 1.5, 'max': 5.0, 'step': 0.1, 'default': 3.5},
            {'name': 'trail_mult', 'type': float, 'min': 1.5, 'max': 8.0, 'step': 0.1, 'default': 5.0},
            {'name': 'risk_percent', 'type': float, 'min': 0.8, 'max': 3.5, 'step': 0.1, 'default': 2.5},
            {'name': 'allow_shorts', 'type': int, 'min': 0, 'max': 1, 'default': 1},
        ]
