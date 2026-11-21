# Underwater angular investigation — bounded diagnostic checkpoint

The full natural-water/sunlight goal remains open. This packet follows the
frozen 0.8.3 checkpoint; it does not modify or promote that shader candidate.
This completed diagnostic seam compares the original flat water VS/FS main against an
independent projected Snell/Fresnel/TIR directional marker field. Real uploaded
water-program camera matrices were captured separately, not guessed from
the screenshot or the user's FOV setting. The rendering goal remains incomplete.

## Lifecycle correction before new GPU work

The ordinary 0.6/physics0.2 world saved all three dimensions at 16:47:55 JST.
The absence of a subsequent log line and live Java process initially led to an
incorrect shutdown-stall diagnosis. A read-only `jcmd Thread.print` at 16:57:24
shows the Render thread in the normal GLFW display-FPS event wait, not a worker
join. Fresh native F2 at 16:58:30 shows the actual title menu. Clicking its
observed Quit button yields `Stopping!` at 16:59:27, terminal launcher-session
exit code 0 and absence of the owned Java/launcher PIDs 2958495/2958370.
No TERM or KILL was used for this ordinary client. This disproves the alleged
ordinary-worker shutdown stall; it does not prove older TEST stalls fixed.

The freshly saved ordinary world matches the private post-save backup
byte-for-byte. No ordinary-world restore, teleport, camera, time or terrain
automation occurred. Original options/Iris/benchmark properties are backed up
privately before installing any new instrumentation.

## Current evidence boundary

The final 0.3.9 projection observer passes CPU RED/GREEN and the retained suites.
Its actual JAR is installed only in Lab, and the exact 0.8.3 candidate produces
one focused 1600x900 near-up PNG and 585 raw intervals. The subsequent requested
TRANSLUCENT capture reads all four actual GPU mat4 uniforms and WATER/source
dimensions successfully, with all inner/outer caller state unchanged. The
[independent audit](observations/audit.json) checks all64 binary32 values and
the exact [replay packet](observations/actual-water-matrices.txt). This capture
is 66.011943401s after measurement completion, not proof of the PNG's same frame.

A native flat directional-marker replay
will not prove real terrain, a same-frame PNG, wave-rim appearance, offscreen
occlusion, motion, Minecraft FPS or full optical radiance calibration.

The first declared100-degree native fixture renders original flat water main
on NVIDIA GL4.6. All76608 saved angular RGB rows lie within their stated bounds,
but the independent visible reflected wall is not resolved by actual SSR; the
whole test is **INCONCLUSIVE**, not GREEN. The supplied real-matrix CPU
qualification also finds no reflected-wall control wholly inside this view.
Increasing only sample density does not remedy that viewport exclusion.
The logs/raw inputs/outputs are retained; no shipping change or relaxed bound
is justified by either result. The subsequently qualified control is recorded below.

The exact real-matrix native run also saves45012 angular RGB rows (15004 rays,
including344 TIR rays across near/deep flat planes) within the declared bounds.
It then fails the independent reflection-control viewport qualification as
predicted by CPU geometry. The complete actual-matrix test is still INCONCLUSIVE.
This is positive evidence about its flat angular subcheck, not attribution of
the natural image's remaining wave-rim or offscreen-reflection defects.

A read-only check of the frozen default reflection pixel finds a physically
visible first wall at travel0.2999252m and a supplied0.75 red C4 source. Those
saved C4/depth arrays are CPU-generated inputs, not standalone GPU texture
readbacks; a true behavior RED still needs that source qualification.
At the0.4m coarse sample, projected source/depth and crossing-width checks fit,
but the old `previous.z > scene.z - 0.25` policy fails by0.04641828m. This is a
source-level candidate for a visible-reflection miss, not yet a qualified shader
RED or a shipping correction. A predetermined later receiver supplies the
resolved positive reflection control recorded below.

## TEST lifecycle distinction

Unlike the ordinary case, actual TEST Save/Quit remains on the native `Saving
world` screen. A read-only thread dump shows client disconnect's nested render
loop waiting for the retained live integrated-server thread, while the server
continues its normal tick wait; no Java-monitor deadlock is demonstrated.
The exact own TEST Java2999348 and launcher2999220 receive scoped TERM only,
after persisted390-cell AIR/no-journal checks. They are absent, session74450
is terminal143, and the bounded post-stop AIR audit passes. This is not a clean
TEST exit or proof of whole-world/entity integrity. Ordinary saved data remains
untouched.

