# Failed raw-interface diagnostic v89

Request `2a674ba8-ec4a-45ad-afeb-550b10700803` attempted the owned disposable
world UUID `b22dbccb-2970-41e6-847f-f183b1ec923d`. Sampling never began.

Native NVIDIA GLSL compile/link passed, but actual Iris 1.8.8 rejected the pack:
its `colortex12ClearColor` directive parser requires four explicit vec4 arguments
and fails on GLSL's valid one-argument constructor `vec4(0.0)`. Iris logged
`ArrayIndexOutOfBoundsException` in `DispatchingDirectiveHolder.processDirective`.
The benchmark correctly rejected shader fallback. No raw-palette screenshot or
ray-status measurement is accepted from this attempt.

The benchmark quit request was also rejected by its shader-active guard. Window
close requests did not terminate the client. Only the verified Lab Java process
was sent SIGTERM (PID1301083, namespace PID16, exact Lab cwd, sole Java process).
After Java was confirmed absent, only its owned diagnostic launcher child was
sent SIGTERM. The owned launcher handle completed and recorded exitCode143.
This was not a clean Minecraft shutdown; no ordinary process was terminated.

The helper subsequently verified exact restoration of configuration/Mods and
unchanged ordinary saves, without save rollback. `runtime-restored.json` records
those checks. `runtime-failure.json` pins the retained failure-log hash and
terminal state. Raw launcher logs remain private. The original failed ZIP is
retained and must not be overwritten.

The builder is corrected to emit `vec4(0.0,0.0,0.0,0.0)` and has a regression
assertion for that Iris directive spelling. A new unique pack must be tested;
this parser correction is not yet actual-runtime acceptance.
