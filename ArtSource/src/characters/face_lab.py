from heroine_model import *
from lab import show
OLD = HEADS["n"]
NEW = dark_outer(parse("""
.G........G...
.FE......EF...
.DEC.hhhhDE...
..00hjjjj00...
.hjjkkkkjjjh..
hjjkkjjjjjjjh.
hijkjjjjjjjjjh
hijjjjjjjijjjh
hiijjjiijiijjh
hiijjiiviijvjh
hiiiv01vvv0vt.
hiiivDwvvvDvt.
.hiivEDvvvEvt.
.hiiuvvvvvvt..
.hiihtvvvvvt..
..hih.tttt....
..hh..........
"""))
print(show([("old", OLD), ("new", NEW)], "face_compare", s=14, bg=(30, 28, 42)))
