"""Tests des fonctions d'analyse, sur des marchés fictifs construits à la main."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from radar.analysis import copy_sim, detector, fees, prices

YES, NO = "Y", "N"
T0 = datetime(2026, 2, 27, 12, 0, tzinfo=UTC)


def at(minutes: float) -> datetime:
    return T0 + timedelta(minutes=minutes)


def frame(rows: list[tuple[float, str, str, str, float, float, bool]]) -> pd.DataFrame:
    """(minutes, wallet, jeton, côté, taille, prix, taker) -> DataFrame de trades."""
    return pd.DataFrame(
        [
            {
                "condition_id": "c1",
                "ts": pd.Timestamp(at(m)),
                "wallet": w,
                "token_id": tok,
                "side": side,
                "size": size,
                "price": price,
                "is_taker": taker,
            }
            for m, w, tok, side, size, price, taker in rows
        ]
    )


# --- Frais -----------------------------------------------------------------------------------


def test_fee_rate_priority_and_formula() -> None:
    assert fees.taker_rate(["politics", "geopolitics"]) == 0.0
    assert fees.taker_rate(["politics"]) == 0.04
    assert fees.taker_rate([]) == fees.DEFAULT_RATE
    assert fees.taker_fee_per_share(0.5, 0.04) == pytest.approx(0.01)
    with pytest.raises(ValueError, match="hors de"):
        fees.taker_fee_per_share(1.5, 0.04)


# --- Prix ------------------------------------------------------------------------------------


def test_token_view_combines_complementary_token_and_skips_makers() -> None:
    trades = frame(
        [
            (0, "a", YES, "BUY", 10, 0.30, True),  # ask YES à 0,30
            (1, "b", NO, "SELL", 10, 0.65, True),  # vendre NO à 0,65 = acheter YES à 0,35
            (2, "c", NO, "BUY", 10, 0.60, True),  # acheter NO à 0,60 = vendre YES à 0,40
            (2, "m", YES, "SELL", 10, 0.30, False),  # ligne maker : ignorée
        ]
    )
    view = prices.token_view(trades, YES)
    assert view["price"].round(2).tolist() == [0.30, 0.35, 0.40]
    assert view["ask"].tolist() == [True, True, False]


def test_ask_price_after_respects_max_wait() -> None:
    view = prices.token_view(frame([(10, "a", YES, "BUY", 1, 0.2, True)]), YES)
    assert prices.ask_price_after(view, at(0)) == (at(10), 0.2)
    assert prices.ask_price_after(view, at(0), max_wait=timedelta(minutes=5)) is None
    assert prices.ask_price_after(view, at(11)) is None
    assert prices.ask_price_after(view, at(10)) == (at(10), 0.2)
    assert prices.ask_price_after(view, at(10), strict=True) is None


def test_information_time_after_last_surprise() -> None:
    rows = [(m, "a", YES, "BUY", 1, 0.1, True) for m in range(0, 120, 5)]
    rows += [(m, "a", YES, "BUY", 1, 0.95, True) for m in range(120, 300, 5)]
    t_info = prices.information_time(prices.token_view(frame(rows), YES))
    assert t_info is not None
    assert at(120) <= t_info <= at(150)


def test_information_time_none_when_winner_always_favourite() -> None:
    rows = [(m, "a", YES, "BUY", 1, 0.9, True) for m in range(0, 120, 5)]
    assert prices.information_time(prices.token_view(frame(rows), YES)) is None


# --- Détecteur -------------------------------------------------------------------------------


def test_signal_fires_when_cumulative_low_price_buys_cross_threshold() -> None:
    trades = frame(
        [
            (0, "w", YES, "BUY", 2000, 0.20, True),  # 400 $
            (5, "w", YES, "BUY", 1000, 0.50, True),  # prix trop haut : ignoré
            (9, "w", YES, "BUY", 2000, 0.25, False),  # 500 $ (maker compté) : 900 $
            (12, "w", YES, "BUY", 1000, 0.30, True),  # 300 $ : 1 200 $ -> signal
            (15, "w", YES, "BUY", 9000, 0.30, True),  # après le signal
            (20, "x", YES, "BUY", 100, 0.10, True),  # trop petit
        ]
    )
    signals = detector.accumulation_signals(trades, detector.Rule())
    assert len(signals) == 1
    s = signals.iloc[0]
    assert s["wallet"] == "w"
    assert pd.Timestamp(s["signal_ts"]) == pd.Timestamp(at(12))
    assert s["signal_usdc"] == pytest.approx(1200)
    assert s["signal_vwap"] == pytest.approx(1200 / 5000)
    assert pd.Timestamp(s["first_buy_ts"]) == pd.Timestamp(at(0))


def test_alert_requires_known_recent_wallet() -> None:
    signals = pd.DataFrame(
        {
            "wallet": ["new", "old", "unknown"],
            "signal_ts": [pd.Timestamp(at(0))] * 3,
        }
    )
    profiles = pd.DataFrame(
        {
            "wallet": ["new", "old"],
            "first_activity_ts": [pd.Timestamp(at(-60 * 24)), pd.Timestamp(at(-60 * 24 * 30))],
        }
    )
    deposits = pd.DataFrame(
        {"wallet": ["new", "new"], "ts": [pd.Timestamp(at(-120)), pd.Timestamp(at(30))]}
    )
    ctx = detector.add_wallet_context(signals, profiles, deposits)
    ctx = ctx.set_index("wallet")
    assert detector.is_alert(ctx.reset_index(), detector.Rule()).tolist() == [True, False, False]
    # Le dépôt postérieur au signal n'est pas vu (pas d'anticipation).
    assert ctx.loc["new", "since_deposit"] == pd.Timedelta(minutes=120)


# --- Suiveur ---------------------------------------------------------------------------------


def test_follower_return() -> None:
    assert copy_sim.follower_return(0.25, True, 0.0) == pytest.approx(3.0)
    assert copy_sim.follower_return(0.25, False, 0.0) == pytest.approx(-1.0)
    with_fee = copy_sim.follower_return(0.5, True, 0.04)
    assert with_fee == pytest.approx(1 / 0.51 - 1)


def test_simulate_enters_later_at_worse_price_and_stops_at_close() -> None:
    trades = frame(
        [
            (0, "w", YES, "BUY", 5000, 0.20, True),
            (3, "z", YES, "BUY", 10, 0.40, True),
            (70, "z", YES, "BUY", 10, 0.80, True),
        ]
    )
    signals = detector.accumulation_signals(trades, detector.Rule())
    views = {YES: prices.token_view(trades, YES)}
    market = copy_sim.MarketInfo(winning_token_id=YES, closed_time=at(60), fee_rate=0.0)
    out = copy_sim.simulate(
        signals,
        views,
        {"c1": market},
        delays=[timedelta(0), timedelta(minutes=1), timedelta(minutes=65)],
    )
    # Jamais dans le bloc du signal : la 1re entrée possible est l'exécution de la 3e minute.
    assert out["entry_price"].tolist() == [0.40, 0.40, 0.80]
    assert out["filled"].tolist() == [True, True, False]  # 3e entrée après la clôture
    assert out["ret"].iloc[0] == pytest.approx(1.5)


# --- Statistiques ----------------------------------------------------------------------------


def test_cluster_bootstrap_mean_point_and_bounds() -> None:
    from radar.analysis.stats import cluster_bootstrap_mean, wilson_interval

    values = pd.Series([1.0, 1.0, 0.0, 0.0, 0.0, 0.0])
    clusters = pd.Series(["a", "a", "b", "b", "c", "c"])
    est = cluster_bootstrap_mean(values, clusters, n_boot=500, seed=1)
    assert est.value == pytest.approx(1 / 3)
    assert est.n == 6
    assert est.clusters == 3
    assert 0.0 <= est.low <= est.value <= est.high <= 1.0
    low, high = wilson_interval(5, 10)
    assert low < 0.5 < high