Local actual Minecraft bytecode shows the integrated server's last-player stop
gate compares the player's name with the resolved host profile name. A name-only
offline TEST override may disagree with the selected account's fetched profile.
This is a falsifiable candidate, not confirmed runtime host-profile evidence;
the next controlled check uses the existing normal profile on **only** disposable
V2 with the same Mods. Benchmark scope guards do not require a TEST username.

That controlled check now completes the same near-up benchmark behavior with
0.8.3/physics0.3.0/observer0.3.9 on V2 under the existing normal profile.
The actual Save/Quit log includes the host-stop line at17:30:59 and all three
dimensions saved. Native F2 at17:31:04 confirms the title menu, and the observed
Quit button produces `Stopping!` at17:32:13, session71840 terminal0 and absence
of the own Java3019869/launcher3019736. No signal is used for this matched-profile
client. This verifies an effective launch-identity workaround; it is not a dump
of the runtime host-profile field or proof that all possible shutdown bugs vanish.
The5s warmup/5s sample is not a controlled performance A/B against the20s TEST
warmup. All future automated checks still target only the exact disposable V2,
never the ordinary world, regardless of which account/profile launches it.

## Completed bounded native checkpoint

The predetermined0.55m wall fixture uses unchanged qualification/bounds and
first input-only eligible pixel18,16 (100 qualified of1028 angle candidates).
Its complete declared100-degree129x129 native test now passes, followed by an
explicitly serialized repeat. The two angular CSVs are byte-identical:
19440 transmitting and6096 TIR rays across near/deep flat planes,76608 RGB rows,
all within declared bounds; maximum angular RGB residual0.00011669042890372.
Wrong-index and rotated-marker controls exceed the unchanged error allowance.
The visible reflected tag actually contributes red C0=.18808098 against zero,
with observed Fresnel1 and SSR path=.5507498m. Whole-image original repeats and
passive STORE-neutrality remain required, including that positive reflector.

The [independent CPU artifact audit](native-independent-audit.json) confirms
all43 files are byte-identical across these two executions, all angular rows
meet their declared bounds, and whole-image original repeat/passive observation
differences are zero. This does not promote the actual-matrix whole test or
natural underwater appearance to accepted.

The [summary](native-wall055/SUMMARY.txt), [CSV](native-wall055/angular.csv),
[repeat log](native-wall055-repeat.log), original failed packets and raw input/
output arrays are retained. The subsequent explicitly serialized retained native
suite passes all11 program pairs and existing regressions. No shader shipping
source changes during this investigation; water FS remains
`c8cdbde6bc15fbf7dab3b59efd6f2897202eb2d5a1c0aee6bf71890b5f7e4ced`.

This closes a native-only flat angular baseline. The captured actual-view
subcheck is positive but its complete reflection qualification remains
INCONCLUSIVE. Correct flat angular mapping does not certify wave normals,
offscreen missing reflected geometry, natural clouds, motion, broad radiance
units or the actual image's visual acceptance. The next near-reflector seam
requires actual bound-texture readbacks and a derived visible-response bound
before any shipping correction.

## Ordinary restoration and handoff

After every owned GPU job is terminal, original options/Iris/benchmark bytes
match the fresh pre-test backups. Instrumentation is recoverably disabled and
ordinary0.6/physics0.2 selected. Ordinary saved data matches its fresh post-save
backup at this prelaunch point; no ordinary-world restoration or automation is
performed. See [restoration ledger](lifecycle/restoration-before-normal-launch.json).

The ordinary account/world is then actually reopened with0.6/physics0.2 and no
benchmark/fallback, paused and captured by native F2 at17:40:51. The original
options and benchmark-property bytes still match; Iris naturally rewrites only
its timestamp comment. Subsequent ordinary autosaves are natural game writes,
not a restored world or continuing byte-equality claim. The existing OpenAL
startup-device error remains; no audio repair or all-feature health is claimed.

The full realism goal remains active, with natural water/shore/cloud/motion and
broader physics still incomplete. These diagnostics deliberately do not redefine
that goal as shader compilation, a flat test PASS or successful restoration.

The visual defects recorded in 0.8.3—strong circular underwater curvature/dark
exterior, cyan shallows, pointed shore bands and artificial clouds—remain
unaccepted until stronger actual-scene evidence supports a correction.
