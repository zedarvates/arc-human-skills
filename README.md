# ARC-AGI-3 Human Skills

> **Learn to READ, WRITE, and PAINT like a human — from absolute zero — using Windows Paint, video tutorials, and iterative self-evaluation.**

An implementation of the ARC-AGI-3 challenge focused on **human-like skill acquisition** rather than puzzle-solving. The agent watches tutorials, practices in Microsoft Paint, evaluates its own output via vision models, and transfers skills across reading, writing, and painting domains.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SKILL DAG ORCHESTRATOR                    │
│  (Topological scheduling, prerequisites, mastery tracking)  │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
   ┌─────────┐    ┌─────────┐    ┌─────────┐
   │ READING │    │ WRITING │    │PAINTING │
   └────┬────┘    └────┬────┘    └────┬────┘
        │              │              │
        └──────────────┼──────────────┘
                       ▼
            ┌─────────────────────┐
            │  CROSS-DOMAIN       │
            │  TRANSFER SKILLS    │
            │  (stroke→shape,     │
            │   reading→writing)  │
            └─────────────────────┘
```

### Three Learning Tracks

| Track | Foundation | Progression | Evaluation |
|-------|------------|-------------|------------|
| **Reading** | Letter recognition (26 letters × 10 fonts) | Sight words → sentences | LocalAI vision (qwen3.6-27b) |
| **Writing** | 10 fundamental strokes (Zaner-Bloser) | 26 letters → words | Stroke geometry + recognition |
| **Painting** | 6 geometric shapes | Bob Ross landscapes (sky, trees, mountains, water) | Shape recognition + human coherence |

### Cross-Domain Transfer
- **Strokes → Shapes**: Vertical/horizontal/diagonal strokes compose squares, triangles
- **Shapes → Letters**: Circles → O, Q; Triangles → A, V; Rectangles → H, E
- **Reading → Writing**: Letter recognition improves formation consistency

## Quick Start

### Windows (ODIN-PC) — Full Training
```cmd
cd C:\Users\redga\projects\arc-human-skills
run_windows.bat
# Or for PowerShell:
.\run_windows.ps1
```

### Linux/WSL — Headless Testing
```bash
cd ~/projects/arc-human-skills
python -m arc_human_skills.trainer --headless --max-sessions 1 --benchmark
```

### Run Benchmark Only
```bash
python -m arc_human_skills.benchmark
```

## Requirements

- **Windows 10/11** (for Paint automation) — or `--headless` mode on Linux
- **Python 3.11+**
- **LocalAI on EUREKAI (192.168.1.47:8080)** with:
  - `whisper-1` (STT)
  - `qwen3.6-27b` (vision)
  - `tts-1` (optional, for TTS)
- **Qdrant on EUREKAI (192.168.1.47:6333)** for embeddings
- **YouTube tutorials** (curated in `config.yaml`)

## Configuration

Edit `config.yaml`:
```yaml
arc_human_skills:
  storage_root: "C:/Users/redga/arc-human-skills"
  paint:
    exe_path: "C:/Windows/System32/mspaint.exe"
    canvas_size: [800, 600]
  video:
    localai_url: "http://192.168.1.47:8080"
    whisper_model: "whisper-1"
  evaluation:
    vision_model: "qwen3.6-27b"
    localai_url: "http://192.168.1.47:8080"
  qdrant:
    url: "http://192.168.1.47:6333"
  learning_tracks:
    reading:   {enabled: true, priority: 1, practice_per_session: 10}
    writing:   {enabled: true, priority: 2, practice_per_session: 15}
    painting:  {enabled: true, priority: 3, practice_per_session: 5}
