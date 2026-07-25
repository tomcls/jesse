# strategies/dual_regime.py
from jesse.strategies import Strategy
from jesse import utils
from jesse.indicators import adx as ta_adx, rsi as ta_rsi, ema as ta_ema, atr as ta_atr, bollinger_bands as ta_bb

class AnyMarket(Strategy):
    # --------------------
    # Hyperparamètres
    # --------------------
    adx_period      = 14
    adx_trend_th    = 25.0
    adx_range_th    = 20.0

    ema_fast        = 50
    ema_slow        = 200
    rsi_period      = 14
    rsi_buy_trend   = 50.0
    rsi_sell_trend  = 50.0

    bb_period       = 20
    bb_stdev        = 2.0
    rsi_mr_short    = 70.0
    rsi_mr_long     = 30.0

    atr_period      = 14
    sl_atr_mult     = 1.5     # stop en trend-mode
    tp_atr_mult     = 2.0     # take profit en trend-mode

    risk_perc       = 0.003   # ~0.3% du capital par trade (plus conservateur)
    neutral_buffer  = (20.0, 25.0)  # pas de trade si ADX entre ces bornes

    # trailing (optionnel) pour modes Trend
    enable_trailing = True
    trail_atr_mult  = 1.0
    arm_trailing_atr_move = 1.0  # arme le trailing après +1*ATR de latence favorable

    timeframe       = '4h'  # indice documentaire; défini dans routes

    def hyperparameters(self):
        # pour les optimisations / backtests paramétriques (facultatif)
        return [
            {'name': 'adx_trend_th', 'type': float, 'min': 20, 'max': 35, 'default': self.adx_trend_th},
            {'name': 'adx_range_th', 'type': float, 'min': 15, 'max': 25, 'default': self.adx_range_th},
            {'name': 'sl_atr_mult',  'type': float, 'min': 1.0, 'max': 2.5, 'default': self.sl_atr_mult},
            {'name': 'tp_atr_mult',  'type': float, 'min': 1.5, 'max': 3.0, 'default': self.tp_atr_mult},
            {'name': 'risk_perc',    'type': float, 'min': 0.001, 'max': 0.01, 'default': self.risk_perc},
        ]

    # --------------------
    # Indicateurs (helpers)
    # --------------------
    @property
    def last_candle(self):
        return self.candles[-1]

    @property
    def close(self):
        return float(self.last_candle[2])

    def _adx(self):
        return float(ta_adx(self.candles, self.adx_period))

    def _ema_fast(self):
        return float(ta_ema(self.candles, self.ema_fast))

    def _ema_slow(self):
        return float(ta_ema(self.candles, self.ema_slow))

    def _rsi(self, period=None):
        p = period or self.rsi_period
        return float(ta_rsi(self.candles, p))

    def _bb(self):
        lower, basis, upper = ta_bb(self.candles, self.bb_period, self.bb_stdev)
        return float(lower), float(basis), float(upper)

    def _atr(self):
        return float(ta_atr(self.candles, self.atr_period))

    # --------------------
    # Détection de régime
    # --------------------
    def regime(self):
        adx_val = self._adx()
        if adx_val < self.adx_range_th:
            return 'range'
        if adx_val > self.adx_trend_th:
            return 'trend'
        return 'neutral'

    # --------------------
    # Conditions d'entrée
    # --------------------
    def should_long(self) -> bool:
        r = self.regime()
        c = self.close
        if r == 'trend':
            ema_f = self._ema_fast()
            ema_s = self._ema_slow()
            rsi_v = self._rsi(self.rsi_period)
            # Trend-Long: tendance haussière "propre" + momentum > 50
            return c > ema_s and ema_f > ema_s and rsi_v > self.rsi_buy_trend
        elif r == 'range':
            lower, basis, upper = self._bb()
            rsi_v = self._rsi(7)  # RSI plus court pour MR
            # MR-Long: excès bas + signal de reversion
            return c < lower and rsi_v < self.rsi_mr_long
        else:
            return False

    def should_short(self) -> bool:
        r = self.regime()
        c = self.close
        if r == 'trend':
            ema_f = self._ema_fast()
            ema_s = self._ema_slow()
            rsi_v = self._rsi(self.rsi_period)
            # Trend-Short: tendance baissière "propre" + momentum < 50
            return c < ema_s and ema_f < ema_s and rsi_v < self.rsi_sell_trend
        elif r == 'range':
            lower, basis, upper = self._bb()
            rsi_v = self._rsi(7)
            # MR-Short: excès haut + signal de reversion
            return c > upper and rsi_v > self.rsi_mr_short
        else:
            return False

    def should_cancel_entry(self) -> bool:
        # Pas d'ordres limit persistent ici; entrées au marché
        return False

    # --------------------
    # Sizing & exécution
    # --------------------
    def _account_equity(self) -> float:
        # Jesse fournit self.available_balance / self.balance.
        # On essaie available_balance, sinon fallback sur balance.
        try:
            return float(self.available_balance)
        except Exception:
            try:
                return float(self.balance)
            except Exception:
                # fallback fixe si l'exchange mock n'expose pas les soldes
                return 10_000.0

    def _risk_qty(self, entry: float, stop: float) -> float:
        """
        Taille de position basée sur un risque fixe (risk_perc * equity).
        Pour du spot USDT: qty = risk / (entry - stop) ; clampé à >= 0.
        """
        equity = self._account_equity()
        risk_amount = max(0.0, equity * self.risk_perc)
        risk_per_unit = abs(entry - stop)
        if risk_per_unit <= 0:
            # fallback qty fixe si stop invalide
            return round( (equity * 0.02) / max(entry, 1e-9), 6)
        qty = risk_amount / risk_per_unit
        # sécurité (éviter des tailles débiles si ATR très petit)
        return round(min(qty, equity / max(entry, 1e-9)), 6)

    # --------------------
    # Entrées & sorties
    # --------------------
    def go_long(self):
        c = self.close
        atr = self._atr()
        r = self.regime()

        if r == 'trend':
            sl = c - self.sl_atr_mult * atr
            tp = c + self.tp_atr_mult * atr
        else:  # range
            lower, basis, upper = self._bb()
            sl = lower - 0.2 * atr  # léger buffer sous la bande
            tp = max(basis, c + 0.5 * atr)  # sécurité si basis trop proche

        # Utilise le sizing natif de Jesse en pourcentage du capital disponible
        risk_pct = self.hp['risk_perc'] * 100 if hasattr(self, 'hp') and 'risk_perc' in self.hp else self.risk_perc * 100
        qty = utils.risk_to_qty(self.available_margin, risk_pct, c, sl, fee_rate=self.fee_rate)
        self.buy = qty, c
        self.stop_loss = qty, sl
        self.take_profit = qty, tp

        # mémos internes pour trailing
        self.vars['entry_price'] = c
        self.vars['atr_at_entry'] = atr
        self.vars['mode'] = r
        self.vars['trailing_armed'] = False

    def go_short(self):
        c = self.close
        atr = self._atr()
        r = self.regime()

        if r == 'trend':
            sl = c + self.sl_atr_mult * atr
            tp = c - self.tp_atr_mult * atr
        else:  # range
            lower, basis, upper = self._bb()
            sl = upper + 0.2 * atr
            tp = min(basis, c - 0.5 * atr)

        risk_pct = self.hp['risk_perc'] * 100 if hasattr(self, 'hp') and 'risk_perc' in self.hp else self.risk_perc * 100
        qty = utils.risk_to_qty(self.available_margin, risk_pct, c, sl, fee_rate=self.fee_rate)
        self.sell = qty, c
        self.stop_loss = qty, sl
        self.take_profit = qty, tp

        self.vars['entry_price'] = c
        self.vars['atr_at_entry'] = atr
        self.vars['mode'] = r
        self.vars['trailing_armed'] = False

    def update_position(self):
        """
        Gestion active : trailing en trend-mode quand le prix a progressé d'au moins 1*ATR.
        """
        if not self.position:
            return
        try:
            mode = self.vars.get('mode', 'trend')
            entry = float(self.vars.get('entry_price', self.position.entry_price))
            atr0  = float(self.vars.get('atr_at_entry', self._atr()))
        except Exception:
            mode = 'trend'
            entry = self.position.entry_price
            atr0  = self._atr()

        c = self.close
        atr = self._atr()

        if self.enable_trailing and mode == 'trend':
            # Arme le trailing quand le prix a bougé d'au moins arm_trailing_atr_move*ATR en faveur
            if not self.vars.get('trailing_armed', False):
                if (self.is_long and c >= entry + self.arm_trailing_atr_move * atr0) or \
                   (self.is_short and c <= entry - self.arm_trailing_atr_move * atr0):
                    self.vars['trailing_armed'] = True

            if self.vars.get('trailing_armed', False):
                if self.is_long:
                    new_sl = max(self.average_stop_loss, c - self.trail_atr_mult * atr)
                    # ne jamais descendre un SL
                    if new_sl > self.average_stop_loss:
                        self.stop_loss = self.position.qty, new_sl
                else:
                    new_sl = min(self.average_stop_loss, c + self.trail_atr_mult * atr)
                    if new_sl < self.average_stop_loss:
                        self.stop_loss = self.position.qty, new_sl

    def should_add_position(self) -> bool:
        return False

    def go_add_position(self):
        pass

    def on_close_position(self, order):
        # Nettoyage
        self.vars['trailing_armed'] = False
        self.vars['mode'] = None
        self.vars['entry_price'] = None
        self.vars['atr_at_entry'] = None
