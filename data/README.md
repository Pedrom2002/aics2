# ML Training Data & Models

## Directory Structure

```
data/
├── demos/              ← Place .dem files here
│   ├── pro/            ← Pro match demos (from HLTV/FACEIT)
│   └── user/           ← User-uploaded demos
├── positioning/        ← Generated .npz training windows (auto-created)
├── utility/            ← Generated grenade feature vectors (auto-created)
└── checkpoints/        ← Trained model weights (auto-created)
    ├── positioning/    ← Mamba model checkpoints
    ├── utility/        ← LightGBM model files
    ├── timing/         ← Timing Mamba checkpoints
    └── strategy/       ← GraphSAGE checkpoints
```

## Quick Start

### 1. Download pro demos (automatic)
```bash
# Download ~2000 pro demos from HLTV (takes 3-4 hours, rate limited)
cd packages/pro-demo-ingester
pip install -e .
python -m src.download_demos --pages 40 --output ../../data/demos/pro

# Or via the pipeline runner:
cd packages/ml-models
python -m src.training.run_pipeline scrape --pages 40

# Resume an interrupted download (auto-skips already downloaded)
python -m src.download_demos --pages 40 --output ../../data/demos/pro --resume
```

**Note:** Requires `unrar` on PATH for .rar extraction:
- Windows: download from https://www.rarlab.com/rar_add.htm
- Linux: `apt install unrar`
- macOS: `brew install unrar`

### 2. Run the full pipeline (one command)
```bash
cd packages/ml-models
python -m src.training.run_pipeline all --demos-dir ../../data/demos --output-dir ../../data
```

This will:
1. Parse all .dem files and extract ML features → `data/positioning/*.npz`
2. Train positioning Mamba model → `data/checkpoints/positioning/best_model.pt`
3. Train utility LightGBM model → `data/checkpoints/utility/model.lgb`
4. Evaluate models and print metrics report
5. Models auto-load into the inference pipeline on next demo processing

### 3. Individual steps
```bash
# Generate dataset only
python -m src.training.run_pipeline generate --demos-dir ../../data/demos

# Train positioning model only
python -m src.training.run_pipeline train-positioning --epochs 50

# Train utility model only
python -m src.training.run_pipeline train-utility

# Evaluate models
python -m src.training.run_pipeline evaluate

# Generate synthetic test data (no demos needed)
python -m src.training.run_pipeline synthetic --count 1000
```

## How many demos do I need?

| Maps in pool | Demos needed | Training windows | GPU time |
|-------------|-------------|-----------------|----------|
| 7 (active duty) | ~500 min | ~150k | ~2h |
| 7 | ~1000 (recommended) | ~300k | ~4h |
| 7 | ~2000+ (ideal) | ~600k+ | ~6h |

## Model auto-loading

When trained model weights exist at `data/checkpoints/*/`, the inference
pipeline automatically uses them instead of the heuristic baseline.
No code changes needed — just train and the models go live.
