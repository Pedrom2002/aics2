"""
One-command ML pipeline runner.

Usage:
    # Full pipeline (generate dataset + train all models + evaluate)
    python -m src.training.run_pipeline all --demos-dir ../../data/demos --output-dir ../../data

    # Individual steps
    python -m src.training.run_pipeline generate --demos-dir ../../data/demos
    python -m src.training.run_pipeline train-positioning --epochs 50
    python -m src.training.run_pipeline train-utility
    python -m src.training.run_pipeline evaluate
    python -m src.training.run_pipeline synthetic --count 2000

    # Scrape demos from HLTV (requires network access)
    python -m src.training.run_pipeline scrape --pages 40 --output ../../data/demos/pro
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Default paths relative to this file
DEFAULT_BASE = Path(__file__).parent.parent.parent.parent.parent / "data"


def cmd_generate(args):
    """Generate training dataset from .dem files."""
    from src.training.generate_dataset import generate_dataset

    demos_dir = args.demos_dir or DEFAULT_BASE / "demos"
    output_pos = args.output_dir / "positioning" if args.output_dir else DEFAULT_BASE / "positioning"
    # Note: utility data generation requires grenade events from tick data
    # which needs deeper awpy integration. For now, use synthetic or manual labeling.

    summary = generate_dataset(demos_dir, output_pos)
    print(f"\nDataset generation summary: {json.dumps(summary, indent=2)}")
    return summary


def cmd_train_positioning(args):
    """Train the positioning Mamba model."""
    from src.training.train_positioning import train

    data_dir = args.output_dir / "positioning" if args.output_dir else DEFAULT_BASE / "positioning"
    ckpt_dir = args.output_dir / "checkpoints" / "positioning" if args.output_dir else DEFAULT_BASE / "checkpoints" / "positioning"

    metrics = train(
        data_dir=data_dir,
        output_dir=ckpt_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        use_mlflow=not args.no_mlflow,
    )
    print(f"\nPositioning training complete: {json.dumps(metrics, indent=2)}")
    return metrics


def cmd_train_utility(args):
    """Train the utility LightGBM model."""
    from src.training.train_utility import train

    data_dir = args.output_dir / "utility" if args.output_dir else DEFAULT_BASE / "utility"
    ckpt_dir = args.output_dir / "checkpoints" / "utility" if args.output_dir else DEFAULT_BASE / "checkpoints" / "utility"

    metrics = train(data_dir=data_dir, output_dir=ckpt_dir, use_mlflow=not args.no_mlflow)
    print(f"\nUtility training complete: {json.dumps(metrics, indent=2)}")
    return metrics


def cmd_evaluate(args):
    """Evaluate trained models and print metrics report."""
    import torch

    base = args.output_dir or DEFAULT_BASE
    report = {"models": {}}

    # Check positioning model
    pos_path = base / "checkpoints" / "positioning" / "best_model.pt"
    pos_metrics_path = base / "checkpoints" / "positioning" / "best_metrics.json"
    if pos_path.exists():
        report["models"]["positioning"] = {
            "status": "trained",
            "path": str(pos_path),
            "size_mb": round(pos_path.stat().st_size / 1024 / 1024, 2),
        }
        if pos_metrics_path.exists():
            with open(pos_metrics_path) as f:
                report["models"]["positioning"]["metrics"] = json.load(f)
    else:
        report["models"]["positioning"] = {"status": "not_trained"}

    # Check utility model
    util_path = base / "checkpoints" / "utility" / "model.lgb"
    util_metrics_path = base / "checkpoints" / "utility" / "metrics.json"
    if util_path.exists():
        report["models"]["utility"] = {
            "status": "trained",
            "path": str(util_path),
            "size_mb": round(util_path.stat().st_size / 1024 / 1024, 2),
        }
        if util_metrics_path.exists():
            with open(util_metrics_path) as f:
                report["models"]["utility"]["metrics"] = json.load(f)
    else:
        report["models"]["utility"] = {"status": "not_trained"}

    # Count training data
    pos_data_dir = base / "positioning"
    util_data_dir = base / "utility"
    report["data"] = {
        "positioning_windows": len(list(pos_data_dir.glob("*.npz"))) if pos_data_dir.exists() else 0,
        "utility_vectors": len(list(util_data_dir.glob("*.npz"))) if util_data_dir.exists() else 0,
    }

    print("\n" + "=" * 60)
    print("ML MODEL EVALUATION REPORT")
    print("=" * 60)
    print(json.dumps(report, indent=2))
    print("=" * 60)

    # Quality gates
    all_good = True
    for name, info in report["models"].items():
        if info["status"] != "trained":
            print(f"\n  WARNING: {name} model not trained")
            all_good = False
            continue

        metrics = info.get("metrics", {})
        if name == "positioning":
            f1 = metrics.get("val_f1", 0)
            precision = metrics.get("val_precision", 0)
            if precision < 0.85:
                print(f"\n  WARNING: {name} precision {precision:.3f} < 0.85 target")
                all_good = False
            if f1 < 0.77:
                print(f"\n  WARNING: {name} F1 {f1:.3f} < 0.77 target")
                all_good = False

    if all_good:
        print("\n  All models meet quality targets.")
    print()

    return report


def cmd_synthetic(args):
    """Generate synthetic data for pipeline testing."""
    from src.training.synthetic_data import generate_synthetic_positioning, generate_synthetic_utility

    base = args.output_dir or DEFAULT_BASE
    count = args.count

    pos_count = generate_synthetic_positioning(base / "positioning", count=count)
    util_count = generate_synthetic_utility(base / "utility", count=count // 2)

    print(f"\nGenerated {pos_count} positioning + {util_count} utility synthetic samples")


def cmd_scrape(args):
    """Scrape and download demos from HLTV (full automatic)."""
    import asyncio

    # Add pro-demo-ingester to path
    ingester_path = Path(__file__).parent.parent.parent.parent / "pro-demo-ingester"
    if str(ingester_path) not in sys.path:
        sys.path.insert(0, str(ingester_path))

    from src.download_demos import HLTVDemoDownloader

    output = Path(args.output) if args.output else DEFAULT_BASE / "demos" / "pro"

    async def _run():
        downloader = HLTVDemoDownloader(output_dir=output, resume=True)
        await downloader.run(pages=args.pages)

    asyncio.run(_run())


def cmd_all(args):
    """Run the full pipeline: generate → train → evaluate."""
    print("=" * 60)
    print("FULL ML PIPELINE")
    print("=" * 60)

    # Check for demos
    demos_dir = args.demos_dir or DEFAULT_BASE / "demos"
    dem_files = list(demos_dir.glob("**/*.dem")) if demos_dir.exists() else []

    if dem_files:
        print(f"\n[1/4] Generating dataset from {len(dem_files)} demos...")
        cmd_generate(args)
    else:
        print(f"\n[1/4] No .dem files in {demos_dir}, generating synthetic data...")
        args.count = args.count or 2000
        cmd_synthetic(args)

    print("\n[2/4] Training positioning model...")
    cmd_train_positioning(args)

    print("\n[3/4] Training utility model...")
    cmd_train_utility(args)

    print("\n[4/4] Evaluating models...")
    cmd_evaluate(args)

    print("\nPipeline complete! Models will auto-load on next demo processing.")


def main():
    parser = argparse.ArgumentParser(
        description="ML Pipeline Runner — one command to train everything",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full pipeline with real demos
  python -m src.training.run_pipeline all --demos-dir ../../data/demos

  # Full pipeline with synthetic data (for testing)
  python -m src.training.run_pipeline all --count 2000

  # Download 2000 pro demos from HLTV (automatic)
  python -m src.training.run_pipeline scrape --pages 40

  # Train only positioning model
  python -m src.training.run_pipeline train-positioning --epochs 100
        """,
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # all
    p_all = sub.add_parser("all", help="Full pipeline: generate → train → evaluate")
    p_all.add_argument("--demos-dir", type=Path)
    p_all.add_argument("--output-dir", type=Path)
    p_all.add_argument("--epochs", type=int, default=50)
    p_all.add_argument("--batch-size", type=int, default=256)
    p_all.add_argument("--lr", type=float, default=1e-3)
    p_all.add_argument("--count", type=int, default=2000)
    p_all.add_argument("--no-mlflow", action="store_true")

    # generate
    p_gen = sub.add_parser("generate", help="Generate dataset from .dem files")
    p_gen.add_argument("--demos-dir", type=Path)
    p_gen.add_argument("--output-dir", type=Path)

    # train-positioning
    p_pos = sub.add_parser("train-positioning", help="Train positioning Mamba model")
    p_pos.add_argument("--output-dir", type=Path)
    p_pos.add_argument("--epochs", type=int, default=50)
    p_pos.add_argument("--batch-size", type=int, default=256)
    p_pos.add_argument("--lr", type=float, default=1e-3)
    p_pos.add_argument("--no-mlflow", action="store_true")

    # train-utility
    p_util = sub.add_parser("train-utility", help="Train utility LightGBM model")
    p_util.add_argument("--output-dir", type=Path)
    p_util.add_argument("--no-mlflow", action="store_true")

    # evaluate
    p_eval = sub.add_parser("evaluate", help="Evaluate trained models")
    p_eval.add_argument("--output-dir", type=Path)

    # synthetic
    p_synth = sub.add_parser("synthetic", help="Generate synthetic test data")
    p_synth.add_argument("--output-dir", type=Path)
    p_synth.add_argument("--count", type=int, default=2000)

    # scrape (download demos)
    p_scrape = sub.add_parser("scrape", help="Download pro demos from HLTV (automatic)")
    p_scrape.add_argument("--pages", type=int, default=40, help="Pages to scrape (50 matches/page, 40=~2000)")
    p_scrape.add_argument("--output", type=str, help="Output dir for .dem files")

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    commands = {
        "all": cmd_all,
        "generate": cmd_generate,
        "train-positioning": cmd_train_positioning,
        "train-utility": cmd_train_utility,
        "evaluate": cmd_evaluate,
        "synthetic": cmd_synthetic,
        "scrape": cmd_scrape,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
