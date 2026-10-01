# RTX 3080 Ti / Minecraft 1.21.1 verification

RTX 3080 Ti 12GB, NVIDIA 580.173.02, Iris 1.8.8, Sodium 0.6.9, Fabric Loader 0.19.5, Java 21.0.7.
2560×1440; 12 render chunks, 6 simulation chunks; BALANCED shader profile; VSync off; small generated ocean/coast world.
Each scenario: 15 seconds warmup followed by 30 seconds of render-loop frame intervals. Screenshots are taken after the timed interval.

| Scene | Frames | Mean FPS | 1% low FPS | P99 ms | Worst ms | Frames over 16.67 ms |
|---|---:|---:|---:|---:|---:|---:|
| noon-water | 15226 | 507.5 | 261.3 | 3.38 | 7.96 | 0 |
| coast-shadows | 16075 | 535.8 | 281.5 | 3.17 | 5.79 | 0 |
| sunset-water | 15729 | 524.3 | 277.9 | 3.27 | 6.51 | 0 |
| underwater | 20429 | 681.0 | 318.2 | 2.78 | 6.22 | 0 |
| moving-view | 15586 | 519.5 | 266.2 | 3.41 | 5.75 | 0 |

The 1% low value is 1000 divided by the mean of the slowest 1% of frame intervals. It is not an absolute minimum FPS.
The absolute worst frame and the count of frames over the 60 FPS budget are reported separately.

P99 <= 16.67 ms in all scenes: True.
Every measured frame <= 16.67 ms: True.

These results apply to this small warmed-up test world only. They do not establish a 60 FPS floor across arbitrary worlds, chunk generation, mods, background workloads, weather or other dimensions.

The startup mapping failure was caused by a missing `net.fabricmc:intermediary:1.21.1` JAR on the offline launch classpath. Its official SHA-256 was checked before installation. The subsequent launch resolved Minecraft to the intermediary namespace and loaded Iris/Sodium successfully.
GPU validation: all 11 shader program pairs compiled and linked; numeric GPU probes passed for normal-incidence reflection, grazing reflection, total internal reflection and red-light attenuation at 10m.
