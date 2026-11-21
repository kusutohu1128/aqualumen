# Actual source adaptation and measured dense-reference cost

Concrete implementation/validation progress, not shipping/full-goal acceptance.
The full `docs/REALISM_GOAL.md` remains active. The diagnose skill kept source
provenance, solar support and derivative-bearing disk evaluation separate from
wave power/density/brightness tuning. Completed phase0/45 and previous RGB core
were not re-executed. No external Claude invocation, subagent, commit or push.

## New source adapter

The unused TEST module `water_supported_sources_test.glsl` imports the retained
supported RGB core read-only. It calls the real production refraction/reflection
tracers and source textures, not constant callback colors. A known air-side
receiver supplies C4; observed sky supplies the actual diffuse LUT. Unknown air
rays retain the old cave/access-squared proxy only when explicitly permitted.
Underwater reflected hits are Beer-attenuated with retained scatter; misses use
a counted, nonblack scatter proxy. Strict mode refuses any proxy and returns
the original color exactly. Missing geometry is not declared physical absence.

Diffuse LUT and sharp celestial sources are separate. Sun48 uses the identical
supported transmission/Smith kernel, stock beam/cache/weather/radius/units and
actual per-direction receiver classification. No unrelated reflected-hemisphere
condition can globally reject its transmission. Actual opaque receivers block
the direct cap, without discarding their shaded C4 source. Moon uses the retained
fixed full-moon radius/amplitude. Derivative-bearing disk AA is not called inside
new source quadratures. This is not a validated pixel-AA, Moon calibration or
index-squared/general étendue model. Raw n/v/C are retained without repair.

The new complete-adapter fixture removes only the old miss-only eligibility
exclusions (receiverKind/reflectedHit), since that restriction could never test
the actual sources. Existing source trace guards, water geometry and spectral
power are unchanged. Native evaluation remains one TEST pixel128,128, not a
production spatial cutoff. Wider projection fixtures have different actual C;
they are not claimed matched-Iris C or whole-Iris replays.

## Failures retained, actual GREEN independently qualified

Five initial source-contract errors mean the module was not implemented; they
are not an optical bug reproduction. Previous genuine optical OLD RED remains
sealed. Native main01 reported raw-control PASS but its authorization flag was
unset: independent audit correctly rejected it, and it is not accepted evidence.
The producer now checks typed authorization and actual invocation/application.
Every case also resets real source depth/C4, eliminating cross-case fixture leak.

Native main02 executes ten scenarios on RTX3080Ti. Independent audit verifies
920 raw comparisons, repeats, fresh direct TES/depth, actual named input maps,
queried four-stage hashes, raw n/v/C, status and unchanged outside-ROI C0. Enabled
and final-ledger C0 match exactly; strict/invalid/disabled return exactly the same
original color. This is the complete returned R+T contribution, not an added tag.

- Real diffuse LUT red0.25 produces transmission0.00610337825, matching the
  sealed transmission reference. Reflected diffuse proxy is nonzero too.
- Low-Sun native cap red2.33588600 matches the independent double model; rain
  red1.34313440 is57.5% under the unchanged weather factor. All48 nodes supported.
- Vertical Sun has48 physically absent directions and zero solar transmission.
- Wide-open actual source tracing observes6933 sky queries, zero air unknowns.
- Wide opaque plane observes6933 real receiver queries, blocks all48 solar
  nodes, and retains green receiver transmission0.00372851966.
- Cave access proxy gives zero direct Sun; fixed-Moon response is positive and
  matches its independent finite-cap reference. Neither proves natural night.

Narrow-aperture cases have5959 or6007 unobserved air queries. **All reflected
queries are misses**:14941 narrow /15145 wide. Proxies remain explicit; this
camera looks upward and cannot qualify a first visible underwater reflector.
Actual reflection-hit control and offscreen/water-volume transport remain open.
The auditor's original requirement that every case have unknown *air* queries
was wrong for the deliberately wide observed-source controls; its failed output
is retained before correcting that predicate. Reflection still uses proxies.

Ten source/reference/audit tests pass, including raw-solar mutation rejection
without Evidence edits. Two new CPU sampling tests pass. The existing NVIDIA
native suite and11 program pairs pass. These do not establish new Iris appearance.

## Performance changes the next action

Draw-only timing: six warmup draws,12 ABBA rounds,24 observations per role.
Separate saved-reader audit verifies34 exact current MAIN/depth/input witnesses.
Disabled median0.030720ms; enabled median72.354816ms (range72.303616–72.360960).
This is a257x257 native draw with **one** TEST evaluation pixel. It is not
Minecraft FPS, all-frame timing, or a valid pixel/full-frame extrapolation.
Nevertheless the dense reference integrator cannot be installed unchanged as
an ordinary whole-water real-time implementation. Keep it as a numeric oracle.

A new CPU prototype samples the SAME Gaussian slope law with randomly shifted
Halton/Box-Muller points and explicit density cancellation. Unsupported R/T
directions contribute zero separately; there is no survivor normalization or
physical spectrum change. Sun/Moon remain separate caps. At16 replicates×4096
samples, transmission mean errors5.14e-5–1.20e-4 exceed the existing tight
reference gates. Replicate standard errors are descriptions, not certified
coverage. This prototype is not adopted, GPU ported or temporally accumulated.
Improve critical-region importance sampling and variance control, rather than
pretend this initial estimator passed or blindly lower quadrature order.

## Preserved normal state

Ordinary launcher88646 saved all dimensions and exited0 before native GL; a new
post-save private baseline was made.41 ordinary saved-file hashes match before
reopening without restoration. Normal0.6/physics0.2 and original configs/disabled
TEST entries are verified; no TEST pack/Mod/config was installed. Root inspected
fresh normal runtime12:11:11 and paused12:11:19; owned launcher29163 and actual
Java3158807 remain live, with the ordinary session.lock independently observed.
No native GL after this handoff. Existing audio initialization failure is not fixed.

All old RGB/GLSL/transmission/legacy manifests and tracked diff SHA
ee4e019473a0468d187e9d3567ec1b1e30f4c6a5dc6b0526c494c3dcbfdd52c5 remain intact.
New source tools/fixtures/results are separately named. Safe continuation is in
RESUME.md. Natural shore/cloud/receiver/units/energy/motion and full-goal
completion remain required, not narrowed to the current numeric slice.
