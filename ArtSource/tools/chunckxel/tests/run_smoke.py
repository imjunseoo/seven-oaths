"""Build the extension, unzip it to a temp dir and run tests/batch_smoke.lua in Aseprite batch mode.
Needs the parity sheets first: python ArtSource/compare/chickxel_test/parity.py --down
and python ArtSource/compare/chickxel_test/parity_c.py

  python ArtSource/tools/chunckxel/tests/run_smoke.py"""
import os, subprocess, sys, tempfile, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
EXT_DIR = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(EXT_DIR, "..", "..", ".."))
ASE = r"C:\Users\imjun\Tools\aseprite\src\build\bin\aseprite.exe"
PAR = os.path.join(ROOT, "ArtSource", "compare", "chickxel_test", "parity")

subprocess.run([sys.executable, os.path.join(EXT_DIR, "build_extension.py")], check=True)
with tempfile.TemporaryDirectory() as tmp:
    with zipfile.ZipFile(os.path.join(EXT_DIR, "chunckxel.aseprite-extension")) as z:
        print("zip contents:", z.namelist())
        z.extractall(tmp)
    cmd = [ASE, "-b",
           "--script-param", f"ext={tmp}",
           "--script-param", "sheet=" + os.path.join(ROOT, "ArtSource", "compare", "chickxel_test", "input", "A_swing_raw96_sheet.png"),
           "--script-param", "ref_clean=" + os.path.join(PAR, "lua_A_clean.png"),
           "--script-param", "ref_down=" + os.path.join(PAR, "lua_A_down2x.png"),
           "--script-param", "c_dir=" + os.path.join(ROOT, "ArtSource", "compare", "chickxel_test", "parity_c"),
           "--script-param", "c_in=" + os.path.join(ROOT, "ArtSource", "compare", "chunckxel_test", "c_test"),
           "--script", os.path.join(HERE, "batch_smoke.lua")]
    r = subprocess.run(cmd, capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip()
    print(out)
    sys.exit(0 if "SMOKE OK" in out else 1)
