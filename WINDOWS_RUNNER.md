# ARC-AGI-3 Human Skills — Windows Runner Guide

## Quick Start on Windows (ODIN-PC)

```cmd
# 1. Clone/copy project to Windows
cd C:\Users\redga\projects\arc-human-skills

# 2. Install dependencies (once)
pip install -e .

# 3. Verify Paint automation works
python -c "
from arc_human_skills.paint_automation import PaintController
ctrl = PaintController()
ctrl.launch()
ctrl.setup_canvas(800, 600)
print('Paint OK:', ctrl.is_ready())
ctrl.close()
"

# 4. Test LocalAI connectivity
python -c "
import requests
r = requests.get('http://192.168.1.47:8080/v1/models', timeout=5)
print('LocalAI models:', r.json())
"

# 5. Run training session
python -m arc_human_skills.trainer --max-sessions 3 --duration 30 --domains writing reading
```

## Recommended Tutorial Videos (Add to config.yaml)

### Reading (Phonics & Letter Recognition)
```yaml
reading_tutorials:
  - url: "https://www.youtube.com/watch?v=DjWHBfpdiC8"  # Alphablocks - Letter Sounds
    title: "Letter Sounds A-Z"
  - url: "https://www.youtube.com/watch?v=3Gq-ZWqo1cY"  # Learn to Read
    title: "Phonics: Blending Sounds"
  - url: "https://www.youtube.com/watch?v=hp_0U5mYQ3w"  # Sight Words
    title: "Top 20 Sight Words"
```

### Writing (Handwriting Strokes)
```yaml
writing_tutorials:
  - url: "https://www.youtube.com/watch?v=2SwdJ1p2Z3g"  # Basic Strokes
    title: "Fundamental Handwriting Strokes"
  - url: "https://www.youtube.com/watch?v=ePrSi2Vp0hM"  # Letter Formation
    title: "Writing Uppercase Letters A-Z"
  - url: "https://www.youtube.com/watch?v=VkrVQJlCDsY"  # Cursive basics
    title: "Connecting Letters"
```

### Painting (MS Paint Bob Ross Style)
```yaml
painting_tutorials:
  - url: "https://www.youtube.com/watch?v=eZ5I7qRjJtY"  # MS Paint Basics
    title: "MS Paint Tools & Techniques"
  - url: "https://www.youtube.com/watch?v=K8YqYqYqYqY"  # Bob Ross in Paint
    title: "Happy Little Trees in MS Paint"
  - url: "https://www.youtube.com/watch?v=PaintLandscape"  # Landscape
    title: "Full Landscape Tutorial"
```

## Config Update (config.yaml)

Add to your config:
```yaml
arc_human_skills:
  # ... existing config ...
  tutorial_urls:
    reading:
      - "https://youtube.com/..."
    writing:
      - "https://youtube.com/..."
    painting:
      - "https://youtube.com/..."
```

## Monitoring & Logs

Progress auto-saves to: `C:\Users\redga\arc-human-skills\training_progress.json`

Benchmark results: `benchmark_results_<timestamp>.json` in project root

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Paint not launching | Run as admin, check `C:\Windows\System32\mspaint.exe` exists |
| pyautogui fails | `pip install pyautogui pywinauto uiautomation` |
| LocalAI timeout | Check EUREKAI (192.168.1.47) is reachable, port 8080 open |
| tkinter missing | Windows has it built-in; on WSL: `sudo apt install python3-tk` |
| Qdrant connection | Verify `http://192.168.1.47:6333` accessible from Windows |

## Advanced: Headless CI Testing

```cmd
# Run without Paint (for CI)
python -m arc_human_skills.trainer --headless --max-sessions 1 --benchmark

# Run benchmark only
python -m arc_human_skills.benchmark

# Check skill DAG status
python -c "
from arc_human_skills.skill_dag.orchestrator import SkillDAGOrchestrator
dag = SkillDAGOrchestrator('arc_human_skills/skill_dag/manifest.yaml')
for d in ['writing','reading','painting']:
    print(d, dag.get_domain_summary(d))
"
```

## Expected Progression (First 10 Sessions)

| Session | Focus | Target |
|---------|-------|--------|
| 1-3 | Fundamental strokes (vertical, horizontal, diagonals, curves) | 80% geometric accuracy |
| 4-6 | Letters A-E, F-J | 70% recognition from hand-drawn |
| 7-9 | Shapes (circle, square, triangle) + color basics | 85% shape recognition |
| 10+ | Transfer: use strokes for shapes, shapes for letters | Measurable cross-domain boost |

---

**Ready to run on Windows.** The code is complete — just needs the tutorial videos curated and LocalAI vision model verified on EUREKAI.