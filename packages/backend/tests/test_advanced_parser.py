"""Tests for advanced parser stats: multi-kills, clutches, trade kills, KAST."""

from src.services.demo_parser import (
    RoundData,
    _classify_buy_type,
    _compute_advanced_stats,
    _is_pistol_round,
    _KillEvent,
)


class TestClassifyBuyType:
    def test_eco(self):
        assert _classify_buy_type(1500) == "eco"

    def test_force(self):
        assert _classify_buy_type(3000) == "force"

    def test_semi(self):
        assert _classify_buy_type(4000) == "semi"

    def test_full(self):
        assert _classify_buy_type(5000) == "full"


class TestIsPistolRound:
    def test_round_1(self):
        assert _is_pistol_round(1) is True

    def test_round_16(self):
        assert _is_pistol_round(16) is True

    def test_round_5(self):
        assert _is_pistol_round(5) is False


class TestComputeAdvancedStats:
    def _make_rounds(self, n=5) -> list[RoundData]:
        return [
            RoundData(
                round_number=i + 1,
                winner_side="T" if i % 2 == 0 else "CT",
                win_reason="elimination",
                team1_score=0,
                team2_score=0,
            )
            for i in range(n)
        ]

    def test_multi_kills(self):
        """Player with 3 kills in round 1 should get a 3k."""
        kills = [
            _KillEvent(
                tick=100,
                round_num=1,
                killer_sid="p1",
                victim_sid="e1",
                killer_side="T",
                victim_side="CT",
            ),
            _KillEvent(
                tick=200,
                round_num=1,
                killer_sid="p1",
                victim_sid="e2",
                killer_side="T",
                victim_side="CT",
            ),
            _KillEvent(
                tick=300,
                round_num=1,
                killer_sid="p1",
                victim_sid="e3",
                killer_side="T",
                victim_side="CT",
            ),
        ]
        rounds = self._make_rounds(1)
        result = _compute_advanced_stats(
            kills, rounds, {"p1": "T", "e1": "CT", "e2": "CT", "e3": "CT"}, {}, 1
        )

        assert result["multi_3k"]["p1"] == 1
        assert result["multi_4k"].get("p1", 0) == 0

    def test_4k(self):
        """Player with 4 kills in a round."""
        kills = [
            _KillEvent(
                tick=100 + i * 100,
                round_num=1,
                killer_sid="p1",
                victim_sid=f"e{i + 1}",
                killer_side="T",
                victim_side="CT",
            )
            for i in range(4)
        ]
        rounds = self._make_rounds(1)
        sides = {"p1": "T"} | {f"e{i + 1}": "CT" for i in range(4)}
        result = _compute_advanced_stats(kills, rounds, sides, {}, 1)

        assert result["multi_3k"]["p1"] == 1  # 4k also counts as 3k+
        assert result["multi_4k"]["p1"] == 1

    def test_trade_kills(self):
        """Kill within TRADE_KILL_WINDOW_TICKS of teammate death = trade kill."""
        kills = [
            # Enemy kills our teammate p2 at tick 1000
            _KillEvent(
                tick=1000,
                round_num=1,
                killer_sid="e1",
                victim_sid="p2",
                killer_side="CT",
                victim_side="T",
            ),
            # p1 trades the kill at tick 1200 (200 ticks later, within 320 window)
            _KillEvent(
                tick=1200,
                round_num=1,
                killer_sid="p1",
                victim_sid="e1",
                killer_side="T",
                victim_side="CT",
            ),
        ]
        rounds = self._make_rounds(1)
        sides = {"p1": "T", "p2": "T", "e1": "CT"}
        result = _compute_advanced_stats(kills, rounds, sides, {}, 1)

        assert result["trade_kills"]["p1"] == 1
        assert result["trade_deaths"]["p2"] == 1

    def test_no_trade_kill_outside_window(self):
        """Kill outside the trade window should not count."""
        kills = [
            _KillEvent(
                tick=1000,
                round_num=1,
                killer_sid="e1",
                victim_sid="p2",
                killer_side="CT",
                victim_side="T",
            ),
            # p1 kills at tick 1500 (500 ticks later, outside 320 window)
            _KillEvent(
                tick=1500,
                round_num=1,
                killer_sid="p1",
                victim_sid="e1",
                killer_side="T",
                victim_side="CT",
            ),
        ]
        rounds = self._make_rounds(1)
        sides = {"p1": "T", "p2": "T", "e1": "CT"}
        result = _compute_advanced_stats(kills, rounds, sides, {}, 1)

        assert result["trade_kills"].get("p1", 0) == 0

    def test_kast_kill(self):
        """Player with a kill in the round should get KAST."""
        kills = [
            _KillEvent(
                tick=100,
                round_num=1,
                killer_sid="p1",
                victim_sid="e1",
                killer_side="T",
                victim_side="CT",
            ),
        ]
        rounds = self._make_rounds(1)
        sides = {"p1": "T", "e1": "CT"}
        result = _compute_advanced_stats(kills, rounds, sides, {}, 1)

        assert result["kast_rounds"]["p1"] == 1

    def test_kast_survived(self):
        """Player who survives the round (no death) should get KAST."""
        # e1 kills e2, p1 is not involved but survives
        kills = [
            _KillEvent(
                tick=100,
                round_num=1,
                killer_sid="e1",
                victim_sid="e2",
                killer_side="CT",
                victim_side="CT",
            ),
        ]
        rounds = self._make_rounds(1)
        sides = {"p1": "T", "e1": "CT", "e2": "CT"}
        result = _compute_advanced_stats(kills, rounds, sides, {}, 1)

        # p1 survived (not in dead_in_round)
        assert result["kast_rounds"]["p1"] == 1

    def test_kast_assisted(self):
        """Player with an assist should get KAST."""
        kills = [
            _KillEvent(
                tick=100,
                round_num=1,
                killer_sid="e1",
                victim_sid="p1",
                killer_side="CT",
                victim_side="T",
            ),
        ]
        rounds = self._make_rounds(1)
        sides = {"p1": "T", "p2": "T", "e1": "CT"}
        # p2 assisted in round 1
        assists_per_round = {"p2": {1}}
        result = _compute_advanced_stats(kills, rounds, sides, assists_per_round, 1)

        assert result["kast_rounds"]["p2"] == 1

    def test_rounds_survived(self):
        """Count rounds where player was not killed."""
        kills = [
            # p1 dies in round 1
            _KillEvent(
                tick=100,
                round_num=1,
                killer_sid="e1",
                victim_sid="p1",
                killer_side="CT",
                victim_side="T",
            ),
            # No deaths in round 2
        ]
        rounds = self._make_rounds(2)
        sides = {"p1": "T", "e1": "CT"}
        result = _compute_advanced_stats(kills, rounds, sides, {}, 2)

        assert result["rounds_survived"]["p1"] == 1  # survived round 2

    def test_clutch_win(self):
        """Last player alive on winning team should get clutch win."""
        kills = [
            # 4 T players die first
            _KillEvent(
                tick=100,
                round_num=1,
                killer_sid="ct1",
                victim_sid="t1",
                killer_side="CT",
                victim_side="T",
            ),
            _KillEvent(
                tick=200,
                round_num=1,
                killer_sid="ct2",
                victim_sid="t2",
                killer_side="CT",
                victim_side="T",
            ),
            _KillEvent(
                tick=300,
                round_num=1,
                killer_sid="ct3",
                victim_sid="t3",
                killer_side="CT",
                victim_side="T",
            ),
            _KillEvent(
                tick=400,
                round_num=1,
                killer_sid="ct4",
                victim_sid="t4",
                killer_side="CT",
                victim_side="T",
            ),
            # t5 (last T alive) gets 2 kills to win
            _KillEvent(
                tick=500,
                round_num=1,
                killer_sid="t5",
                victim_sid="ct1",
                killer_side="T",
                victim_side="CT",
            ),
            _KillEvent(
                tick=600,
                round_num=1,
                killer_sid="t5",
                victim_sid="ct2",
                killer_side="T",
                victim_side="CT",
            ),
        ]
        rounds = [RoundData(round_number=1, winner_side="T", win_reason="elimination")]
        sides = {
            "t1": "T",
            "t2": "T",
            "t3": "T",
            "t4": "T",
            "t5": "T",
            "ct1": "CT",
            "ct2": "CT",
            "ct3": "CT",
            "ct4": "CT",
            "ct5": "CT",
        }
        result = _compute_advanced_stats(kills, rounds, sides, {}, 1)

        assert result["clutch_wins"]["t5"] == 1
