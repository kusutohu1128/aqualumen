#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
prism_root="${AQUALUMEN_PRISM_ROOT:-/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher}"
java_bin="$prism_root/java/java-runtime-delta/bin"
loader="$prism_root/libraries/net/fabricmc/fabric-loader/0.19.5/fabric-loader-0.19.5.jar"
mixin="$prism_root/libraries/net/fabricmc/sponge-mixin/0.17.4+mixin.0.8.7/sponge-mixin-0.17.4+mixin.0.8.7.jar"
mkdir -p build
output="${1:-build/aqualumen-benchmark-0.3.9-projection-guards.jar}"
if [[ $# -gt 1 || ! "$output" =~ ^build/aqualumen-benchmark-[A-Za-z0-9._-]+\.jar$ ]]; then
    printf '%s\n' 'Output must be a benchmark JAR directly under build/' >&2
    exit 1
fi
if [[ -e "$output" || -L "$output" ]]; then
    printf 'Refusing to overwrite existing %s\n' "$output" >&2
    exit 1
fi
task_classes=$(mktemp -d build/benchmark-classes.XXXXXX)
"$java_bin/javac" -proc:none -d "$task_classes" tools/benchmark-mod/dev/aqualumen/bench/ScreenshotCompletion.java tools/benchmark-mod/dev/aqualumen/bench/NativeMotionCapture.java tools/benchmark-mod/dev/aqualumen/bench/GroundShadowClip.java
loader="$task_classes:$loader"
"$java_bin/javac" -proc:none -cp "$loader:$mixin" -d "$task_classes" tools/benchmark-mod/dev/aqualumen/bench/FrameMixin.java tools/benchmark-mod/dev/aqualumen/bench/CameraMixin.java tools/benchmark-mod/dev/aqualumen/bench/Recorder.java tools/benchmark-mod/dev/aqualumen/bench/OcclusionFixture.java tools/benchmark-mod/dev/aqualumen/bench/LocalLightFixture.java tools/benchmark-mod/dev/aqualumen/bench/HandLightFixture.java tools/benchmark-mod/dev/aqualumen/bench/ScreenshotCompletion.java tools/benchmark-mod/dev/aqualumen/bench/UnderwaterScene.java tools/benchmark-mod/dev/aqualumen/bench/RenderTargetSnapshot.java tools/benchmark-mod/dev/aqualumen/bench/BathymetrySnapshot.java tools/benchmark-mod/dev/aqualumen/bench/BathymetryMixin.java tools/benchmark-mod/dev/aqualumen/bench/ShoreSamplerSnapshot.java tools/benchmark-mod/dev/aqualumen/bench/ShoreRuntimeObserver.java tools/benchmark-mod/dev/aqualumen/bench/ShoreFinalMixin.java tools/benchmark-mod/dev/aqualumen/bench/SolarCacheSnapshot.java
cp tools/benchmark-mod/fabric.mod.json tools/benchmark-mod/aqualumen-benchmark.mixins.json "$task_classes/"
task_test_classes=$(mktemp -d build/benchmark-test.XXXXXX)
"$java_bin/javac" -proc:none -cp "$task_classes" -d "$task_test_classes" tools/benchmark-mod/test/dev/aqualumen/bench/NativeMotionCaptureTest.java
"$java_bin/java" -cp "$task_test_classes:$task_classes" dev.aqualumen.bench.NativeMotionCaptureTest
"$java_bin/javac" -proc:none -cp "$task_classes:$loader" -d "$task_test_classes" tools/benchmark-mod/test/dev/aqualumen/bench/FinisherWaitTest.java tools/benchmark-mod/test/dev/aqualumen/bench/OcclusionFixtureTest.java tools/benchmark-mod/test/dev/aqualumen/bench/AirShadowFixtureTest.java tools/benchmark-mod/test/dev/aqualumen/bench/LocalLightFixtureTest.java tools/benchmark-mod/test/dev/aqualumen/bench/HandLightFixtureTest.java tools/benchmark-mod/test/dev/aqualumen/bench/ScreenshotCompletionTest.java tools/benchmark-mod/test/dev/aqualumen/bench/UnderwaterSceneTest.java tools/benchmark-mod/test/dev/aqualumen/bench/RenderTargetSnapshotTest.java tools/benchmark-mod/test/dev/aqualumen/bench/BathymetrySnapshotTest.java tools/benchmark-mod/test/dev/aqualumen/bench/BathymetryMetadataTest.java tools/benchmark-mod/test/dev/aqualumen/bench/ShoreSamplerSnapshotTest.java tools/benchmark-mod/test/dev/aqualumen/bench/SolarCacheSnapshotTest.java
"$java_bin/java" -cp "$task_test_classes:$task_classes:$loader" dev.aqualumen.bench.FinisherWaitTest
"$java_bin/java" -cp "$task_test_classes:$task_classes:$loader" dev.aqualumen.bench.OcclusionFixtureTest
"$java_bin/java" -cp "$task_test_classes:$task_classes:$loader" dev.aqualumen.bench.AirShadowFixtureTest
"$java_bin/java" -cp "$task_test_classes:$task_classes:$loader" dev.aqualumen.bench.LocalLightFixtureTest
"$java_bin/java" -cp "$task_test_classes:$task_classes:$loader" dev.aqualumen.bench.HandLightFixtureTest
"$java_bin/java" -cp "$task_test_classes:$task_classes:$loader" dev.aqualumen.bench.ScreenshotCompletionTest
"$java_bin/java" -cp "$task_test_classes:$task_classes:$loader" dev.aqualumen.bench.UnderwaterSceneTest
"$java_bin/java" -cp "$task_test_classes:$task_classes:$loader" dev.aqualumen.bench.RenderTargetSnapshotTest
"$java_bin/java" -cp "$task_test_classes:$task_classes:$loader" dev.aqualumen.bench.BathymetrySnapshotTest
"$java_bin/java" -cp "$task_test_classes:$task_classes:$loader" dev.aqualumen.bench.ShoreSamplerSnapshotTest
"$java_bin/java" -cp "$task_test_classes:$task_classes:$loader" dev.aqualumen.bench.SolarCacheSnapshotTest
"$java_bin/javac" -proc:none -cp "$task_classes:$loader" -d "$task_test_classes" tools/benchmark-mod/test/dev/aqualumen/bench/ShoreRuntimeGuardsTest.java
"$java_bin/java" -cp "$task_test_classes:$task_classes:$loader" dev.aqualumen.bench.ShoreRuntimeGuardsTest
"$java_bin/java" -cp "$task_test_classes:$task_classes:$loader" dev.aqualumen.bench.BathymetryMetadataTest dist/aqualumen-physics-0.3.0.jar dist/aqualumen-physics-0.2.0.jar "$task_test_classes"
python3 -B tools/benchmark-mod/test/test_air_shadow_report.py
python3 -B tools/benchmark-mod/test/test_audit_fixture_air.py
python3 -B tools/benchmark-mod/test/test_png_integrity.py
python3 -B tools/benchmark-mod/test/test_underwater_up_control.py
python3 -B tools/benchmark-mod/test/test_local_light_control.py
python3 -B tools/benchmark-mod/test/test_local_light_geometry.py
python3 -B tools/benchmark-mod/test/test_hand_light_control.py
python3 -B tools/benchmark-mod/test/test_hand_light_geometry.py
python3 -B tools/benchmark-mod/test/test_underwater_up_report.py
"$java_bin/jar" --create --file "$output" -C "$task_classes" .
printf 'Built %s (existing artifacts untouched; not installed)\n' "$output"
