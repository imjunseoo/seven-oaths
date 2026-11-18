"""Build chunckxel.aseprite-extension (a zip of package.json + the Lua sources).

  python ArtSource/tools/chunckxel/build_extension.py

Install: Aseprite > Edit > Preferences > Extensions > Add Extension > pick the built file."""
import os
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
FILES = ["package.json", "chunckxel.lua", "chunckxel_core.lua", "chunckxel_fake.lua"]
OUT = os.path.join(HERE, "chunckxel.aseprite-extension")

if __name__ == "__main__":
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for f in FILES:
            z.write(os.path.join(HERE, f), f)
    print("built", OUT, os.path.getsize(OUT), "bytes:", ", ".join(FILES))
