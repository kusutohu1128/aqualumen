"""Validate native framebuffer sequences and prepare timestamp-faithful playback."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

from report import check_png


def audit(directory):
    manifest = json.loads((directory / 'run.json').read_text())
    if not (manifest['native_motion_capture_active'] and manifest['shader_active'] and
            not manifest['shader_fallback'] and 'NVIDIA' in manifest['gl_renderer']):
        raise ValueError('Native runtime identity or activation is unproven')
    sequences = []
    for scene in manifest['scenarios']:
        sequence = directory / ('native-motion-' + scene)
        with (sequence / 'frames.csv').open() as source:
            samples = list(csv.DictReader(source))
        if not 2 <= len(samples) <= 80:
            raise ValueError('Sequence has insufficient or excess frames')
        previous = -100_000_000
        frames = []
        for index, sample in enumerate(samples):
            elapsed = int(sample['elapsed_ns'])
            yaw, pitch = float(sample['yaw']), float(sample['pitch'])
            if (int(sample['frame']) != index or elapsed < 0 or elapsed - previous < 100_000_000 or
                    not math.isfinite(yaw) or not math.isfinite(pitch)):
                raise ValueError('Invalid sequence timing or camera metadata')
            path = sequence / f'frame-{index:03d}.png'
            check_png(path, manifest['resolution'])
            frames.append(dict(file=path.name, elapsed_ns=elapsed, yaw=yaw, pitch=pitch,
                               sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
            previous = elapsed
        if set(sequence.glob('frame-*.png')) != {sequence / frame['file'] for frame in frames}:
            raise ValueError('Unindexed or missing framebuffer images')
        if scene == 'underwater-up-moving':
            if frames[-1]['yaw'] - frames[0]['yaw'] < 30 or any(abs(frame['pitch'] + 65) > .05 for frame in frames):
                raise ValueError('Requested underwater camera motion is not demonstrated')
        concat = ['ffconcat version 1.0']
        for index, frame in enumerate(frames):
            concat.append("file '" + frame['file'] + "'")
            if index + 1 < len(frames):
                concat.append(f"duration {(frames[index+1]['elapsed_ns']-frame['elapsed_ns'])/1e9:.9f}")
        with (sequence / 'playback.ffconcat').open('x') as target:
            target.write('\n'.join(concat) + '\n')
        sequences.append(dict(scene=scene, frames=frames, duration_seconds=(frames[-1]['elapsed_ns']-frames[0]['elapsed_ns'])/1e9))
    result = dict(sequences=sequences, strict_png_count=sum(len(sequence['frames']) for sequence in sequences),
                  performance_benchmark=False, motion_visually_accepted=False, goal_complete=False)
    with (directory / 'native-motion-audit.json').open('x') as target:
        json.dump(result, target, indent=2)
    print(f"Verified {result['strict_png_count']} native PNGs; visual acceptance remains open")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    audit(parser.parse_args().directory)
