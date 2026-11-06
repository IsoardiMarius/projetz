"""Tests du modèle « avantage sur le prix » et des caractéristiques, sur données simulées."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from radar.analysis import edge_model, features

T0 = datetime(2026, 3, 1, tzinfo=UTC)


def test_question_flags() -> None:
    f = features.question_flags("Will Israel strike Lebanon on January 22, 2026?")
    assert f["q_military"] == 1.0
    assert f["q_exact_day"] == 1.0
    assert f["q_date_ladder"] == 1.0
    g = features.question_flags("Will María Corina Machado win the Nobel Peace Prize in 2025?")
    assert g["q_award"] == 1.0
    assert g["q_military"] == 0.0


def test_flow_features_use_only_the_past() -> None:
    signals = pd.DataFrame(
        {
            "signal_ts": [T0, T0 + timedelta(hours=1), T0 + timedelta(hours=8)],
            "signal_usdc": [1000.0, 2000.0, 500.0],
            "wallet_age": [pd.Timedelta(days=1), pd.Timedelta(days=100), pd.NaT],
        }
    )
    view = pd.DataFrame(
        {
            "ts": [T0 - timedelta(hours=2), T0 - timedelta(minutes=30), T0 + timedelta(hours=2)],
            "price": [0.10, 0.20, 0.90],
            "ask": [True, True, True],
            "usdc": [100.0, 300.0, 5000.0],
        }
    )
    out = features.flow_features(signals, view)
    assert out["n_signals_6h"].tolist() == [0, 1, 0]  # le 3e est à 7 h du 2e
    assert out["n_new_signals_6h"].tolist() == [0, 1, 0]
    assert out["vol_24h"].iloc[0] == pytest.approx(400.0)  # le trade à +2 h n'est pas vu
    assert out["mom_1h"].iloc[0] == pytest.approx(0.10)  # 0,10 une heure avant, 0,20 juste avant
    assert out["share_24h"].iloc[0] == pytest.approx(1000 / 400)


def test_wallet_track_record_ignores_unresolved_markets() -> None:
    signals = pd.DataFrame(
        {
            "wallet": ["w", "w", "w"],
            "signal_ts": [T0, T0 + timedelta(days=1), T0 + timedelta(days=10)],
            "won": [True, True, False],
            "signal_vwap": [0.2, 0.3, 0.4],
        }
    )
    closed = pd.Series([T0 + timedelta(days=5), T0 + timedelta(days=20), T0 + timedelta(days=30)])
    out = features.wallet_track_record(signals, closed)
    # Au 2e signal, le 1er marché n'est pas encore résolu ; au 3e, seul le 1er l'est.
    assert out["prior_n"].tolist() == [0.0, 0.0, 1.0]
    assert out["prior_excess"].iloc[2] == pytest.approx((1 - 0.2) / 6)


def _simulated(n: int, informative: bool, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    price = rng.uniform(0.05, 0.6, n)
    x = rng.normal(size=n)
    eta = edge_model.logit(price) + (1.2 * x if informative else 0.0)
    won = rng.uniform(size=n) < 1 / (1 + np.exp(-eta))
    return pd.DataFrame({"price": price, "x": x, "won": won, "event_id": rng.integers(0, 50, n)})


def test_offset_logit_returns_price_when_features_are_noise() -> None:
    data = _simulated(4000, informative=False)
    cv = edge_model.cross_validate(data, ["x"], price_col="price")
    assert abs(cv.coefficients["x"]) < 0.1
    assert cv.loss_model == pytest.approx(cv.loss_price, abs=0.01)


def test_offset_logit_finds_real_edge() -> None:
    data = _simulated(4000, informative=True)
    cv = edge_model.cross_validate(data, ["x"], price_col="price")
    assert cv.coefficients["x"] > 0.8
    assert cv.loss_model < cv.loss_price - 0.05


def test_offset_logit_matches_sklearn_without_offset() -> None:
    rng = np.random.default_rng(3)
    x = rng.normal(size=(3000, 1))
    y = (rng.uniform(size=3000) < 1 / (1 + np.exp(-(0.5 + 0.9 * x[:, 0])))).astype(float)
    ours = edge_model.OffsetLogit(c=1e9).fit(x, y, np.zeros(3000))
    assert ours.coef_ is not None
    assert ours.scale_ is not None
    assert ours.coef_[0] / ours.scale_[0] == pytest.approx(
        edge_model.sklearn_sanity_check(x, y), rel=1e-3
    )


def test_gbm_cross_validation_finds_nonlinear_edge() -> None:
    rng = np.random.default_rng(5)
    n = 6000
    price = rng.uniform(0.05, 0.6, n)
    x = rng.normal(size=n)
    # Avantage seulement quand x est grand : effet non linéaire.
    eta = edge_model.logit(price) + np.where(x > 1.0, 2.0, 0.0)
    won = rng.uniform(size=n) < 1 / (1 + np.exp(-eta))
    data = pd.DataFrame(
        {
            "price": price,
            "lp": edge_model.logit(price),
            "x": x,
            "won": won,
            "event_id": rng.integers(0, 60, n),
        }
    )
    _, loss = edge_model.cross_validate_gbm(data, ["lp", "x"], price_col="price")
    assert loss < edge_model.log_loss(won.astype(float), price) - 0.01
