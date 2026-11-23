"""Render the same rainy, open-roof room from the previous ownership test."""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PREVIOUS = HERE.parent / "2026-11-23-visible-terrain"
sys.path.insert(0, str(PREVIOUS))
from wet_room import CACHE, COMPILER, STAGES, WetRoom, guarded
from visible_pack import SOURCE, SOURCE_SHA, PACK, STUDY_SHA


def render(pack, checksum, label):
    assert guarded.sha(pack) == checksum
    fixed = {"backend":"vgl", "size":"1600x900", "settle":"1", "period-ticks":"260",
             "shot-gap":"0.15", "stages":",".join(STAGES), "glcache":str(CACHE),
             "compiler-mod":str(COMPILER)}
    guarded.launch(pack, label, "off", fixed, HERE, WetRoom)


if __name__ == "__main__":
    arms = {"forward":(SOURCE,SOURCE_SHA), "stored":(PACK,STUDY_SHA)}
    name = sys.argv[1]
    render(*arms[name], name)
