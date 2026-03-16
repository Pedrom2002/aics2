"""Tests for the demo parser service module."""

from unittest.mock import MagicMock

import pytest

from src.services.demo_parser import (
    ParsedDemo,
    _classify_win_reason,
    parse_demo,
)


def _make_mock_demo_cls(mock_dem):
    """Create a mock Demo class that returns the given instance."""

    class MockDemo:
        def __init__(self, path):
            self._path = path
            # Copy attributes from mock
            self.header = mock_dem.header
            self.rounds = mock_dem.rounds
            self.kills = mock_dem.kills
            self.damages = mock_dem.damages
            self.ticks = mock_dem.ticks

        def parse(self, **kwargs):
            pass

    return MockDemo


def _make_mock_dem():
    """Create a mock awpy Demo with realistic CS2 data."""
    import polars as pl

    mock_dem = MagicMock()
    mock_dem.header = {"map_name": "de_dust2", "server_name": "Test Server"}

    mock_dem.rounds = pl.DataFrame(
        {
            "round_num": [1, 2, 3],
            "start": [1000, 5000, 9000],
            "freeze_end": [2000, 6000, 10000],
            "end": [4000, 8000, 12000],
            "winner": ["T", "CT", "T"],
            "reason": ["Elimination", "BombDefused", "BombExploded"],
            "bomb_plant": [0, 6500, 10500],
            "bomb_site": [None, "B", "A"],
        }
    )

    mock_dem.kills = pl.DataFrame(
        {
            "steamid": [100, 100, 200, 100, 200],
            "name": ["PlayerA", "PlayerA", "PlayerB", "PlayerA", "PlayerB"],
            "victim_steamid": [200, 200, 100, 200, 100],
            "victim_name": ["PlayerB", "PlayerB", "PlayerA", "PlayerB", "PlayerA"],
            "round_num": [1, 1, 2, 3, 3],
            "headshot": [True, False, True, False, False],
            "assister_steamid": [None, None, None, None, None],
            "assistedflash": [False, False, False, False, False],
        }
    )

    mock_dem.damages = pl.DataFrame(
        {
            "steamid": [100, 100, 200, 100, 200],
            "name": ["PlayerA", "PlayerA", "PlayerB", "PlayerA", "PlayerB"],
            "dmg_health_real": [100, 85, 100, 70, 90],
            "weapon": ["ak47", "ak47", "m4a1", "hegrenade", "m4a1"],
        }
    )

    mock_dem.ticks = pl.DataFrame({"tick": [], "steamid": [], "name": [], "round_num": []})

    return mock_dem


class TestClassifyWinReason:
    def test_bomb_exploded(self):
        assert _classify_win_reason("BombExploded") == "bomb_exploded"
        assert _classify_win_reason("bomb_explosion") == "bomb_exploded"

    def test_defuse(self):
        assert _classify_win_reason("BombDefused") == "defuse"
        assert _classify_win_reason("defuse") == "defuse"

    def test_elimination(self):
        assert _classify_win_reason("Elimination") == "elimination"
        assert _classify_win_reason("TerroristKilled") == "elimination"

    def test_time(self):
        assert _classify_win_reason("TimeExpired") == "time"
        assert _classify_win_reason("timer_ran_out") == "time"

    def test_none(self):
        assert _classify_win_reason(None) is None

    def test_unknown_truncated(self):
        long_reason = "x" * 50
        result = _classify_win_reason(long_reason)
        assert len(result) == 30


class TestParseDemoFileNotFound:
    def test_raises_on_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            parse_demo(tmp_path / "nonexistent.dem")


class TestParseDemo:
    """Test parse_demo with a mocked awpy Demo object."""

    def test_basic(self, tmp_path):
        dem_file = tmp_path / "test.dem"
        dem_file.write_bytes(b"fake demo")
        mock_dem = _make_mock_dem()

        result = parse_demo(dem_file, _demo_cls=_make_mock_demo_cls(mock_dem))

        assert isinstance(result, ParsedDemo)
        assert result.map_name == "de_dust2"
        assert result.team1_score == 2  # T wins
        assert result.team2_score == 1  # CT wins
        assert result.total_rounds == 3
        assert result.overtime_rounds == 0

    def test_rounds(self, tmp_path):
        dem_file = tmp_path / "test.dem"
        dem_file.write_bytes(b"fake demo")
        mock_dem = _make_mock_dem()

        result = parse_demo(dem_file, _demo_cls=_make_mock_demo_cls(mock_dem))

        assert len(result.rounds) == 3

        r1 = result.rounds[0]
        assert r1.round_number == 1
        assert r1.winner_side == "T"
        assert r1.win_reason == "elimination"
        assert r1.team1_score == 1
        assert r1.team2_score == 0

        r2 = result.rounds[1]
        assert r2.winner_side == "CT"
        assert r2.win_reason == "defuse"
        assert r2.bomb_defused is True

        r3 = result.rounds[2]
        assert r3.winner_side == "T"
        assert r3.win_reason == "bomb_exploded"
        assert r3.plant_site == "A"

    def test_players(self, tmp_path):
        dem_file = tmp_path / "test.dem"
        dem_file.write_bytes(b"fake demo")
        mock_dem = _make_mock_dem()

        result = parse_demo(dem_file, _demo_cls=_make_mock_demo_cls(mock_dem))

        assert len(result.players) == 2

        player_a = next(p for p in result.players if p.name == "PlayerA")
        player_b = next(p for p in result.players if p.name == "PlayerB")

        assert player_a.kills == 3
        assert player_a.deaths == 2
        assert player_a.headshot_kills == 1
        assert player_a.damage == 255  # 100 + 85 + 70
        assert player_a.utility_damage == 70  # hegrenade damage

        assert player_b.kills == 2
        assert player_b.deaths == 3

    def test_first_kills(self, tmp_path):
        dem_file = tmp_path / "test.dem"
        dem_file.write_bytes(b"fake demo")
        mock_dem = _make_mock_dem()

        result = parse_demo(dem_file, _demo_cls=_make_mock_demo_cls(mock_dem))

        player_a = next(p for p in result.players if p.name == "PlayerA")
        player_b = next(p for p in result.players if p.name == "PlayerB")

        # PlayerA gets first kill in rounds 1 and 3
        assert player_a.first_kills == 2
        # PlayerB gets first kill in round 2
        assert player_b.first_kills == 1

    def test_adr(self, tmp_path):
        dem_file = tmp_path / "test.dem"
        dem_file.write_bytes(b"fake demo")
        mock_dem = _make_mock_dem()

        result = parse_demo(dem_file, _demo_cls=_make_mock_demo_cls(mock_dem))

        player_a = next(p for p in result.players if p.name == "PlayerA")
        # ADR = 255 / 3 rounds = 85.0
        assert player_a.adr == 85.0
