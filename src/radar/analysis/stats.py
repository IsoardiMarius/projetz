"""Outils statistiques : intervalles de confiance robustes à la corrélation entre marchés.

Les marchés d'un même événement (« frappe avant le 28/02 », « avant le 1/03 »…) ne sont pas
indépendants. Le bootstrap rééchantillonne donc des **grappes** (événements) entières, et
non des lignes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Estimate:
    value: float
    low: float
    high: float
    n: int
    clusters: int

    def fmt(self, pct: bool = True) -> str:
        if self.n == 0 or math.isnan(self.value):
            return "—"
        if pct:
            return f"{self.value:+.0%} [{self.low:+.0%} ; {self.high:+.0%}]"
        return f"{self.value:.2f} [{self.low:.2f} ; {self.high:.2f}]"


def cluster_bootstrap_mean(
    values: pd.Series, clusters: pd.Series, *, n_boot: int = 2000, seed: int = 0, level: float = 0.9
) -> Estimate:
    """Moyenne et intervalle de confiance par bootstrap de grappes (percentiles)."""
    data = pd.DataFrame({"v": values.astype(float), "c": clusters.astype(str)}).dropna()
    if data.empty:
        return Estimate(math.nan, math.nan, math.nan, 0, 0)
    sums = data.groupby("c")["v"].agg(["sum", "count"])
    s = sums["sum"].to_numpy()
    k = sums["count"].to_numpy()
    point = float(s.sum() / k.sum())
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(s), size=(n_boot, len(s)))
    boot = s[idx].sum(axis=1) / k[idx].sum(axis=1)
    alpha = (1.0 - level) / 2.0
    low, high = np.quantile(boot, [alpha, 1.0 - alpha])
    return Estimate(point, float(low), float(high), int(k.sum()), len(s))


def wilson_interval(successes: int, n: int, z: float = 1.645) -> tuple[float, float]:
    """Intervalle de Wilson pour une proportion (90 % par défaut)."""
    if n == 0:
        return (math.nan, math.nan)
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (centre - half, centre + half)
