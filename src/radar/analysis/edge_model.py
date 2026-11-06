"""Modèle « avantage sur le prix » : ce trade gagne-t-il plus souvent que son prix ne le dit ?

Formulation : régression logistique avec le logit du prix d'entrée en *offset*.
logit P(gain) = logit(prix) + β · x. Si toutes les caractéristiques x sont sans valeur, β ≈ 0
et le modèle redonne le prix du marché. Tout ce que le modèle ajoute au prix est donc
l'avantage estimé, mesuré hors échantillon.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold

EPS = 1e-4


def logit(p: np.ndarray) -> np.ndarray:
    q = np.clip(p, EPS, 1 - EPS)
    return np.asarray(np.log(q / (1 - q)), dtype=float)


def log_loss(y: np.ndarray, p: np.ndarray) -> float:
    q = np.clip(p, EPS, 1 - EPS)
    return float(-np.mean(y * np.log(q) + (1 - y) * np.log(1 - q)))


@dataclass
class OffsetLogit:
    """Régression logistique avec offset et pénalité L2 (ajustement de Newton / IRLS).

    Les caractéristiques sont standardisées ; l'interception n'est pas pénalisée. Les valeurs
    manquantes valent la moyenne (0 après standardisation).
    """

    c: float = 1.0
    coef_: np.ndarray | None = None
    intercept_: float = 0.0
    mean_: np.ndarray | None = None
    scale_: np.ndarray | None = None

    def fit(self, x: np.ndarray, y: np.ndarray, offset: np.ndarray) -> OffsetLogit:
        self.mean_ = np.nanmean(x, axis=0)
        self.scale_ = np.nanstd(x, axis=0)
        self.scale_[self.scale_ == 0] = 1.0
        z = self._z(x)
        beta = np.zeros(z.shape[1] + 1)
        design = np.column_stack([np.ones(len(z)), z])
        penalty = np.eye(design.shape[1]) / self.c
        penalty[0, 0] = 0.0
        for _ in range(50):
            eta = offset + design @ beta
            mu = 1 / (1 + np.exp(-eta))
            w = np.clip(mu * (1 - mu), 1e-6, None)
            grad = design.T @ (y - mu) - penalty @ beta
            hess = design.T @ (design * w[:, None]) + penalty
            step = np.linalg.solve(hess, grad)
            beta += step
            if np.max(np.abs(step)) < 1e-8:
                break
        self.intercept_ = float(beta[0])
        self.coef_ = beta[1:]
        return self

    def _z(self, x: np.ndarray) -> np.ndarray:
        assert self.mean_ is not None
        assert self.scale_ is not None
        z = (x - self.mean_) / self.scale_
        return np.asarray(np.nan_to_num(z, nan=0.0), dtype=float)

    def predict_proba(self, x: np.ndarray, offset: np.ndarray) -> np.ndarray:
        assert self.coef_ is not None
        eta = offset + self.intercept_ + self._z(x) @ self.coef_
        return np.asarray(1 / (1 + np.exp(-eta)), dtype=float)


@dataclass(frozen=True)
class CvResult:
    predictions: pd.Series  # probabilité hors échantillon, alignée sur les lignes d'entrée
    loss_model: float
    loss_price: float
    coefficients: pd.Series  # moyenne des coefficients standardisés sur les plis


def cross_validate(
    data: pd.DataFrame,
    features: Sequence[str],
    *,
    price_col: str,
    target_col: str = "won",
    group_col: str = "event_id",
    folds: int = 5,
    c: float = 0.5,
) -> CvResult:
    """Prédictions hors échantillon par validation croisée groupée par événement.

    Un événement entier (tous ses marchés corrélés) est toujours du même côté de la coupe.
    """
    x = data[list(features)].to_numpy(dtype=float)
    y = data[target_col].to_numpy(dtype=float)
    offset = logit(data[price_col].to_numpy(dtype=float))
    groups = data[group_col].astype(str).to_numpy()
    preds = np.full(len(data), np.nan)
    coefs = []
    splitter = GroupKFold(n_splits=min(folds, len(np.unique(groups))))
    for train, test in splitter.split(x, y, groups):
        model = OffsetLogit(c=c).fit(x[train], y[train], offset[train])
        preds[test] = model.predict_proba(x[test], offset[test])
        assert model.coef_ is not None
        coefs.append(model.coef_)
    price = np.clip(data[price_col].to_numpy(dtype=float), EPS, 1 - EPS)
    return CvResult(
        predictions=pd.Series(preds, index=data.index),
        loss_model=log_loss(y, preds),
        loss_price=log_loss(y, price),
        coefficients=pd.Series(np.mean(coefs, axis=0), index=list(features)),
    )


def cross_validate_gbm(
    data: pd.DataFrame,
    features: Sequence[str],
    *,
    price_col: str,
    target_col: str = "won",
    group_col: str = "event_id",
    folds: int = 5,
) -> tuple[pd.Series, float]:
    """Même protocole avec un modèle non linéaire (gradient boosting, fortement régularisé).

    Le logit du prix est une caractéristique comme les autres (pas d'offset possible ici).
    Renvoie les prédictions hors échantillon et leur log-loss.
    """
    x = data[list(features)].to_numpy(dtype=float)
    y = data[target_col].to_numpy(dtype=int)
    groups = data[group_col].astype(str).to_numpy()
    preds = np.full(len(data), np.nan)
    splitter = GroupKFold(n_splits=min(folds, len(np.unique(groups))))
    for train, test in splitter.split(x, y, groups):
        model = HistGradientBoostingClassifier(
            max_depth=3,
            learning_rate=0.05,
            max_iter=300,
            min_samples_leaf=100,
            l2_regularization=1.0,
            early_stopping=True,
            validation_fraction=0.2,
            random_state=0,
        ).fit(x[train], y[train])
        preds[test] = model.predict_proba(x[test])[:, 1]
    return pd.Series(preds, index=data.index), log_loss(y.astype(float), preds)


def sklearn_sanity_check(x: np.ndarray, y: np.ndarray) -> float:
    """Contrôle croisé avec scikit-learn (sans offset) : utilisé dans les tests."""
    model = LogisticRegression(C=1e6, max_iter=1000).fit(x, y)
    return float(model.coef_[0][0])
