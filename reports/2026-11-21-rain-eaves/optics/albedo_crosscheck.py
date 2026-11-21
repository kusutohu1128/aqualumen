#!/usr/bin/env python3
"""Third, independent statement of the directional albedo of the rain-film BRDF (pure Python, no shader code, no
half-vector sampler): brute-force solid-angle grid of  (1/pi) * Int pi*f_r cos(theta_l) dOmega  with
GGX (alpha = perceptual^2, a2 = alpha^2) + height-correlated Smith + Schlick(F0=0.0204 on v.h).
Compares to the GPU metrics `albedo_thv<deg>_r<r>_s<s2>` of a results JSON written by the native probe.
Usage: python3 -I albedo_crosscheck.py RESULTS.json OUT.txt   (OUT must not exist)"""
import json, math, sys
from pathlib import Path

F0 = 0.0204

def albedo(thv_deg, r, s2, nth, nph):
    a2 = min(max(r ** 4 + s2, 0.00012), 1.0)
    thv = math.radians(thv_deg)
    v = (math.sin(thv), 0.0, math.cos(thv)); nv = v[2]
    total = 0.0
    for i in range(nth):
        t = (i + 0.5) / nth * math.pi / 2
        st, ct = math.sin(t), math.cos(t)
        row = 0.0
        for j in range(nph):
            p = (j + 0.5) / nph * 2 * math.pi
            l = (st * math.cos(p), st * math.sin(p), ct)
            hx, hy, hz = l[0] + v[0], l[1] + v[1], l[2] + v[2]
            n = math.sqrt(hx * hx + hy * hy + hz * hz)
            nh = hz / n; vh = (v[0] * hx + v[2] * hz) / n
            d = nh * nh * (a2 - 1) + 1
            D = a2 / (math.pi * d * d)
            vis = 0.5 / (ct * math.sqrt(a2 + (1 - a2) * nv * nv) + nv * math.sqrt(a2 + (1 - a2) * ct * ct))
            F = F0 + (1 - F0) * (1 - max(0.0, min(1.0, vh))) ** 5
            row += D * vis * F * ct * st                      # (pi*f_r*cos*sin)/pi
        total += row
    return total * (math.pi / 2 / nth) * (2 * math.pi / nph) * math.pi / math.pi

if __name__ == "__main__":
    results, out = json.loads(Path(sys.argv[1]).read_text()), Path(sys.argv[2])
    if out.exists(): sys.exit("refusing to overwrite " + str(out))
    lines, worst = [], 0.0
    for thv, r, s2, key in [(0, 0.3, 0.0, "albedo_thv0_r0.3_s0"), (0, 0.6, 0.0, "albedo_thv0_r0.6_s0"), (0, 1.0, 0.0, "albedo_thv0_r1_s0"),
                            (45, 0.3, 0.0, "albedo_thv45_r0.3_s0"), (45, 0.6, 0.0, "albedo_thv45_r0.6_s0"),
                            (65, 0.3, 0.01, "albedo_thv65_r0.3_s0.01"), (65, 0.6, 0.0, "albedo_thv65_r0.6_s0"),
                            (80, 0.6, 0.0, "albedo_thv80_r0.6_s0"), (0, 0.15, 0.0, "albedo_thv0_r0.15_s0"), (80, 0.3, 0.01, "albedo_thv80_r0.3_s0.01")]:
        narrow = r <= 0.15 or s2 == 0.0 and r <= 0.3
        ref = albedo(thv, r, s2, 2400 if narrow else 1000, 180)
        gpu = results["metrics"][key]
        rel = abs(gpu - ref) / max(ref, 1e-6); worst = max(worst, rel)
        lines.append(f"{key}: GPU {gpu:.6f}  pure-python grid {ref:.6f}  rel {rel:.4%}")
    lines.append(f"worst relative difference {worst:.4%} (grid resolution limited; 3% gate)")
    lines.append("RESULT " + ("PASS" if worst < 0.03 else "FAIL"))
    out.write_text("\n".join(lines) + "\n"); print("\n".join(lines))
    sys.exit(0 if worst < 0.03 else 1)
