from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class R4_BTCKeltnerAsym(Strategy):
    """
    Research Run #4 -- BTC CANDIDATE (night shift 2026-07-26). CONFIG FROZEN.

    Asymmetric Keltner breakout, BTC-USD 1h, Kraken Pro Futures, leverage 3.
    CONFIG: period=64, long_mult=4.4, short_mult=6.8, atr_period=15,
    atr_sma_period=18, vol_expansion_mult=1.25, atr_mult=1.25, risk_percent=1.7.

    Full window 2022-05-15 -> 2026-07-21 (holdout 2026 INCLUDED at Tom's
    explicit request -- no virgin holdout remains; paper trading is the
    out-of-sample test): Sharpe 1.5701, +36.7%/yr, max DD -14.48%, PF 2.09,
    130 trades. Tom's hard criteria (annual>=20%, DD<=25%): PASSED.

    Neighborhood: (4.2,6.8)=1.53, (4.2,6.2)=1.48, (4.2,5.6)=1.35 -- smooth
    on the long side and the 6.2-6.8 short zone; (4.2,7.4)=1.40 with DD -24.5
    (shorts nearly off doubles DD -- the rare shorts are crash insurance).
    Correlations: vs R4_SOL -0.03, vs R2_ETH_1h 0.06, vs R2_ETH_4h 0.07.
    Backtest id: a5fb2199-d76c-45c2-b02a-d440c177d752.
    """

    @property
    def kc_long(self):
        return ta.keltner(self.candles, self.hp['period'], self.hp['long_mult'])

    @property
    def kc_short(self):
        return ta.keltner(self.candles, self.hp['period'], self.hp['short_mult'])

    @property
    def atr(self):
        return ta.atr(self.candles, self.hp['atr_period'])

    @property
    def atr_sma(self):
        return ta.sma(ta.atr(self.candles, self.hp['atr_period'], sequential=True), self.hp['atr_sma_period'])

    @property
    def vol_ok(self):
        return self.atr > self.atr_sma * self.hp['vol_expansion_mult']

    def should_long(self) -> bool:
        return self.price > self.kc_long.upperband and self.vol_ok

    def should_short(self) -> bool:
        return self.price < self.kc_short.lowerband and self.vol_ok

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
        if self.is_long and self.price <= self.kc_long.middleband:
            self.liquidate()
        if self.is_short and self.price >= self.kc_short.middleband:
            self.liquidate()

    def hyperparameters(self) -> list:
        return [
            {'name': 'period', 'type': int, 'min': 40, 'max': 120, 'default': 64},
            {'name': 'long_mult', 'type': float, 'min': 3.0, 'max': 6.0, 'step': 0.1, 'default': 4.4},
            {'name': 'short_mult', 'type': float, 'min': 3.0, 'max': 9.0, 'step': 0.1, 'default': 6.8},
            {'name': 'atr_period', 'type': int, 'min': 10, 'max': 20, 'default': 15},
            {'name': 'atr_sma_period', 'type': int, 'min': 14, 'max': 30, 'default': 18},
            {'name': 'vol_expansion_mult', 'type': float, 'min': 1.0, 'max': 1.4, 'step': 0.05, 'default': 1.25},
            {'name': 'atr_mult', 'type': float, 'min': 1.2, 'max': 1.8, 'step': 0.05, 'default': 1.25},
            {'name': 'risk_percent', 'type': float, 'min': 1.0, 'max': 1.8, 'step': 0.1, 'default': 1.7},
        ]
