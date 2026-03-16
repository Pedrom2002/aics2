"""Tests for the feature engine service."""

import pytest

from src.services.feature_engine import (
    AggregatedPlayerStats,
    PlayerFeatures,
    compute_aggregated_stats,
    compute_match_features,
)


class TestComputeMatchFeatures:
    """Tests for per-match feature computation."""

    def test_basic_features(self):
        features = compute_match_features(
            player_steam_id="76561198000000001",
            player_name="s1mple",
            match_id="match-1",
            kills=28,
            deaths=15,
            assists=4,
            headshot_kills=14,
            damage=2100,
            total_rounds=23,
            flash_assists=2,
            utility_damage=120,
            first_kills=6,
            first_deaths=2,
            trade_kills=3,
            trade_deaths=2,
            clutch_wins=2,
            multi_kills_3k=3,
            multi_kills_4k=1,
            multi_kills_5k=0,
            kast_rounds=19,
            rounds_survived=12,
        )

        assert isinstance(features, PlayerFeatures)
        assert features.player_steam_id == "76561198000000001"

        # KPR = 28/23 = 1.217
        assert features.kills_per_round == pytest.approx(1.217, abs=0.001)
        # DPR = 15/23 = 0.652
        assert features.deaths_per_round == pytest.approx(0.652, abs=0.001)
        # KD = 28/15 = 1.87
        assert features.kd_ratio == pytest.approx(1.87, abs=0.01)
        # HS% = 14/28 * 100 = 50.0
        assert features.headshot_pct == pytest.approx(50.0, abs=0.1)
        # ADR = 2100/23 = 91.3
        assert features.adr == pytest.approx(91.3, abs=0.1)

    def test_opening_duel_stats(self):
        features = compute_match_features(
            player_steam_id="1",
            player_name="test",
            match_id="m1",
            kills=20,
            deaths=10,
            assists=5,
            headshot_kills=10,
            damage=1500,
            total_rounds=20,
            flash_assists=1,
            utility_damage=50,
            first_kills=6,
            first_deaths=2,
            trade_kills=2,
            trade_deaths=1,
            clutch_wins=1,
            multi_kills_3k=2,
            multi_kills_4k=0,
            multi_kills_5k=0,
            kast_rounds=16,
            rounds_survived=12,
        )

        assert features.opening_duel_attempts == 8  # 6 + 2
        assert features.opening_duel_win_rate == pytest.approx(75.0, abs=0.1)

    def test_kast_and_survival(self):
        features = compute_match_features(
            player_steam_id="1",
            player_name="test",
            match_id="m1",
            kills=15,
            deaths=10,
            assists=3,
            headshot_kills=7,
            damage=1200,
            total_rounds=25,
            flash_assists=2,
            utility_damage=80,
            first_kills=3,
            first_deaths=2,
            trade_kills=1,
            trade_deaths=1,
            clutch_wins=0,
            multi_kills_3k=1,
            multi_kills_4k=0,
            multi_kills_5k=0,
            kast_rounds=20,
            rounds_survived=15,
        )

        # KAST% = 20/25 * 100 = 80.0
        assert features.kast_pct == pytest.approx(80.0, abs=0.1)
        # Survival = 15/25 * 100 = 60.0
        assert features.survival_rate == pytest.approx(60.0, abs=0.1)

    def test_hltv_rating_positive(self):
        features = compute_match_features(
            player_steam_id="1",
            player_name="test",
            match_id="m1",
            kills=20,
            deaths=10,
            assists=5,
            headshot_kills=10,
            damage=1500,
            total_rounds=20,
            flash_assists=2,
            utility_damage=100,
            first_kills=5,
            first_deaths=2,
            trade_kills=3,
            trade_deaths=1,
            clutch_wins=1,
            multi_kills_3k=2,
            multi_kills_4k=0,
            multi_kills_5k=0,
            kast_rounds=16,
            rounds_survived=12,
        )

        assert features.hltv_rating_approx > 0
        assert features.impact_rating > 0

    def test_zero_rounds_no_division_error(self):
        features = compute_match_features(
            player_steam_id="1",
            player_name="test",
            match_id="m1",
            kills=0,
            deaths=0,
            assists=0,
            headshot_kills=0,
            damage=0,
            total_rounds=0,
            flash_assists=0,
            utility_damage=0,
            first_kills=0,
            first_deaths=0,
            trade_kills=0,
            trade_deaths=0,
            clutch_wins=0,
            multi_kills_3k=0,
            multi_kills_4k=0,
            multi_kills_5k=0,
            kast_rounds=0,
            rounds_survived=0,
        )

        assert features.kills_per_round == 0.0
        assert features.kd_ratio == 0.0
        assert features.hltv_rating_approx >= 0


class TestComputeAggregatedStats:
    """Tests for multi-match aggregation."""

    def _make_match_stats(self, kills=20, deaths=10, total_rounds=20, map_name="de_mirage"):
        return {
            "match_id": "m1",
            "player_name": "test",
            "kills": kills,
            "deaths": deaths,
            "assists": 5,
            "headshot_kills": kills // 2,
            "damage": kills * 80,
            "flash_assists": 2,
            "utility_damage": 50,
            "first_kills": 3,
            "first_deaths": 1,
            "trade_kills": 2,
            "trade_deaths": 1,
            "clutch_wins": 1,
            "multi_kills_3k": 1,
            "multi_kills_4k": 0,
            "multi_kills_5k": 0,
            "kast_rounds": total_rounds - 3,
            "rounds_survived": total_rounds - deaths,
            "total_rounds": total_rounds,
            "map": map_name,
        }

    def test_single_match(self):
        stats = compute_aggregated_stats("steam1", [self._make_match_stats()])
        assert isinstance(stats, AggregatedPlayerStats)
        assert stats.total_matches == 1
        assert stats.total_kills == 20
        assert stats.total_deaths == 10
        assert stats.avg_kd_ratio == 2.0

    def test_multiple_matches(self):
        matches = [
            self._make_match_stats(kills=25, deaths=10, map_name="de_mirage"),
            self._make_match_stats(kills=15, deaths=15, map_name="de_dust2"),
            self._make_match_stats(kills=20, deaths=12, map_name="de_mirage"),
        ]
        stats = compute_aggregated_stats("steam1", matches)

        assert stats.total_matches == 3
        assert stats.total_kills == 60
        assert stats.total_deaths == 37
        assert stats.maps_played == {"de_mirage": 2, "de_dust2": 1}
        assert stats.best_map == "de_mirage"

    def test_consistency_std_deviation(self):
        matches = [
            self._make_match_stats(kills=30, deaths=5, total_rounds=20),
            self._make_match_stats(kills=5, deaths=20, total_rounds=20),
        ]
        stats = compute_aggregated_stats("steam1", matches)

        assert stats.rating_std_deviation > 0
        assert len(stats.match_ratings) == 2

    def test_empty_match_stats(self):
        stats = compute_aggregated_stats("steam1", [])
        assert stats.total_matches == 0
        assert stats.total_kills == 0
        assert stats.player_name == "Unknown"
