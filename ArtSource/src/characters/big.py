"""Render chosen tag frames big (6x) with a dark bg for close inspection."""
import sys
from heroine import *
from lab import show
tag = sys.argv[1]
idx = [int(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else None
frames, durs = ANIMS[tag]()
items = [(f"{tag} {i}", f[8:64, 22:90]) for i, f in enumerate(frames) if idx is None or i in idx]
print(show(items, f"big_{tag}", s=6, bg=(30, 28, 42)))
