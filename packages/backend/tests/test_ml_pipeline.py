"""Tests for the ML error detection pipeline.

Tests cover:
  - Feature extraction (positioning windows, utility features)
  - Heuristic labeling (positioning errors from death events)
  - Recommendation engine (template matching)
  - ML inference pipeline (heuristic baseline)
  - API endpoints (match errors, player errors)
"""

import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import TestSessionLocal

# ============ Feature Extraction Tests ============


class TestPositioningFeatureExtraction:
    def test_ticks_to_features_shape(self):
        from src.services.ml_feature_extractor import TickSnapshot, _ticks_to_features

        ticks = [
            TickSnapshot(
                tick=i,
                round_number=1,
                player_steam_id="123",
                pos_x=100.0,
                pos_y=200.0,
                pos_z=50.0,
                velocity=150.0,
                health=100,
                armor=100,
                angles_exposed_count=2,
                distance_to_nearest_cover=150.0,
            )
            for i in range(64)
        ]
        features = _ticks_to_features(ticks)
        assert features.shape == (64, 18)
        # Check normalization
        assert features[0, 0] == pytest.approx(100.0 / 1000.0)  # pos_x normalized
        assert features[0, 6] == pytest.approx(1.0)  # health=100 / 100

    def test_extract_windows_empty(self):
        from src.services.ml_feature_extractor import extract_positioning_windows

        windows = extract_positioning_windows([], [])
        assert windows == []

    def test_extract_windows_creates_windows(self):
        from src.services.ml_feature_extractor import TickSnapshot, extract_positioning_windows

        ticks = [TickSnapshot(tick=i, round_number=1, player_steam_id="p1") for i in range(128)]
        windows = extract_positioning_windows(ticks, [], window_size=64, stride=32)
        assert len(windows) >= 2
        assert windows[0].features.shape == (64, 18)
        assert windows[0].player_steam_id == "p1"


class TestHeuristicLabeling:
    def test_critical_error_label(self):
        import numpy as np

        from src.services.ml_feature_extractor import (
            PlayerDeathEvent,
            PositioningWindow,
            _apply_heuristic_labels,
        )

        death = PlayerDeathEvent(
            tick=100,
            round_number=1,
            player_steam_id="p1",
            pos_x=0,
            pos_y=0,
            pos_z=0,
            angles_exposed=3,
            distance_to_cover=300.0,
            had_teammate_nearby=False,
            was_traded=False,
        )
        window = PositioningWindow(
            features=np.zeros((64, 18)),
            player_steam_id="p1",
            round_number=1,
            center_tick=100,
        )
        _apply_heuristic_labels([window], [death])
        assert window.label == 2  # critical

    def test_minor_error_label(self):
        import numpy as np

        from src.services.ml_feature_extractor import (
            PlayerDeathEvent,
            PositioningWindow,
            _apply_heuristic_labels,
        )

        death = PlayerDeathEvent(
            tick=100,
            round_number=1,
            player_steam_id="p1",
            pos_x=0,
            pos_y=0,
            pos_z=0,
            angles_exposed=2,
            distance_to_cover=50.0,  # close to cover
            had_teammate_nearby=False,
            was_traded=False,
        )
        window = PositioningWindow(
            features=np.zeros((64, 18)),
            player_steam_id="p1",
            round_number=1,
            center_tick=100,
        )
        _apply_heuristic_labels([window], [death])
        assert window.label == 1  # minor (2 angles, not traded)

    def test_no_error_when_traded(self):
        import numpy as np

        from src.services.ml_feature_extractor import (
            PlayerDeathEvent,
            PositioningWindow,
            _apply_heuristic_labels,
        )

        death = PlayerDeathEvent(
            tick=100,
            round_number=1,
            player_steam_id="p1",
            pos_x=0,
            pos_y=0,
            pos_z=0,
            angles_exposed=2,
            distance_to_cover=50.0,
            had_teammate_nearby=True,
            was_traded=True,
        )
        window = PositioningWindow(
            features=np.zeros((64, 18)),
            player_steam_id="p1",
            round_number=1,
            center_tick=100,
        )
        _apply_heuristic_labels([window], [death])
        assert window.label == 0  # no error (was traded)

    def test_no_error_when_no_death(self):
        import numpy as np

        from src.services.ml_feature_extractor import PositioningWindow, _apply_heuristic_labels

        window = PositioningWindow(
            features=np.zeros((64, 18)),
            player_steam_id="p1",
            round_number=1,
            center_tick=100,
        )
        _apply_heuristic_labels([window], [])
        assert window.label == 0


