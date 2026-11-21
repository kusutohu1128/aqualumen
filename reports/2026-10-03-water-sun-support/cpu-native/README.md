# CPU-native construction checkpoint

Eight public CPU tests pass; the final C++17/O2 build is warning-free. Source,
tests and the final executable are pinned in HANDOFF.json. All initial binaries,
RED logs and failed compilations remain separate, with no overwrite.

Only root may execute the native entry point. Pass four shader roots in order:
reject-reasons, zero-reasons, reject-inputs, zero-inputs, then a new output path.
The four-root `--cpu-contract` checks exact source recovery without creating GL.

The exporter retains six four-stage programs, four fixed central cases, and
descriptive 60°/90° views. C10.z is the certificate countword, not source kind;
input C12 is a first-failure target/index/reason, not TES. Reject counts were not
collected. Zero counts must be read from actual output: a synthetic CPU fixture
does not establish that the native branch ran.

No native result, optical reference acceptance, natural appearance, Iris,
pixel-AA, FPS floor or shipping acceptance is established by this checkpoint.
Forty-eight certified-zero quadrature samples do not prove a zero continuum.
