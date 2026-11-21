# Timing claim before reading the scene timings

No speedup, regression or production FPS verdict is claimed. These are instrumented 1600x900 correctness scenes with a frozen bounded root solver, readback and the TEST receiver bridge. Their single-run frame distributions are observations only, not ordinary 0.6 performance or a comparison suitable for adoption.

Pre-extraction ambient check at 00:12:55 JST returned 24 logical processors and load averages 18.92, 14.76, 10.30. Unrelated Android builds were observed earlier and were not stopped. The sides are not interleaved five-run benchmarks. The CPU/GPU limiter has not been profiled, so the performance verdict is inconclusive.

The first five-second baseline run aborted with fewer than ten intervals. It is retained as a failure, not a fast successful sample. Later scenes use ten seconds of warmup and twenty seconds of sampling. A successful scene must identify the actual NVIDIA pack, world, framebuffer size and no shader fallback before its timings are reported.
