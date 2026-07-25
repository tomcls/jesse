# filename: strategies/hma_trend/hma_trend.py
import math
import numpy as np
from jesse.strategies import Strategy
import jesse.indicators as ta  # pour ATR, ADX si tu veux
from jesse import utils

class HMA(Strategy):
    """
    HMA Trend-Follow (15m/30m)
    - Entrée long: HMA_fast croise au-dessus de HMA_slow + close > HMA_slow
    - SL = atr_mult_sl * ATR
    - TP = atr_mult_tp * ATR
    - Trailing: optionnel, sous HMA_fast
    """

  
    def hyperparameters(self):
        return [
            {"name": "hma_fast_len", "type": int, "min": 14, "max": 34, "default": 21},
            {"name": "hma_slow_len", "type": int, "min": 34, "max": 89, "default": 55},
            {"name": "atr_len",      "type": int, "min": 7,  "max": 28, "default": 14},
            {"name": "atr_mult_sl",  "type": float, "min": 0.8, "max": 2.0, "default": 1.2},
            {"name": "atr_mult_tp",  "type": float, "min": 1.6, "max": 3.5, "default": 2.4},
            {"name": "risk_pct", "type": float, "min": 2.4, "max": 3.6, "default": 3.0, "step": 0.2},
            # Optionnels
            {"name": "use_trailing", "type": int, "min": 0, "max": 1, "default": 1},  # 1 = on
            {"name": "adx_min",      "type": int, "min": 0, "max": 30, "default": 15},  # 0 = désactiver filtre
        ]

    # ---------- Utils HMA ----------
    def _wma(self, series: np.ndarray, length: int) -> np.ndarray:
        if length < 1:
            raise ValueError("length must be >= 1")

        series = np.asarray(series, dtype=float).ravel()   # ⚠️ force 1D array
        n = len(series)
        out = np.full(n, np.nan, dtype=float)
        if n < length:
            return out  # pas assez de données

        weights = np.arange(1, length + 1, dtype=float)
        wsum = weights.sum()
        for i in range(length - 1, n):
            window = series[i - length + 1:i + 1]
            out[i] = np.dot(window, weights) / wsum
        return out

    def _hma(self, series: np.ndarray, length: int) -> np.ndarray:
        series = np.asarray(series, dtype=float).ravel()
        if length < 2 or len(series) == 0:
            return series.astype(float)

        n2 = max(1, length // 2)
        sqrt_n = max(1, int(math.sqrt(length)))
        wma_n  = self._wma(series, length)
        wma_n2 = self._wma(series, n2)
        diff = 2 * wma_n2 - wma_n
        return self._wma(diff, sqrt_n)
    # ---------- Cached series ----------
    @property
    def _close(self) -> np.ndarray:
        # Série de close sur tout l’historique dispo (1D float)
        return self.candles[:, 2].astype(float)

    @property
    def hma_fast(self) -> np.ndarray:
        return self._hma(self._close, int(self.hp['hma_fast_len']))

    @property
    def hma_slow(self) -> np.ndarray:
        return self._hma(self._close, int(self.hp['hma_slow_len']))

    @property
    def atr(self) -> float:
        return float(ta.atr(self.candles, period=int(self.hp['atr_len'])))

    @property
    def adx(self) -> float:
        # Filtre directionnel optionnel ; renvoie 0 si non calculable
        try:
            return float(ta.adx(self.candles, period=14))
        except Exception:
            return 0.0

    # ---------- Conditions d'entrée/sortie ----------
    def _hma_cross_up(self) -> bool:
        hf, hs = self.hma_fast, self.hma_slow
        if len(hf) < 3 or len(hs) < 3:
            return False
        return (hf[-1] > hs[-1]) and (hf[-2] <= hs[-2])

    def _hma_cross_down(self) -> bool:
        hf, hs = self.hma_fast, self.hma_slow
        if len(hf) < 3 or len(hs) < 3:
            return False
        return (hf[-1] < hs[-1]) and (hf[-2] >= hs[-2])

    def should_long(self) -> bool:
        # Filtre tendance + croisement propre
        if np.isnan(self.hma_fast[-1]) or np.isnan(self.hma_slow[-1]):
            return False

        price_above_slow = self.price > self.hma_slow[-1]
        cross_up = self._hma_cross_up()

        # Filtre ADX optionnel : si adx_min > 0, on exige adx >= adx_min
        adx_ok = True
        if int(self.hp['adx_min']) > 0:
            adx_ok = self.adx >= int(self.hp['adx_min'])

        return cross_up and price_above_slow and adx_ok

    def should_short(self) -> bool:
        if np.isnan(self.hma_fast[-1]) or np.isnan(self.hma_slow[-1]):
            return False

        price_below_slow = self.price < self.hma_slow[-1]
        cross_down = self._hma_cross_down()

        adx_ok = True
        if int(self.hp['adx_min']) > 0:
            adx_ok = self.adx >= int(self.hp['adx_min'])

        return cross_down and price_below_slow and adx_ok

    def go_long(self):
        sl = self.price - float(self.hp['atr_mult_sl']) * self.atr
        tp = self.price + float(self.hp['atr_mult_tp']) * self.atr
        qty = utils.risk_to_qty(self.available_margin, self.hp['risk_pct'], self.price, sl, fee_rate=self.fee_rate)

        self.buy = qty, self.price
        self.stop_loss = qty, sl
        self.take_profit =qty, tp

    def go_short(self):
        sl = self.price + float(self.hp['atr_mult_sl']) * self.atr
        tp = self.price - float(self.hp['atr_mult_tp']) * self.atr
        qty = utils.risk_to_qty(self.available_margin, self.hp['risk_pct'], self.price, sl, fee_rate=self.fee_rate)

        self.sell = qty, self.price
        self.stop_loss = qty,sl
        self.take_profit =qty, tp

    def update_position(self):
        """
        Trailing stop (optionnel) : on suit HMA_fast avec un petit delta ATR.
        Active si use_trailing == 1.
        """
        if int(self.hp['use_trailing']) != 1 or self.position is None or self.position.qty == 0:
            return

        atr = self.atr
        pad = 0.6 * atr  # marge sous/sur HMA_fast
        hf = self.hma_fast[-1]

        if self.is_long:
            new_sl = max(self.average_stop_loss, hf - pad)
            # ne jamais baisser le SL
            if new_sl > self.average_stop_loss:
                self.stop_loss = self.position.qty, new_sl

        elif self.is_short:
            new_sl = min(self.average_stop_loss, hf + pad)
            if new_sl < self.average_stop_loss:
                self.stop_loss = self.position.qty, new_sl

    # (optionnel) Sécurité: si recroisement opposé, on sort
    def should_cancel(self) -> bool:
        if self.is_long:
            return self._hma_cross_down() or (self.price < self.hma_slow[-1])
        if self.is_short:
            return self._hma_cross_up() or (self.price > self.hma_slow[-1])
        return False
