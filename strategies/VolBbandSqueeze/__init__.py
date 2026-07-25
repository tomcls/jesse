from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class VolBbandSqueeze(Strategy):
    """
    Volatility breakout: wait for Bollinger Band width to contract below
    its own recent rolling minimum (a "squeeze"), then enter in the
    direction of the breakout once price closes outside the bands.
    """

    @property
    def bb(self):
        return ta.bollinger_bands(self.candles, self.hp['bb_period'], self.hp['bb_dev'], self.hp['bb_dev'])

    @property
    def bb_width_series(self):
        return ta.bollinger_bands_width(self.candles, self.hp['bb_period'], self.hp['bb_dev'], sequential=True)

    @property
    def is_squeeze(self):
        w = self.bb_width_series
        lookback = self.hp['squeeze_lookback']
        return w[-1] <= min(w[-lookback:])

    @property
    def atr(self):
        return ta.atr(self.candles, self.hp['atr_period'])

    def should_long(self) -> bool:
        return self.is_squeeze and self.price > self.bb.upperband

    def should_short(self) -> bool:
        return self.is_squeeze and self.price < self.bb.lowerband

    def should_cancel_entry(self) -> bool:
        return True

    def go_long(self):
        entry = self.price
        stop = entry - self.atr * self.hp['atr_mult']
        qty = utils.risk_to_qty(self.available_margin, self.hp['risk_percent'], entry, stop, fee_rate=self.fee_rate)
        self.buy = qty, entry
        self.stop_loss = qty, stop
        self.take_profit = qty, entry + self.atr * self.hp['atr_mult'] * self.hp['reward_risk']

    def go_short(self):
        entry = self.price
        stop = entry + self.atr * self.hp['atr_mult']
        qty = utils.risk_to_qty(self.available_margin, self.hp['risk_percent'], entry, stop, fee_rate=self.fee_rate)
        self.sell = qty, entry
        self.stop_loss = qty, stop
        self.take_profit = qty, entry - self.atr * self.hp['atr_mult'] * self.hp['reward_risk']

    def update_position(self):
        pass

    def hyperparameters(self) -> list:
        return [
            {'name': 'bb_period', 'type': int, 'min': 10, 'max': 30, 'default': 20},
            {'name': 'bb_dev', 'type': float, 'min': 1.5, 'max': 3.0, 'step': 0.1, 'default': 2.0},
            {'name': 'squeeze_lookback', 'type': int, 'min': 20, 'max': 100, 'default': 50},
            {'name': 'atr_period', 'type': int, 'min': 5, 'max': 30, 'default': 14},
            {'name': 'atr_mult', 'type': float, 'min': 1.0, 'max': 4.0, 'step': 0.1, 'default': 2.0},
            {'name': 'reward_risk', 'type': float, 'min': 0.5, 'max': 3.0, 'step': 0.1, 'default': 2.0},
            {'name': 'risk_percent', 'type': float, 'min': 0.5, 'max': 3.0, 'step': 0.1, 'default': 1.5},
        ]
