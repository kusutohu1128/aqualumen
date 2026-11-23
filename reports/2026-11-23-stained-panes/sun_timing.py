"""Measure consecutive Minecraft render intervals before/after the solar treatment."""
import argparse
from frame_times import analyze
from sun_room import HERE,capture,source_pack,PACKAGES

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("mode",choices=PACKAGES)
    mode=ap.parse_args().mode
    pack=source_pack(mode)
    label="sun-timing-"+mode
    try:
        capture(pack,label,550,"2560x1440",("open-early","red"))
    except SystemExit as exc:
        if exc.code:raise
    analyze(HERE/label,pack,False,min_frames=50)
