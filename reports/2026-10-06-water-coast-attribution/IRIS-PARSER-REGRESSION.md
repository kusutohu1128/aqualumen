# Retained actual-Iris RED and new v2

V1 compiled on native NVIDIA GL4.6, but real Iris1.8.8 rejected its annotation
`const vec4 colortex9ClearColor = vec4(0.0);` at14:09:47: its ConstDirective
parser requires four arguments. This is a new TEST builder defect, NOT the
natural coast defect or a production shader regression. Actual run never started
and no fallback screenshot is reported as an active shader capture.

V1 ZIP/source/pack.json/failed builder/parser log remain unchanged. Regression
`test_iris_clear_annotation_requires_four_explicit_components` was added before
fixing the builder and failed1/4 tests. Explicit fourzero components now pass4/4.
V2 differs from v1 in ONLY the three clear-vector annotations; nonwater GLSL
zeros remain valid single-argument constructors. V2 is NEW exclusive-created
ZIP/source/pack-v2.json, not a rewrite of failed evidence.

V1 TEST world saved all dimensions14:10:32, inspected title14.11.25 Quit focus,
owned launcher75727 exit0, Java3261945 absent. V2 native compile-only completed0
on RTX3080Ti/NVIDIA580.173.02GL4.6:11 pairs plus three compute entrypoints passed;
no draw/readback or neutrality claim. V2 installed before a distinct owned launch.
Native compile remains separate from actual Iris parser/routing execution.

UI F2 in the same invocation as focus changes can retain the previous frame's
highlight. Later title navigation separates tabbing, F2, root inspection and
Return. No process was terminated and no ordinary save was restored.

Old364-file seal first used the wrong check working directory, producing only
missing-relative-path errors. Correct repo-root `sha256sum --quiet -c` finished0;
no evidence files were modified to address that invocation error.
