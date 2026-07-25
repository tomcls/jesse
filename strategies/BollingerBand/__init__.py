from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class BollingerBand(Strategy):
    # Optional overrides: set to use a different market for regime filter
    # If None, current route's exchange/symbol are used
    regime_exchange = None
    regime_symbol = None
    regime_timeframe_default = '1D'

    @property
    def upper_sd(self) -> float:
        return self.hp['upper_sd']

    @property
    def lower_sd(self) -> float:
        return self.hp['lower_sd']

    @property
    def ma_period(self) -> int:
        return self.hp['ma_period']

    @property
    def bb_upper(self) -> float:
        bb = ta.bollinger_bands(self.candles, self.ma_period, self.upper_sd)
        return bb.upperband

    @property
    def bb_mid_and_low(self):
        # Compute mid and lower using the lower std multiplier
        bb = ta.bollinger_bands(self.candles, self.ma_period, self.lower_sd)
        return bb.middleband, bb.lowerband

    @property
    def bb_mid(self) -> float:
        mid, _ = self.bb_mid_and_low
        return mid

    @property
    def bb_low(self) -> float:
        _, low = self.bb_mid_and_low
        return low

    # Regime filter (higher timeframe EMA of a market)
    @property
    def regime_candles(self):
        ex = self.regime_exchange or self.exchange
        sym = self.regime_symbol or self.symbol
        tf = self.hp['regime_timeframe']
        return self.get_candles(ex, sym, tf)

    @property
    def regime_ema(self) -> float:
        return ta.ema(self.regime_candles, self.hp['regime_ema_len'])

    @property
    def regime_close(self) -> float:
        # candles: [timestamp, open, close, high, low, volume]
        return float(self.regime_candles[-1, 2])

    @property
    def regime_pass(self) -> bool:
        if not bool(self.hp['use_regime']):
            return True
        return self.regime_close > self.regime_ema

    def should_long(self) -> bool:
        # Entry when close breaks above upper band and regime filter passes
        return self.close > self.bb_upper and self.regime_pass

    def should_short(self) -> bool:
        return False
        
    def go_long(self):
        entry = self.price
        position_size_usd = self.balance * (self.hp['position_percent'] / 100.0)
        qty = utils.size_to_qty( self.balance, entry, fee_rate=self.fee_rate)
        self.buy = qty, entry

    def go_short(self):
        pass

    def update_position(self) -> None:
        # Exit when close crosses below the lower band
        if self.is_long and self.close < self.bb_low:
            self.liquidate()

    def should_cancel_entry(self) -> bool:
        # Cancel unfilled entries if regime fails or price no longer above upper band
        if bool(self.hp['use_regime']) and not self.regime_pass:
            return True
        return not (self.close > self.bb_upper)

    def after(self) -> None:
        # Draw Bollinger Bands
        self.add_line_to_candle_chart('BB Mid', self.bb_mid, 'blue')
        self.add_line_to_candle_chart('BB Upper', self.bb_upper, 'green')
        self.add_line_to_candle_chart('BB Lower', self.bb_low, 'red')

    def hyperparameters(self) -> list:
        return [
            {'name': 'upper_sd', 'type': float, 'min': 1.0, 'max': 5.0, 'step': 0.1, 'default': 1.5},
            {'name': 'lower_sd', 'type': float, 'min': 0.5, 'max': 3.0, 'step': 0.1, 'default': 2.0},
            {'name': 'ma_period', 'type': int, 'min': 10, 'max': 300, 'default': 100},
            {'name': 'position_percent', 'type': float, 'min': 1.0, 'max': 100.0, 'step': 1.0, 'default': 100.0},
            {'name': 'use_regime', 'type': int, 'min': 0, 'max': 1, 'default': 1},
            {'name': 'regime_ema_len', 'type': int, 'min': 5, 'max': 200, 'default': 20},
            {'name': 'regime_timeframe', 'type': 'categorical', 'options': ['1D', '4h', '1h'], 'default': self.regime_timeframe_default},
        ]
