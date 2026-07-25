from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class SuperTrend(Strategy):
    """
    SuperTrend strategy based on the PineScript by KivancOzbilgic.

    Logic:
    - Compute SuperTrend with ATR period and multiplier
    - Detect flips: go long when trend flips from down (-1) to up (1),
      go short when trend flips from up (1) to down (-1)
    - Set stop-loss at the SuperTrend line and trail it as it moves
    - Exit on opposite flip as safety
    """

    def before(self) -> None:
        # Compute current direction using SuperTrend line: above => uptrend(1), below => downtrend(-1)
        st = ta.supertrend(self.candles, period=self.hp['atr_period'], factor=self.hp['multiplier'])
        curr_dir = 1 if self.price > st.trend else -1

        if self.index == 0:
            self.vars['prev_dir'] = curr_dir
        self.vars['curr_dir'] = curr_dir

    def should_long(self) -> bool:
        # Flip from -1 to 1
        return self.vars.get('curr_dir', 0) == 1 and self.vars.get('prev_dir', 0) == -1

    def should_short(self) -> bool:
        # Flip from 1 to -1 (futures only). In spot, Jesse will ignore shorts.
        return self.vars.get('curr_dir', 0) == -1 and self.vars.get('prev_dir', 0) == 1
        
    def go_long(self):
        st = ta.supertrend(self.candles, period=self.hp['atr_period'], factor=self.hp['multiplier'])
        entry = self.price
        stop = st.trend  # place stop at SuperTrend line
        qty = utils.risk_to_qty(
            self.available_margin,
            self.hp['risk_percent'],
            entry,
            stop,
            fee_rate=self.fee_rate
        )
        self.buy = qty, entry

    def go_short(self):
        st = ta.supertrend(self.candles, period=self.hp['atr_period'], factor=self.hp['multiplier'])
        entry = self.price
        stop = st.trend  # place stop at SuperTrend line
        qty = utils.risk_to_qty(
            self.available_margin,
            self.hp['risk_percent'],
            entry,
            stop,
            fee_rate=self.fee_rate
        )
        self.sell = qty, entry

    def on_open_position(self, order) -> None:
        # Initialize stop at the SuperTrend line
        st = ta.supertrend(self.candles, period=self.hp['atr_period'], factor=self.hp['multiplier'])
        if self.is_long:
            self.stop_loss = self.position.qty, st.trend
        elif self.is_short:
            self.stop_loss = self.position.qty, st.trend

    def update_position(self) -> None:
        # Trail stop along the SuperTrend line and exit on opposite flip
        st = ta.supertrend(self.candles, period=self.hp['atr_period'], factor=self.hp['multiplier'])
        curr_dir = self.vars.get('curr_dir', 0)

        if self.is_long:
            # trail up only
            self.stop_loss = self.position.qty, max(self.average_stop_loss, st.trend)
            if curr_dir == -1:
                self.liquidate()
        elif self.is_short:
            # trail down only
            self.stop_loss = self.position.qty, min(self.average_stop_loss, st.trend)
            if curr_dir == 1:
                self.liquidate()

    def should_cancel_entry(self) -> bool:
        return True

    def after(self) -> None:
        # shift dir for next candle and draw the line on chart
        self.vars['prev_dir'] = self.vars.get('curr_dir', 0)
        st = ta.supertrend(self.candles, period=self.hp['atr_period'], factor=self.hp['multiplier'])
        self.add_line_to_candle_chart('SuperTrend', st.trend)

    def watch_list(self) -> list:
        st = ta.supertrend(self.candles, period=self.hp['atr_period'], factor=self.hp['multiplier'])
        return [
            ('Direction', 1 if self.price > st.trend else -1),
            ('ST line', st.trend),
        ]

    def hyperparameters(self) -> list:
        return [
            {'name': 'atr_period', 'type': int, 'min': 5, 'max': 50, 'default': 10},
            {'name': 'multiplier', 'type': float, 'min': 1.0, 'max': 6.0, 'step': 0.1, 'default': 3.0},
            {'name': 'risk_percent', 'type': float, 'min': 0.5, 'max': 5.0, 'step': 0.1, 'default': 1.5},
        ]
