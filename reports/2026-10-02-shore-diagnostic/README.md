# Post-0.5 stepped-shore investigation

2026-10-02. This is **diagnostic evidence, not a shipping water fix or full-goal
completion**. The installed0.5 ZIP and production shader bytes stay unchanged.
The diagnostic extends only the native opt-in CLI, not default `make check`
acceptance. Implementation and independent review are Codex work.

See the [design and measured findings](../../docs/reviews/codex-shore-diagnostic-design.md)
and [independent CPU review](../../docs/reviews/codex-shore-diagnostic-review.md).
Executed command: `build/glcheck shaders --shore-diagnostic-only`, against0.5
shader commit `4d732c9`, real RTX3080Ti/NVIDIA580.173.02/native GL4.6.
Minecraft was paused, with no Minecraft frame measurement running.

## Preserved raw evidence

- [First log](first.log) and [all first artifacts](first-artifacts.tar.gz)
  preserve the initial investigation, including legitimate input discontinuities.
- [Qualified log](qualified.log) and [all qualified artifacts](qualified-artifacts.tar.gz)
  include both-filter source/repeat controls, independent scene inputs, raw HDR
  PFM/RGBA32F images, source-response fields, endpoint metadata and expanded
  one-variable diagnostic programs. No game screenshot was edited.
- [Same baseline bracket](same-baseline-bracket.csv) compares variants at the
  same pixel/endpoints; [all jump measurements](jumps.csv) retain each variant's
  own search result. The two should not be confused.
- The [default full check](default-check.log) was rerun after the CLI addition:
  all11 graphics pairs,3 compute programs and retained controls pass. This is
  shader correctness evidence, not game FPS or proof of shoreline realism.

Each archive uses relative names and contains only that run's generated
diagnostic files. SHA-256 values are preserved in [SHA256SUMS](SHA256SUMS).
The standalone build directories remain available; a future run may replace
the second directory, so these exported archives identify this checkpoint.
Read-only round-trip validation confirms108 first-run and211 qualified-run
files: every archived entry has safe relative naming and bytes identical to
its original generated file. All46 entries of the0.5 installed-source archive
still match production files; the diagnostics are not shipping ZIP entries.

## What changes the next action

Both filters retain positive above-water reflection and deep-bottom responses,
zero reflection tag in the environment-only variant, and exact repeatability.
The safely-deep2064-pixel derivative-quad control has measured clearance at least
1.13674m and no change under the fragment-depth64 variant. Pointwise NEAREST
green-source differences do not demonstrate submerged SSR in this fixture.

The largest first-run baseline jump is at the finite world boundary, where a
gray receiver becomes sky. Another same-face jump crosses the fixture's wet/dry
palette. Neither is treated as a shader defect.

With full-quad original face/color/coverage qualification, the NEAREST baseline
at pixel `(65,46)`, b=`0.0464765616..0.0464843735`m, retains RGB change0.0518771.
At those exact endpoints the environment-only variant is unchanged, face-normal
change is9.57e-6 and fragment-depth64 change7.45e-9. This points to the coupled
optical-normal/view-depth/refraction path for that switch, not SSR alone.
Other variants still have other large switches. LINEAR filtering behaves
differently, and the actual refracted receiver/texel/occlusion identity is not
yet proven continuous.

The next causal check must distinguish a screen-space miss/rejection switch
from a legitimate stepped receiver/source edge, ideally with independently
raycast geometry and a controlled actual-main output. Do not ship a global
flat-normal/deep-depth substitution just because it shrinks one bracket. The
natural cyan shore, temporal rowing/wakes, cloud/light coherence and other
[full-goal requirements](../../docs/REALISM_GOAL.md) remain open.

## Ordinary runtime after investigation

At21:23:58UTC, normal Java2322822 remained live, installed and selected0.5
still hashed88ff19…, ordinary options still matched the pre-test snapshot
byte-for-byte, and active benchmark JAR count was0 with the opt-in marker absent.
The fresh native [paused image](ordinary-paused.png), captured06:22:24JST and
visually inspected, passes the1600x900 PNG integrity checker. This is a later
point-in-time handoff check, not a new gameplay performance measurement or an
ordinary-world content checksum. Source changes in this investigation did not
alter the selected pack or reload/automate the user's world.
