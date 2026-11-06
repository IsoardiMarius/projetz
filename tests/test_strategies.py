"""Tests des briques des stratégies, sur des données fictives."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from radar.phase0 import strategies

T0 = datetime(2026, 3, 1, tzinfo=UTC)


def test_cooldown_keeps_first_trigger_of_each_burst() -> None:
    hours = np.array([0, 1, 2, 30, 31, 60]) * 3600 * 10**9
    assert strategies._first_with_cooldown(hours, timedelta(hours=24)) == [0, 3, 5]


def test_wallet_history_uses_only_resolved_past_positions() -> None:
    signals = pd.DataFrame(
        {
            "wallet": ["w"] * 4,
            "signal_ts": pd.to_datetime(
                [T0, T0 + timedelta(days=1), T0 + timedelta(days=10), T0 + timedelta(days=20)],
                utc=True,
            ),
            "closed_time": pd.to_datetime(
                [
                    T0 + timedelta(days=5),
                    T0 + timedelta(days=6),
                    T0 + timedelta(days=30),
                    T0 + timedelta(days=40),
                ],
                utc=True,
            ),
            "won": [1.0, 1.0, 0.0, 1.0],
            "signal_vwap": [0.2, 0.5, 0.4, 0.3],
        }
    )
    hist = strategies.wallet_history(signals)
    assert hist["prior_n"].tolist() == [0.0, 0.0, 2.0, 2.0]
    expected_z = ((1 + 1) - (0.2 + 0.5)) / np.sqrt(0.2 * 0.8 + 0.5 * 0.5)
    assert hist["prior_z"].iloc[2] == pytest.approx(expected_z)
    assert hist["prior_z"].iloc[0] == 0.0
