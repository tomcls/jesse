# strategies/eth_btc_stat_arb.py
from jesse.strategies import Strategy
import numpy as np
import jesse.indicators as ta


class ETHBTCStatArb(Strategy):
    #
    # ------- Paramètres (adaptables / optimisables) -------
    #
    z_entry = 2         # |z| au-delà duquel on entre
    z_exit  = 0.2          # zone "vers la moyenne" pour sortir si pas de cross net
    lookback_ratio = 70    # fenêtre de moyenne/écart-type du ratio
    ema_trend_len = 200    # filtre de tendance (EMA)
    atr_len = 14           # ATR pour stop de sécurité
    atr_mult = 3.0         # distance du stop de sécurité (en ATR)
    risk_per_trade = 0.01  # % du capital risqué par trade (dimensionnement)

    other_symbol = 'ETC-USDT'
    other_tf_sec = 0       # 0 => même TF que la stratégie (recommandé)

    #
    # --------------- Utilitaires internes -----------------
    #
    def _timeframe_seconds(self) -> int:
        """
        Renvoie la durée de la timeframe active en secondes.
        (Jesse renseigne self.timeframe en str '1m','5m','1h', etc. depuis v0.42+)
        """
        tf = self.timeframe
        if tf.endswith('m'):
            return int(tf[:-1]) * 60
        if tf.endswith('h'):
            return int(tf[:-1]) * 3600
        if tf.endswith('D') or tf.endswith('d'):
            return int(tf[:-1]) * 86400
        # fallback: 30m si non détecté
        return 1800

    def _get_eth_closes(self, n: int) -> np.ndarray:
        # Use the same exchange and timeframe as the current route for alignment
        c = self.get_candles(self.exchange, self.other_symbol, self.timeframe)
        closes = c[:, 2]  # index 2 = close
        if len(closes) < n:
            return np.array([])
        return closes[-n:]

    def _zscore_ratio(self):
        """
        Calcule le z-score du ratio ETH/BTC sur 'lookback_ratio'.
        Retourne (z_current, z_prev) pour détecter les crosses.
        """
        lb = max(self.lookback_ratio, 5)

        # ETH closes (courant symbole)
        eth_closes = self.candles[:, 2]  # série de clôtures alignée
        if len(eth_closes) < lb + 1:
            return None, None

        # BTC closes alignés
        btc_closes = self._get_eth_closes(lb + 1)
        if btc_closes is None or len(btc_closes) < lb + 1:
            return None, None

        # Construire le ratio ETH/BTC aligné fin de série
        # ETH close est un scalaire "current close" + historique via self.candles[:,2]
        eth_hist = self.candles[:, 2]
        eth_hist = eth_hist[-(lb + 1):]
        ratio = eth_hist / btc_closes  # vectorisé

        mean = np.mean(ratio[-lb:])
        std = np.std(ratio[-lb:])
        if std == 0:
            return None, None

        z_prev = (ratio[-2] - mean) / std
        z_curr = (ratio[-1] - mean) / std
        return z_curr, z_prev

    def _tp_price_from_z_target(self, z_target: float) -> float:
        """
        Calcule le prix ETH cible correspondant à un z-score visé (z_target),
        en utilisant le ratio ETH / other_symbol.
        """
        lb = max(self.lookback_ratio, 5)

        # Série des clôtures ETH alignée
        eth_hist = self.candles[:, 2]
        if len(eth_hist) < lb + 1:
            return 0.0
        eth_hist = eth_hist[-(lb + 1):]

        # Série des clôtures de l'autre actif (dénominateur du ratio)
        other_closes = self._get_eth_closes(lb + 1)
        if other_closes is None or len(other_closes) < lb + 1:
            return 0.0

        ratio = eth_hist / other_closes
        std = np.std(ratio[-lb:])
        if std == 0:
            return 0.0
        mean = np.mean(ratio[-lb:])

        # Ratio et prix cibles
        r_target = mean + z_target * std
        other_last = other_closes[-1]
        return float(r_target * other_last)

    def _trend_ok(self) -> bool:
        """
        Filtre de tendance : ETH et BTC au-dessus de leur EMA200,
        avec EMA200 en pente positive (moyenne > moyenne(lag)).
        """
        # ETH
        if len(self.candles) < self.ema_trend_len + 1:
            return False
        eth_ema = ta.ema(self.candles, self.ema_trend_len, sequential=True)
        eth_above = self.price > eth_ema[-1]
        eth_slope_pos = eth_ema[-1] > eth_ema[-2]

        # BTC
        btc_c = self.get_candles(self.exchange, self.other_symbol, self.timeframe)
        if len(btc_c) < self.ema_trend_len + 1:
            return False
        btc_ema = ta.ema(btc_c, self.ema_trend_len, sequential=True)
        btc_above = btc_c[-1, 2] > btc_ema[-1]
        btc_slope_pos = btc_ema[-1] > btc_ema[-2]

        return eth_above and eth_slope_pos and btc_above and btc_slope_pos

    def _position_size_by_atr(self, side: str) -> float:
        """
        Dimensionne la position pour risquer ~ risk_per_trade du capital
        avec un stop ATR * atr_mult. Simple et robuste.
        """
        atr = ta.atr(self.candles, self.atr_len)
        if atr <= 0:
            return 0.0
        stop_dist = self.atr_mult * atr
        capital_risk = self.available_margin * self.risk_per_trade
        qty = capital_risk / max(stop_dist, 1e-9)
        # convertir en quantité d'ETH (spot/futures) :
        return max(qty, 0.0)

    #
    # -------------------- Hooks Jesse ----------------------
    #
    def should_long(self) -> bool:
        z, z_prev = self._zscore_ratio()
        if z is None:
            return False
        # Entrée long ETH si ratio trop bas (ETH "sous-performe" BTC) + filtre tendance
        return (z < -self.z_entry) and self._trend_ok()

    def should_short(self) -> bool:
        z, z_prev = self._zscore_ratio()
        if z is None:
            return False
        # Entrée short ETH si ratio trop haut (ETH "surperforme" BTC) + filtre tendance inversé?
        # Ici, on garde le même filtre haussier (arbitrage "soft" dans tendances saines).
        # Si tu veux autoriser short aussi en tendance baissière, retire self._trend_ok().
        return (z > self.z_entry) 

    def go_long(self):
        qty = self._position_size_by_atr('long')
        if qty > 0:
            self.buy = qty, self.price

    def go_short(self):
        qty = self._position_size_by_atr('short')
        if qty > 0:
            self.sell = qty, self.price

    # def on_open_position(self, order) -> None:
    #     """
    #     Place un stop sécurité basé sur ATR et un take-profit fixe
    #     correspondant au retour à la moyenne du z-score (z_target = 0).
    #     """
    #     atr = ta.atr(self.candles, self.atr_len)
    #     if self.is_long:
    #         self.stop_loss = self.position.qty, self.position.entry_price - self.atr_mult * atr
    #         tp_price = self._tp_price_from_z_target(0.0)  # utilisez -self.z_entry ou -self.z_exit si souhaité
    #         if tp_price > 0:
    #             self.take_profit = self.position.qty, tp_price
    #     elif self.is_short:
    #         self.stop_loss = self.position.qty, self.position.entry_price + self.atr_mult * atr
    #         tp_price = self._tp_price_from_z_target(0.0)  # utilisez +self.z_entry ou +self.z_exit si souhaité
    #         if tp_price > 0:
    #             self.take_profit = self.position.qty, tp_price

    def update_position(self):
        """
        Sortie conditionnelle :
        - LONG  : si zscore remonte vers 0 (cross up −z_exit ou cross 0)
        - SHORT : si zscore retombe vers 0 (cross down +z_exit ou cross 0)
        + Stop de sécurité basé ATR.
        """
        if self.is_close:
            return

        z, z_prev = self._zscore_ratio()
        if z is None:
            return

        # Stop catastrophe (ATR)
        atr = ta.atr(self.candles, self.atr_len)
        if self.is_long:
            stop_price = self.position.entry_price - self.atr_mult * atr
            if self.price <= stop_price:
                self.liquidate()
                return

            # sortie “mean reversion”
            # on sort si le z-score revient vers la moyenne
            if (z_prev < -self.z_exit and z >= -self.z_exit) or (z_prev < 0 <= z):
                self.liquidate()

        elif self.is_short:
            stop_price = self.position.entry_price + self.atr_mult * atr
            if self.price >= stop_price:
                self.liquidate()
                return

            if (z_prev > self.z_exit and z <= self.z_exit) or (z_prev > 0 >= z):
                self.liquidate()

    def should_cancel_entry(self) -> bool:
        return False