class TestUtilityFeatureExtraction:
    def test_extract_flash_features(self):
        from src.services.ml_feature_extractor import GrenadeEvent, extract_utility_features

        event = GrenadeEvent(
            tick=100,
            round_number=1,
            player_steam_id="p1",
            grenade_type="flash",
            enemies_flashed_count=2,
            flash_duration_avg=2.5,
        )
        vectors = extract_utility_features([event])
        assert len(vectors) == 1
        assert vectors[0].features.shape == (25,)
        assert vectors[0].label == 0  # effective (2 flashed)

    def test_wasted_flash_label(self):
        from src.services.ml_feature_extractor import GrenadeEvent, extract_utility_features

        event = GrenadeEvent(
            tick=100,
            round_number=1,
            player_steam_id="p1",
            grenade_type="flash",
            enemies_flashed_count=0,
        )
        vectors = extract_utility_features([event])
        assert vectors[0].label == 2  # wasted

    def test_effective_smoke_label(self):
        from src.services.ml_feature_extractor import GrenadeEvent, extract_utility_features

        event = GrenadeEvent(
            tick=100,
            round_number=1,
            player_steam_id="p1",
            grenade_type="smoke",
            smoke_blocks_los_count=1,
        )
        vectors = extract_utility_features([event])
        assert vectors[0].label == 0  # effective


# ============ Recommendation Engine Tests ============


class TestRecommendationEngine:
    def test_positioning_critical_multi_angle(self):
        from src.services.recommendation_engine import generate_positioning_recommendation

        rec = generate_positioning_recommendation(
            "critical",
            {"angles_exposed": 4, "distance_to_cover": 300, "position_area": "mid"},
        )
        assert rec.priority == 1
        assert "angles" in rec.title.lower() or "exposed" in rec.title.lower()
        assert rec.template_id == "pos_multi_angle_001"

    def test_positioning_minor_no_trade(self):
        from src.services.recommendation_engine import generate_positioning_recommendation

        rec = generate_positioning_recommendation(
            "minor",
            {"angles_exposed": 2, "distance_to_cover": 50, "had_teammate_nearby": False},
        )
        assert rec.priority <= 2
        assert "trade" in rec.description.lower() or "teammate" in rec.description.lower()

    def test_utility_wasted_flash(self):
        from src.services.recommendation_engine import generate_utility_recommendation

        rec = generate_utility_recommendation(
            predicted_class=2,  # wasted
            grenade_type="flash",
            context={"enemies_flashed_count": 0},
        )
        assert rec.priority <= 2
        assert "flash" in rec.title.lower()

    def test_timing_early_peek(self):
        from src.services.recommendation_engine import generate_timing_recommendation

        rec = generate_timing_recommendation(
            predicted_class=1,  # too_early
            context={"has_flash_available": True},
        )
        assert "flash" in rec.description.lower()


# ============ ML Inference Tests ============


class TestMLInference:
    def test_heuristic_positioning_analysis(self):
        from src.services.ml_feature_extractor import PlayerDeathEvent
        from src.services.ml_inference import run_heuristic_positioning_analysis

        deaths = [
            PlayerDeathEvent(
                tick=100,
                round_number=1,
                player_steam_id="p1",
                pos_x=0,
                pos_y=0,
                pos_z=0,
                angles_exposed=3,
                distance_to_cover=300.0,
                had_teammate_nearby=False,
                was_traded=False,
            ),
            PlayerDeathEvent(
                tick=200,
                round_number=2,
                player_steam_id="p1",
                pos_x=0,
                pos_y=0,
                pos_z=0,
                angles_exposed=1,
                distance_to_cover=50.0,
                had_teammate_nearby=True,
                was_traded=True,
            ),
        ]
        results = run_heuristic_positioning_analysis(deaths)
        assert len(results) == 1  # Only first death is an error
        assert results[0].severity == "critical"
        assert results[0].error_type == "positioning"
        assert results[0].rec_title  # Has recommendation

    def test_full_ml_analysis(self):
        from src.services.ml_feature_extractor import PlayerDeathEvent
        from src.services.ml_inference import run_ml_analysis

        deaths = [
            PlayerDeathEvent(
                tick=100,
                round_number=3,
                player_steam_id="p2",
                pos_x=500,
                pos_y=600,
                pos_z=0,
                angles_exposed=4,
                distance_to_cover=400.0,
                had_teammate_nearby=False,
                was_traded=False,
            ),
        ]
        results = run_ml_analysis(deaths, [])
        assert len(results) == 1
        assert results[0].explanation_text
        assert results[0].feature_importances_json


# ============ API Endpoint Tests ============


