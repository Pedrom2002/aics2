"""
Recommendation Engine — Template-based actionable suggestions for detected errors.

Maps detected errors to specific improvement recommendations using:
  - Error type + context → template matching
  - Feature attributions → context-aware description filling
  - Pro player reference (when available)
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Recommendation:
    """An actionable recommendation for a detected error."""

    title: str
    description: str
    priority: int  # 1=high, 2=medium, 3=low
    template_id: str
    expected_impact: str
    pro_reference: str | None = None


# ---------- POSITIONING ERROR TEMPLATES ----------

POSITIONING_TEMPLATES: list[dict] = [
    {
        "id": "pos_multi_angle_001",
        "severity": ["critical"],
        "condition": lambda ctx: ctx.get("angles_exposed", 0) >= 3,
        "title": "Exposed to multiple angles",
        "description": (
            "You were exposed to {angles_exposed} angles simultaneously while holding "
            "{position_area}. Cover was available {distance_to_cover:.0f} units away. "
            "Limit exposure to 1-2 angles max by using nearby cover."
        ),
        "expected_impact": "30-50% reduction in positioning deaths",
        "priority": 1,
    },
    {
        "id": "pos_no_cover_002",
        "severity": ["critical", "minor"],
        "condition": lambda ctx: ctx.get("distance_to_cover", 0) > 200,
        "title": "Too far from cover",
        "description": (
            "You were {distance_to_cover:.0f} units from the nearest cover when engaged. "
            "At this distance, you cannot escape or jiggle-peek effectively. "
            "Stay within 100 units of cover for better survivability."
        ),
        "expected_impact": "25% improvement in survival rate",
        "priority": 1,
    },
    {
        "id": "pos_no_trade_003",
        "severity": ["minor"],
        "condition": lambda ctx: not ctx.get("had_teammate_nearby", False),
        "title": "No teammate in trade position",
        "description": (
            "You died without a teammate close enough to trade. "
            "Ensure at least one teammate is within 800 units and has a clear angle "
            "for a trade kill. Coordinate before peeking."
        ),
        "expected_impact": "20% increase in trade rate after death",
        "priority": 2,
    },
    {
        "id": "pos_overexposed_004",
        "severity": ["minor"],
        "condition": lambda ctx: ctx.get("angles_exposed", 0) >= 2,
        "title": "Holding too wide",
        "description": (
            "You held a wide angle exposing yourself to {angles_exposed} opponents. "
            "Consider jiggle-peeking or using utility (flash/smoke) before committing "
            "to a wide peek."
        ),
        "expected_impact": "15% fewer opening deaths",
        "priority": 2,
    },
    {
        "id": "pos_default_005",
        "severity": ["critical", "minor"],
        "condition": lambda _ctx: True,  # fallback
        "title": "Positioning improvement needed",
        "description": (
            "Review your position at this moment. Consider: angles of exposure, "
            "distance to cover, teammate positions for trade potential, and whether "
            "utility usage could improve your position."
        ),
        "expected_impact": "General positioning improvement",
        "priority": 3,
    },
]

# ---------- UTILITY ERROR TEMPLATES ----------

UTILITY_TEMPLATES: list[dict] = [
    {
        "id": "util_wasted_flash_001",
        "grenade_type": "flash",
        "classes": [2],  # wasted
        "condition": lambda ctx: ctx.get("enemies_flashed_count", 0) == 0,
        "title": "Wasted flash — no enemies blinded",
        "description": (
            "Your flash didn't blind any enemies. Before throwing, verify enemy "
            "positions with info utility or teammate callouts. Practice pop-flashes "
            "for common angles."
        ),
        "expected_impact": "40% increase in flash effectiveness",
        "priority": 1,
    },
    {
        "id": "util_bad_smoke_002",
        "grenade_type": "smoke",
        "classes": [2],  # wasted
        "condition": lambda _ctx: True,
        "title": "Ineffective smoke placement",
        "description": (
            "Your smoke didn't block any relevant lines of sight. Study common "
            "smoke lineups for this map and position. Ensure smokes land before "
            "your team's execute timing."
        ),
        "expected_impact": "Better site executes with proper smoke coverage",
        "priority": 2,
    },
    {
        "id": "util_low_damage_003",
        "grenade_type": "he",
        "classes": [1, 2],  # suboptimal or wasted
        "condition": lambda ctx: ctx.get("he_damage_dealt", 0) < 10,
        "title": "Low damage HE grenade",
        "description": (
            "Your HE grenade dealt minimal damage ({he_damage_dealt:.0f}). "
            "Time HE throws to land when enemies are likely stacked in tight "
            "spaces. Consider using molotov for area denial instead."
        ),
        "expected_impact": "20% more damage per HE on average",
        "priority": 2,
    },
    {
        "id": "util_molly_miss_004",
        "grenade_type": "molotov",
        "classes": [2],  # wasted
        "condition": lambda _ctx: True,
        "title": "Ineffective molotov",
        "description": (
            "Your molotov didn't deal damage or deny a useful area. "
            "Use molotovs to clear common hiding spots or deny plant/defuse. "
            "Practice lineups for key positions."
        ),
        "expected_impact": "Better area denial and flush utility",
        "priority": 2,
    },
    {
        "id": "util_default_005",
        "grenade_type": None,
        "classes": [1, 2, 3],
        "condition": lambda _ctx: True,
        "title": "Utility usage needs improvement",
        "description": (
            "Review your utility usage in this round. Consider timing, placement, "
            "and coordination with teammates for maximum impact."
        ),
        "expected_impact": "General utility improvement",
        "priority": 3,
    },
]

# ---------- TIMING ERROR TEMPLATES ----------

TIMING_TEMPLATES: list[dict] = [
    {
        "id": "timing_early_peek_001",
        "classes": [1],  # too_early
        "condition": lambda ctx: ctx.get("has_flash_available", False),
        "title": "Peeked without using available flash",
        "description": (
            "You peeked early without using your flash. Always consider flashing "
            "before dry-peeking, especially when you have utility available."
        ),
        "expected_impact": "35% better opening duel win rate",
        "priority": 1,
    },
    {
        "id": "timing_late_rotate_002",
        "classes": [2],  # too_late
        "condition": lambda _ctx: True,
        "title": "Late rotation",
        "description": (
            "Your rotation was too slow — the opportunity passed. Read the "
            "mini-map and teammate callouts to rotate earlier. Pay attention to "
            "sound cues and bomb information."
        ),
        "expected_impact": "Faster rotations leading to better retakes",
        "priority": 2,
    },
    {
        "id": "timing_unnecessary_peek_003",
        "classes": [3],  # unnecessary
        "condition": lambda _ctx: True,
        "title": "Unnecessary peek — already had control",
        "description": (
            "You peeked without necessity while your team had the advantage. "
            "When controlling an area, hold angles instead of pushing. "
            "Let opponents come to you when time is on your side."
        ),
        "expected_impact": "Fewer unnecessary deaths in won positions",
        "priority": 2,
    },
]


# ---------- RECOMMENDATION GENERATOR ----------


def generate_positioning_recommendation(
    severity: str,
    context: dict,
) -> Recommendation:
    """Generate a recommendation for a positioning error.

    Args:
        severity: "critical" or "minor"
        context: Dict with keys like angles_exposed, distance_to_cover,
                 had_teammate_nearby, position_area, etc.
    """
    for template in POSITIONING_TEMPLATES:
        if severity not in template["severity"]:
            continue
        if template["condition"](context):
            try:
                desc = template["description"].format(**context)
            except KeyError:
                desc = template["description"].format_map(
                    {
                        **context,
                        **{
                            k: "unknown"
                            for k in ["angles_exposed", "distance_to_cover", "position_area"]
                        },
                    }
                )
            return Recommendation(
                title=template["title"],
                description=desc,
                priority=template["priority"],
                template_id=template["id"],
                expected_impact=template["expected_impact"],
            )

    # Fallback
    return Recommendation(
        title="Review positioning",
        description="Review your position in this round for potential improvements.",
        priority=3,
        template_id="pos_fallback",
        expected_impact="General improvement",
    )


def generate_utility_recommendation(
    predicted_class: int,
    grenade_type: str,
    context: dict,
) -> Recommendation:
    """Generate a recommendation for a utility error."""
    for template in UTILITY_TEMPLATES:
        if template["grenade_type"] is not None and template["grenade_type"] != grenade_type:
            continue
        if predicted_class not in template["classes"]:
            continue
        if template["condition"](context):
            try:
                desc = template["description"].format(**context)
            except KeyError:
                desc = template["description"]
            return Recommendation(
                title=template["title"],
                description=desc,
                priority=template["priority"],
                template_id=template["id"],
                expected_impact=template["expected_impact"],
            )

    return Recommendation(
        title="Review utility usage",
        description="Review your grenade usage for this round.",
        priority=3,
        template_id="util_fallback",
        expected_impact="General improvement",
    )


def generate_timing_recommendation(
    predicted_class: int,
    context: dict,
) -> Recommendation:
    """Generate a recommendation for a timing error."""
    for template in TIMING_TEMPLATES:
        if predicted_class not in template["classes"]:
            continue
        if template["condition"](context):
            return Recommendation(
                title=template["title"],
                description=template["description"],
                priority=template["priority"],
                template_id=template["id"],
                expected_impact=template["expected_impact"],
            )

    return Recommendation(
        title="Review timing",
        description="Review the timing of your actions in this round.",
        priority=3,
        template_id="timing_fallback",
        expected_impact="General improvement",
    )
