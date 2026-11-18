from heroine_model import *
from lab import show
items = []
for g, ol in (("mid", "b"), ("light", "c"), ("dark", "b")):
    STYLE["greave"] = g; STYLE["cape_ol"] = ol
    img, j = compose(Pose())
    items.append((f"{g}/{ol}", img[12:64, 26:78]))
print(show(items, "idle_try2", s=6, bg=(30, 28, 42)))