```

## Project Structure

```
arc-human-skills/
├── config.yaml                    # Main configuration
├── pyproject.toml                 # Dependencies
├── WINDOWS_RUNNER.md              # Windows deployment guide
├── run_windows.bat / .ps1         # Windows launchers
├── arc_human_skills/
│   ├── config.py                  # Typed config loader
│   ├── paint_automation.py        # Windows Paint control (pywinauto)
│   ├── video_tutorial.py          # YouTube → Whisper → keyframes
│   ├── benchmark.py               # ARC-style evaluation runner
│   ├── trainer.py                 # Main training loop (CLI)
│   ├── reading/
│   │   ├── training_data.py       # Letter gen + Qdrant embeddings
│   │   └── recognizer.py          # Vision recognition + practice
│   ├── writing/
│   │   └── stroke_patterns.py     # 10 strokes + 26 letter compositions
│   ├── painting/
│   │   └── shapes.py              # 6 shapes + Bob Ross landscape
│   ├── skill_dag/
│   │   ├── manifest.yaml          # 50+ atomic skills (YAML)
│   │   └── orchestrator.py        # Topological scheduler
│   └── eval_tasks/
│       └── arc_tasks.json         # 15 benchmark tasks
└── tests/                         # 34 passing (10 skipped on Linux)
```

## Training Flow

1. **Watch Tutorial** → Download YouTube, extract audio, transcribe (Whisper), detect key frames
2. **Practice in Paint** → Automated stroke/letter/shape drawing via pywinauto
3. **Self-Evaluate** → Capture canvas, send to LocalAI vision model (qwen3.6-27b)
4. **Update SkillDAG** → Record attempts, track mastery, unlock dependent skills
5. **Transfer** → Apply learned strokes to shapes, shapes to letters, reading to writing
6. **Benchmark** → Run ARC-style tasks every N sessions

## CLI Reference

```bash
# Full training (infinite 30-min sessions)
python -m arc_human_skills.trainer --max-sessions 0 --duration 30

# Limited sessions, specific domains
python -m arc_human_skills.trainer --max-sessions 10 --duration 20 --domains writing reading

# Headless (no Paint) for CI/testing
python -m arc_human_skills.trainer --headless --max-sessions 1

# Benchmark only
python -m arc_human_skills.benchmark

# With custom config
python -m arc_human_skills.trainer --config custom.yaml
```

## Monitoring

Progress auto-saves to: `C:/Users/redga/arc-human-skills/training_progress.json`

```json
{
  "session_count": 15,
  "total_attempts": 1247,
  "total_successes": 983,
  "skill_progress": {
    "stroke_vertical_down": {"attempts": 45, "successes": 38, "mastered": true, "avg_score": 0.84},
    "letter_A": {"attempts": 30, "successes": 22, "mastered": false, "avg_score": 0.73},
    "shape_circle": {"attempts": 25, "successes": 21, "mastered": true, "avg_score": 0.88}
  }
}
```

Benchmark results: `benchmark_results_<timestamp>.json`

## Tutorial Curation

Add YouTube URLs to `config.yaml`:
```yaml
tutorial_urls:
  reading:
    - "https://youtube.com/watch?v=..."  # Phonics, letter sounds
  writing:
    - "https://youtube.com/watch?v=..."  # Basic strokes, letter formation
  painting:
    - "https://youtube.com/watch?v=..."  # MS Paint basics, Bob Ross style
```

## ARC-AGI-3 Alignment

This project addresses the **ARC-AGI-3 "Human-Like Learning" track** by:
- **No pre-trained priors** — starts from zero, learns strokes → letters → shapes
- **Embodied practice** — physical (simulated) drawing in Paint, not just pattern matching
- **Self-supervision** — vision model evaluates own output, no human labels needed
- **Compositional skills** — SkillDAG enforces prerequisite structure
- **Cross-domain transfer** — explicit transfer skills with measurable efficiency
- **Continuous learning** — no fixed dataset, incremental skill acquisition

## License

MIT — See `LICENSE` for details.

---

**Built for ARC-AGI-3** — Human-like skill acquisition from zero.

---

[![Donate](https://img.shields.io/badge/☕%20Soutenir-BTC%20%7C%20ETH-orange)](DONATE.md)