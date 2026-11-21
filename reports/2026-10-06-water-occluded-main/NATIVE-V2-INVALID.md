# Invalid revised run: previous binary was executed

The v2 run was started while corrected build handle11855 still reported running.
It therefore executed the previous v1 binary: both recorded binary SHA256 values
are identical, and its stdout reports pixel64,53 rather than revised65,53.
The frozen v2 source is newer than the binary. **v2 is not valid source-to-GPU
evidence and must not be used for acceptance or the corrected regression.**

No old output is overwritten. The correction is to compile a unique per-report
binary synchronously inside the recording process, require compiler exit0, then
execute that exact path and retain its compile log/hash. This prevents observing
a live compiler and accidentally running an old executable. v3 is required.

This is an orchestration failure, not a shader fix or a new visual result.
