"""Exhaust the voxel corner topologies in the old and compact GPU scene traversals."""

import argparse
import hashlib
import itertools
import json
import os
import subprocess
import tempfile
from pathlib import Path

import numpy as np


def shader_function(path, name):
    text = path.read_text()
    start = text.index("bool lampCornerClosed(")
    end = text.index("\n}", start) + 2
    return text[start:end].replace("lampCornerClosed(", name + "(")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("previous", type=Path)
    parser.add_argument("compact", type=Path)
    parser.add_argument("runner", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    before = shader_function(args.previous, "oldClosed")
    after = shader_function(args.compact, "newClosed")
    shader = (
        """#version 430 core
layout(local_size_x=64) in;
layout(std430,binding=0) readonly buffer Questions { vec4 query[]; };
layout(std430,binding=1) writeonly buffer Answers { vec2 answer[]; };
int currentMask;
bool lampOpenCell(ivec3 cell,vec3 crossing) {
    ivec3 stepOffset=abs(cell-ivec3(10));
    int subset=stepOffset.x+2*stepOffset.y+4*stepOffset.z;
    return ((currentMask>>subset)&1)!=0;
}
"""
        + before
        + "\n"
        + after
        + """
void main() {
    int i=int(gl_GlobalInvocationID.x);
    if(i>=answer.length()) return;
    vec4 question=query[3*i];
    currentMask=int(question.w);
    ivec3 stepAcross=ivec3(question.xyz);
    answer[i]=vec2(oldClosed(ivec3(10),stepAcross,vec3(0)),
                   newClosed(ivec3(10),stepAcross,vec3(0)));
}
"""
    )
    questions, expected = [], []
    for step in itertools.product(range(-1, 2), repeat=3):
        axes = [1 << k for k in range(3) if step[k]]
        for mask in range(0, 128, 2):
            blocked = True
            for order in itertools.permutations(axes):
                intermediate = itertools.accumulate(order[:-1])
                if all(mask & (1 << cell) for cell in intermediate):
                    blocked = False
                    break
            questions.append([*step, mask] + [0] * 8)
            expected.append(blocked)
    doc = {
        "scope": "Open/closed intermediate cells abstract the material test; the production corner traversal runs on each GPU.",
        "cases": len(questions),
        "sourceSha256": [
            hashlib.sha256(s.encode()).hexdigest() for s in [before, after]
        ],
        "drivers": [],
    }
    with tempfile.TemporaryDirectory() as work:
        d = Path(work)
        (d / "test.csh").write_text(shader)
        np.zeros((1024, 512), dtype="f4").tofile(d / "field")
        np.asarray(questions, dtype="f4").tofile(d / "questions")
        for vendor in ["10_nvidia", "50_mesa"]:
            env = dict(
                os.environ,
                EGL_PLATFORM="surfaceless",
                __EGL_VENDOR_LIBRARY_FILENAMES=f"/usr/share/glvnd/egl_vendor.d/{vendor}.json",
            )
            run = subprocess.run(
                [
                    args.runner.resolve(),
                    d / "test.csh",
                    d / "field",
                    d / "questions",
                    d / "results",
                ],
                env=env,
                capture_output=True,
                check=True,
                text=True,
            )
            answer = np.fromfile(d / "results", dtype="f4").reshape(-1, 2)
            errors = np.count_nonzero(answer != np.asarray(expected)[:, None], axis=0)
            assert not errors.any(), (vendor, errors)
            doc["drivers"].append(
                {"renderer": run.stderr.strip(), "mismatches": errors.tolist()}
            )
    args.output.write_text(json.dumps(doc, indent=2) + "\n")
    print(doc)


if __name__ == "__main__":
    main()
