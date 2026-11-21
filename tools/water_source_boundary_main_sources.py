"""Prepare affected ten-case MAIN regression sources, CPU only.

Keep the qualified probability8 helper/caps/roles, only the SSR correction.
Actual execution/audit remains required before candidate Iris qualification.
"""
import argparse
from pathlib import Path
from water_source_boundary_fix_source import clip_segment

ROOT=Path(__file__).resolve().parents[1]


def build(out):
    original=ROOT/'reports/2026-10-06-water-fast-inverse/main-probability-8-v1'
    out=Path(out);out.mkdir(exist_ok=False)
    for path in sorted(original.iterdir()):
        if not path.is_file():continue
        text=path.read_text()
        if path.suffix=='.fsh':text=clip_segment(text)
        with (out/path.name).open('x') as f:f.write(text)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('out');args=parser.parse_args();build(args.out)
