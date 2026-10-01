"""Summarize the actual Minecraft frame captures, preserving the raw data."""
import json
from pathlib import Path

root=Path(__file__).resolve().parents[1]
report=root/'reports'/'2026-10-01'
rows=[]
for name in ['noon-water','coast-shadows','sunset-water','underwater','moving-view']:
    file=report/(name+'.json')
    if file.exists(): rows.append(json.loads(file.read_text()))
if len(rows)!=5:
    raise SystemExit('All five scenario files are required; partial runs are not a completed benchmark')
if any(row['resolution']!=[2560,1440] for row in rows):
    raise SystemExit('Resolution mismatch; do not report this run as 1440p')
text=['# RTX 3080 Ti / Minecraft 1.21.1 verification','',
 'RTX 3080 Ti 12GB, NVIDIA 580.173.02, Iris 1.8.8, Sodium 0.6.9, Fabric Loader 0.19.5, Java 21.0.7.',
 '2560×1440; 12 render chunks, 6 simulation chunks; BALANCED shader profile; VSync off; small generated ocean/coast world.',
 'Each scenario: 15 seconds warmup followed by 30 seconds of render-loop frame intervals. Screenshots are taken after the timed interval.', '',
 '| Scene | Frames | Mean FPS | 1% low FPS | P99 ms | Worst ms | Frames over 16.67 ms |',
 '|---|---:|---:|---:|---:|---:|---:|']
for row in rows:
    text.append(f"| {row['scenario']} | {row['frames']} | {row['mean_fps']:.1f} | {row['one_percent_low_fps']:.1f} | {row['p99_ms']:.2f} | {row['max_ms']:.2f} | {row['frames_over_16_667_ms']} |")
text+=['',
 'The 1% low value is 1000 divided by the mean of the slowest 1% of frame intervals. It is not an absolute minimum FPS.',
 'The absolute worst frame and the count of frames over the 60 FPS budget are reported separately.', '',
 f"P99 <= 16.67 ms in all scenes: {all(row['p99_ms']<=1000/60 for row in rows)}.",
 f"Every measured frame <= 16.67 ms: {all(row['max_ms']<=1000/60 for row in rows)}.", '',
 'These results apply to this small warmed-up test world only. They do not establish a 60 FPS floor across arbitrary worlds, chunk generation, mods, background workloads, weather or other dimensions.', '',
 'The startup mapping failure was caused by a missing `net.fabricmc:intermediary:1.21.1` JAR on the offline launch classpath. Its official SHA-256 was checked before installation. The subsequent launch resolved Minecraft to the intermediary namespace and loaded Iris/Sodium successfully.',
 'GPU validation: all 11 shader program pairs compiled and linked; numeric GPU probes passed for normal-incidence reflection, grazing reflection, total internal reflection and red-light attenuation at 10m.', '']
(report/'RESULTS.md').write_text('\n'.join(text))
print('\n'.join(text))