class TestMLEndpoints:
    @pytest.mark.asyncio
    async def test_match_errors_empty(self, client: AsyncClient):
        """Match with no errors returns empty list."""
        fake_id = str(uuid.uuid4())
        resp = await client.get(f"/api/v1/matches/{fake_id}/errors")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_errors"] == 0
        assert data["errors"] == []

    @pytest.mark.asyncio
    async def test_match_errors_with_data(self, client: AsyncClient):
        """Store errors and retrieve them via API."""
        from src.models.demo import Demo
        from src.models.detected_error import DetectedError, ErrorExplanation, ErrorRecommendation
        from src.models.match import Match
        from src.models.organization import Organization

        async with TestSessionLocal() as session:
            org = Organization(name="TestOrg", slug="testorg")
            session.add(org)
            await session.flush()

            demo = Demo(
                org_id=org.id,
                uploaded_by=uuid.uuid4(),
                s3_key="test.dem",
                original_filename="test.dem",
                file_size_bytes=1000,
                checksum_sha256="abc123",
                status="completed",
            )
            session.add(demo)
            await session.flush()

            match = Match(
                demo_id=demo.id,
                org_id=org.id,
                map="de_mirage",
                total_rounds=30,
                team1_score=16,
                team2_score=14,
            )
            session.add(match)
            await session.flush()

            error = DetectedError(
                match_id=match.id,
                org_id=org.id,
                player_steam_id="76561198000000001",
                round_number=5,
                error_type="positioning",
                severity="critical",
                confidence=0.85,
                tick=12345,
                position_x=100.0,
                position_y=200.0,
                description="Died exposed to 3 angles",
                model_name="positioning_heuristic",
                model_version="0.1.0-heuristic",
            )
            session.add(error)
            await session.flush()

            session.add(
                ErrorExplanation(
                    error_id=error.id,
                    feature_importances='[{"feature": "angles_exposed", "value": 3, "impact": 0.45}]',
                    method="heuristic",
                    explanation_text="Critical positioning error",
                )
            )
            session.add(
                ErrorRecommendation(
                    error_id=error.id,
                    title="Reduce angle exposure",
                    description="Hold from cover",
                    priority=1,
                    template_id="pos_multi_angle_001",
                    expected_impact="30% fewer deaths",
                )
            )
            await session.commit()
            match_id = str(match.id)

        resp = await client.get(f"/api/v1/matches/{match_id}/errors")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_errors"] == 1
        assert data["critical_count"] == 1
        assert data["errors"][0]["severity"] == "critical"
        assert data["errors"][0]["explanation"]["method"] == "heuristic"
        assert data["errors"][0]["recommendation"]["title"] == "Reduce angle exposure"

    @pytest.mark.asyncio
    async def test_player_errors_not_found(self, client: AsyncClient):
        resp = await client.get("/api/v1/players/unknown_steam_id/errors")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_player_errors_with_data(self, client: AsyncClient):
        """Store errors for a player and retrieve summary."""
        from src.models.demo import Demo
        from src.models.detected_error import DetectedError, ErrorRecommendation
        from src.models.match import Match
        from src.models.organization import Organization

        steam_id = "76561198000000099"

        async with TestSessionLocal() as session:
            org = Organization(name="TestOrg2", slug="testorg2")
            session.add(org)
            await session.flush()

            demo = Demo(
                org_id=org.id,
                uploaded_by=uuid.uuid4(),
                s3_key="test2.dem",
                original_filename="test2.dem",
                file_size_bytes=1000,
                checksum_sha256="def456",
                status="completed",
            )
            session.add(demo)
            await session.flush()

            match = Match(
                demo_id=demo.id,
                org_id=org.id,
                map="de_dust2",
                total_rounds=25,
                team1_score=13,
                team2_score=12,
            )
            session.add(match)
            await session.flush()

            for i, (etype, sev) in enumerate(
                [
                    ("positioning", "critical"),
                    ("positioning", "minor"),
                    ("utility", "minor"),
                ]
            ):
                err = DetectedError(
                    match_id=match.id,
                    org_id=org.id,
                    player_steam_id=steam_id,
                    round_number=i + 1,
                    error_type=etype,
                    severity=sev,
                    confidence=0.8,
                    description=f"Test error {i}",
                    model_name="test",
                    model_version="0.1.0",
                )
                session.add(err)
                await session.flush()

                session.add(
                    ErrorRecommendation(
                        error_id=err.id,
                        title=f"Fix {etype} issue",
                        description=f"Recommendation for {etype}",
                        priority=i + 1,
                        template_id=f"test_{i}",
                    )
                )

            await session.commit()

        resp = await client.get(f"/api/v1/players/{steam_id}/errors")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_errors"] == 3
        assert data["positioning_errors"] == 2
        assert data["utility_errors"] == 1
        assert data["critical_count"] == 1
        assert len(data["top_recommendations"]) >= 1
