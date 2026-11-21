"""Same retained dense MAIN, only the qualified SSR exit-segment correction."""
import argparse
from pathlib import Path
from water_source_boundary_fix_source import clip_segment

ROOT=Path(__file__).resolve().parents[1]


def build(out):
    original=ROOT/'reports/2026-10-06-water-conditioned-sampling/reflector-main-01'
    out=Path(out);out.mkdir(exist_ok=False)
    for role in ('enabled','ledger','disabled'):
        with (out/f'{role}.fsh').open('x') as f:
            f.write(clip_segment((original/f'{role}.fsh').read_text()))
    for i in range(3):
        with (out/f'geometry-stage{i}.glsl').open('x') as f:
            f.write((original/f'geometry-stage{i}.glsl').read_text())


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('out');args=parser.parse_args();build(args.out)
