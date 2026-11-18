"""Re-render every sound, measure, rebuild the preview page.  python render_all.py"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
for script in ("make_sfx.py", "make_bgm.py", "make_amb.py", "import_bgm.py", "encode_ogg.py", "analyze.py", "build_preview.py"):
    print(f"=== {script}")
    subprocess.run([sys.executable, str(HERE / script)], cwd=HERE, check=True)
