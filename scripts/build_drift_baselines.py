"""Derive drift baselines from the parsed demos in d:/aics2-data/parse-cache/.

Runs the same feature extraction as the training scripts, then writes the
per-feature mean/std/p05/p95 to packages/ml-models/baselines/*.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "backend"))

from demo_cache import parse_demo_cached  # noqa: E402


DEMOS_DIR = Path("d:/aics2-data/demos/pro")
BASELINE_DIR = ROOT / "packages" / "ml-models" / "baselines"
BASELINE_DIR.mkdir(parents=True, exist_ok=True)

MAPS = ["de_mirage", "de_dust2", "de_inferno", "de_nuke", "de_overpass", "de_ancient", "de_anubis"]
MAP_TO_IDX = {m: i for i, m in enumerate(MAPS)}

WIN_PROB_FEATS = [
    "alive_t", "alive_ct", "victim_is_t", "round_num",
    "score_diff", "score_t", "score_ct", "is_overtime",
    "equip_diff", "bomb_planted", "time_remaining",
    "avg_hp_t", "avg_hp_ct",
] + [f"map_{m}" for m in MAPS]

PLAYER_RATING_FEATS = [
    "kpr", "dpr", "apr", "kd", "hs_pct", "kast", "survival",
    "adr", "impact",
]


def _alive_at_tick(parsed, round_num: int, tick: int) -> dict:
    alive_t = alive_ct = 0
    total_equip_t = total_equip_ct = 0
    hp_t: list[int] = []
    hp_ct: list[int] = []
    seen = set()
    for t in parsed.raw_ticks:
        if t.get("round_num") != round_num or t.get("tick", 0) > tick:
            continue
        sid = t.get("steamid")
        if sid in seen:
            continue
        seen.add(sid)
        side = t.get("side")
        hp = t.get("health") or 0
        eq = t.get("current_equip_value") or 0
        if hp <= 0:
            continue
        if side == "t":
            alive_t += 1
            total_equip_t += eq
            hp_t.append(hp)
        elif side == "ct":
            alive_ct += 1
            total_equip_ct += eq
            hp_ct.append(hp)
    return {
        "alive_t": alive_t, "alive_ct": alive_ct,
        "total_equip_t": total_equip_t, "total_equip_ct": total_equip_ct,
        "avg_hp_t": (sum(hp_t) / len(hp_t)) if hp_t else 0,
        "avg_hp_ct": (sum(hp_ct) / len(hp_ct)) if hp_ct else 0,
    }


def build_win_prob_features(limit: int = 30) -> np.ndarray:
    dem_files = sorted(DEMOS_DIR.glob("*.dem"))[:limit]
    out = []
    for i, path in enumerate(dem_files):
        try:
            parsed = parse_demo_cached(path)
        except Exception as e:  # noqa: BLE001
            print(f"  [{i+1}] skip: {e}")
            continue
        if not parsed.rounds or not parsed.raw_kills:
            continue
        round_winners = {r.round_number: r.winner_side for r in parsed.rounds if r.winner_side}
        round_bomb = {r.round_number: bool(r.bomb_planted) for r in parsed.rounds}
        starts = {r.round_number: r.start_tick for r in parsed.rounds if r.start_tick}
        ends = {r.round_number: r.end_tick for r in parsed.rounds if r.end_tick}
        total_rounds = len(parsed.rounds)
        map_idx = MAP_TO_IDX.get(parsed.map_name or "", -1)

        for kill in parsed.raw_kills:
            rn = kill.get("round_num", 0)
            if rn not in round_winners:
                continue
            tick = kill.get("tick", 0)
            victim = kill.get("victim_side", "")
            s = _alive_at_tick(parsed, rn, tick - 1)
            t_score = sum(1 for r in parsed.rounds if r.round_number < rn and r.winner_side == "t")
            ct_score = sum(1 for r in parsed.rounds if r.round_number < rn and r.winner_side == "ct")
            st, et = starts.get(rn, tick - 4000), ends.get(rn, tick + 4000)
            time_rem = 1 - min((tick - st) / max(et - st, 1), 1.0)
            equip_diff = max(-1.0, min(1.0, (s["total_equip_t"] - s["total_equip_ct"]) / 25000.0))
            map_oh = [0.0] * len(MAPS)
            if map_idx >= 0:
                map_oh[map_idx] = 1.0
            out.append([
                s["alive_t"] / 5.0, s["alive_ct"] / 5.0,
                1.0 if victim == "t" else 0.0, rn / 30.0,
                (t_score - ct_score) / max(total_rounds, 1),
                t_score / 16.0, ct_score / 16.0,
                1.0 if rn > 24 else 0.0, equip_diff,
                1.0 if round_bomb.get(rn) else 0.0,
                time_rem, s["avg_hp_t"] / 100.0, s["avg_hp_ct"] / 100.0,
            ] + map_oh)
        print(f"  [{i+1}/{len(dem_files)}] cumulative snapshots: {len(out)}")
    return np.array(out, dtype=np.float32)


def build_player_rating_features(limit: int = 30) -> np.ndarray:
    """Derive per-player per-match stats.

    The cached pickle's PlayerData.kills/headshot_kills are zero due to an
    older awpy schema. Recompute them from raw_kills events.
    """
    dem_files = sorted(DEMOS_DIR.glob("*.dem"))[:limit]
    out = []
    for i, path in enumerate(dem_files):
        try:
            parsed = parse_demo_cached(path)
        except Exception:
            continue
        if not parsed.players:
            continue
        total_rounds = len(parsed.rounds) or 1

        kills_by: dict[str, int] = {}
        hs_by: dict[str, int] = {}
        for k in (parsed.raw_kills or []):
            sid = k.get("attacker_steamid")
            if sid is None:
                continue
            sid = str(sid)
            kills_by[sid] = kills_by.get(sid, 0) + 1
            if k.get("headshot"):
                hs_by[sid] = hs_by.get(sid, 0) + 1

        for p in parsed.players:
            pid = str(p.steam_id)
            kills = kills_by.get(pid, p.kills or 0)
            hs = hs_by.get(pid, p.headshot_kills or 0)
            deaths = p.deaths or 0
            kpr = kills / total_rounds
            dpr = deaths / total_rounds
            apr = (p.assists or 0) / total_rounds
            kd = kills / max(deaths, 1)
            hs_pct = (hs / kills) if kills else 0.0
            kast = (p.kast_rounds or 0) / total_rounds
            survival = (p.rounds_survived or 0) / total_rounds
            adr = (p.adr or 0) / 200.0
            impact = kpr + 0.5 * apr
            out.append([kpr, dpr, apr, kd, hs_pct, kast, survival, adr, impact])
        print(f"  [{i+1}/{len(dem_files)}] cumulative rows: {len(out)}")
    return np.array(out, dtype=np.float32)


def _baseline(X: np.ndarray, names: list[str]) -> dict:
    b = {}
    for i, n in enumerate(names):
        col = X[:, i]
        b[n] = {
            "mean": round(float(col.mean()), 4),
            "std": round(float(col.std()), 4),
            "p05": round(float(np.percentile(col, 5)), 4),
            "p95": round(float(np.percentile(col, 95)), 4),
        }
    return b


def main() -> None:
    print("Building player_rating baseline")
    X = build_player_rating_features(limit=25)
    if len(X):
        (BASELINE_DIR / "player_rating.json").write_text(json.dumps(_baseline(X, PLAYER_RATING_FEATS), indent=2))
        print(f"  -> player_rating.json ({len(X)} samples)")
    else:
        print("  no samples")


if __name__ == "__main__":
    main()
