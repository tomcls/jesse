from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class SlowTrendFollowing(Strategy):
    def should_long(self) -> bool:
        conversion_line, base_line, span_a, span_b = self.ichimoku_cloud

        return (self.price > span_a) and (self.price > base_line) and (self.small_trend == 1) and (span_a > span_b)

    def should_short(self) -> bool:
        conversion_line, base_line, span_a, span_b = self.ichimoku_cloud

        return (self.price < span_a) and (self.price < base_line) and (self.small_trend == -1) and (span_a < span_b)

    def go_long(self):
        entry = self.price + self.entry_atr * self.hp['entry_stop_atr_rate']
        stop = self.stop_loss_long(entry)
        take_profit = self.take_profit_long(entry)
        qty = self.position_size(entry, stop)
        self.buy = qty, entry
        self.take_profit = qty, take_profit
        self.stop_loss = qty, stop

    def go_short(self):
        entry = self.price - self.entry_atr * self.hp['entry_stop_atr_rate']
        # sometimes an extreme ATR value can lead to a negative price
        if entry <= 0:
            entry = self.price
        stop = self.stop_loss_short(entry)
        take_profit = self.take_profit_short(entry)
        qty = self.position_size(entry, stop)
        self.sell = qty, entry
        self.take_profit = qty, take_profit
        self.stop_loss = qty, stop

    def update_position(self):
        if self.position.pnl > 0:
            base_line = self.ichimoku_cloud[1]
            # make sure to only update take_profit with a STOP order
            if (self.is_long and self.price > base_line) or (self.is_short and self.price < base_line):
                self.take_profit = self.position.qty, base_line

    def should_cancel_entry(self) -> bool:
        return True

    def take_profit_short(self, entry):
        take_profit = entry - self.take_profit_atr * self.hp['take_profit_atr_rate']
        # sometimes an extreme ATR value can lead to a negative price
        if take_profit <= 0:
            # fallback to donchian channel
            take_profit = self.dc.lowerband
        return take_profit

    def take_profit_long(self, entry):
        take_profit = entry + self.take_profit_atr * self.hp['take_profit_atr_rate']
        return take_profit

    def stop_loss_long(self, entry):
        exit = entry - self.stop_atr * self.hp['stop_loss_atr_rate']
        # sometimes an extreme ATR value can lead to a negative price
        if exit <= 0:
            # fallback to donchian channel
            exit = self.dc.lowerband
        return exit

    def stop_loss_short(self, entry):
        exit = entry + (self.stop_atr * self.hp['stop_loss_atr_rate'])
        return exit

    def position_size(self, entry, stop):
        # depending on the coin you might want to set the precisions. Live does take care of the automatically.
        # instead of self.hp['risk'] you can use the dynamic self.kelly_risk value. Make sure to update the hardcoded rates.
        risk_qty = utils.risk_to_qty(self.balance,  self.hp['risk'], entry, stop, precision=6, fee_rate=self.fee_rate)
        # if you are a conservative trader you might want to uncomment this to never risk more than 30%
        # max_qty = utils.size_to_qty(0.30 * self.balance, entry, precision=6, fee_rate=self.fee_rate)
        # risk_qty = min(risk_qty, max_qty)
        return risk_qty

    @property
    def kelly_risk(self):
        # in the beginning without trades or too few we need to hardcode values. You can get them from backtests.
        if not self.metrics or self.metrics['total'] < 20:
            win_rate = 0.48
            ratio_avg_win_loss = 3.74
        else:
            win_rate = self.metrics['win_rate']
            ratio_avg_win_loss = self.metrics['ratio_avg_win_loss']

        kc = utils.kelly_criterion(win_rate, ratio_avg_win_loss) * 100
        if kc < 0:
            # if the kelly criterion is negative the strategy turned bad
            raise ValueError("Bad Kelly criterion.")
        return kc

    ################################################################
    # # # # # # # # # # # # # indicators # # # # # # # # # # # # # #
    ################################################################

    @property
    def take_profit_atr(self):
        return ta.atr(self.candles, self.hp['take_profit_atr_period'])

    @property
    def stop_atr(self):
        return ta.atr(self.candles, self.hp['stop_atr_period'])

    @property
    def entry_atr(self):
        return ta.atr(self.candles, self.hp['entry_atr_period'])

    @property
    def ichimoku_cloud(self):
        return ta.ichimoku_cloud(self.candles, conversion_line_period=9, base_line_period=26, lagging_line_period=52, displacement=26)

        # The default settings work best. These are famous ones too:
        #return ta.ichimoku_cloud(self.candles, conversion_line_period=10, base_line_period=30, lagging_line_period=60, displacement=30)
        #return ta.ichimoku_cloud(self.candles, conversion_line_period=20, base_line_period=60, lagging_line_period=120, displacement=30)

    @property
    def small_trend(self):
        conversion_line, base_line, span_a, span_b = self.ichimoku_cloud

        if conversion_line > base_line:
            return 1
        elif conversion_line < base_line:
            return -1
        else:
            return 0

    @property
    def dc(self):
        return ta.donchian(self.candles, period=self.hp['stop_dc_period'])

    def watch_list(self):
        conversion_line, base_line, span_a, span_b = self.ichimoku_cloud

        return [
            ('self.price > span_a', self.price > span_a),
            ('self.price < span_a', self.price < span_a),
            ('self.small_trend', self.small_trend),
            ('span_a > span_b', span_a > span_b),
            ('span_a < span_b', span_a < span_b),
        ]



    ###############################################################
    # # # # # # # # # # # # # filters # # # # # # # # # # # # # # #
    ###############################################################

    def filters(self):
        return []

    def hyperparameters(self):
        return [
            {'name': 'entry_stop_atr_rate', 'type': float, 'min': 0.02, 'max': 1.5, 'default': 0.1},
            {'name': 'stop_loss_atr_rate', 'type': float, 'min': 1, 'max': 4, 'default': 1.8},
            {'name': 'take_profit_atr_rate', 'type': int, 'min': 1, 'max': 15, 'default': 10},
            {'name': 'entry_atr_period', 'type': int, 'min': 2, 'max': 50, 'default': 14},
            {'name': 'stop_atr_period', 'type': int, 'min': 2, 'max': 50, 'default': 14},
            {'name': 'take_profit_atr_period', 'type': int, 'min': 2, 'max': 50, 'default': 14},
            {'name': 'stop_dc_period', 'type': int, 'min': 2, 'max': 50, 'default': 14},
            {'name': 'risk', 'type': int, 'min': 1, 'max': 10, 'default': 3},
        ]