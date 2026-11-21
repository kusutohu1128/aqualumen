#!/usr/bin/env bash
# Private forest-light benchmark JAR: same javac/jar recipe as tools/build-benchmark-mod.sh, but sources come from the
# pinned scratch snapshot (forest-tools/jar-src) and the output is build/aqualumen-benchmark-forest-light.jar.
# Never installs anything and never overwrites an existing file. Classes are built in a private /tmp directory.
set -euo pipefail
tools_dir="$(cd "$(dirname "$0")" && pwd)"
repo="$(cd "$tools_dir/../../.." && pwd)"
cd "$repo"
prism_root="${AQUALUMEN_PRISM_ROOT:-/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher}"
java_bin="$prism_root/java/java-runtime-delta/bin"
loader="$prism_root/libraries/net/fabricmc/fabric-loader/0.19.5/fabric-loader-0.19.5.jar"
mixin="$prism_root/libraries/net/fabricmc/sponge-mixin/0.17.4+mixin.0.8.7/sponge-mixin-0.17.4+mixin.0.8.7.jar"
output="build/aqualumen-benchmark-forest-light.jar"
if [[ -e "$output" || -L "$output" ]]; then printf 'Refusing to overwrite existing %s\n' "$output" >&2; exit 1; fi
mkdir -p build
# The pristine snapshot must still match the recorded hashes (proves the patch is relative to the pinned copy).
(cd "$tools_dir/jar-src-orig" && grep -v '^#' ../snapshot-original-sha256.txt | sha256sum --check --quiet)
src="$tools_dir/jar-src"
b="$src/dev/aqualumen/bench"
work="$(mktemp -d /tmp/aqualumen-forest-build.XXXXXX)"
classes="$work/classes"; tests="$work/tests"; mkdir -p "$classes" "$tests"
"$java_bin/javac" -proc:none -d "$classes" "$b/ScreenshotCompletion.java" "$b/NativeMotionCapture.java" "$b/GroundShadowClip.java"
cp="$classes:$loader"
"$java_bin/javac" -proc:none -cp "$cp:$mixin" -d "$classes" "$b/FrameMixin.java" "$b/CameraMixin.java" "$b/Recorder.java" "$b/OcclusionFixture.java" \
    "$b/ForestSite.java" "$b/LocalLightFixture.java" "$b/ScreenshotCompletion.java" "$b/UnderwaterScene.java" "$b/RenderTargetSnapshot.java" \
    "$b/BathymetrySnapshot.java" "$b/BathymetryMixin.java" "$b/ShoreSamplerSnapshot.java" "$b/ShoreRuntimeObserver.java" "$b/ShoreFinalMixin.java" "$b/SolarCacheSnapshot.java"
cp "$src/fabric.mod.json" "$src/aqualumen-benchmark.mixins.json" "$classes/"
# CPU tests: the new alias plans plus original suites that do not depend on the aliased scene keys.
t="$repo/tools/benchmark-mod/test/dev/aqualumen/bench"
"$java_bin/javac" -proc:none -cp "$classes:$loader" -d "$tests" "$src/test/dev/aqualumen/bench/ForestSiteTest.java" \
    "$t/LocalLightFixtureTest.java" "$t/ScreenshotCompletionTest.java" "$t/NativeMotionCaptureTest.java" "$t/UnderwaterSceneTest.java"
for test in ForestSiteTest LocalLightFixtureTest ScreenshotCompletionTest NativeMotionCaptureTest UnderwaterSceneTest; do
    "$java_bin/java" -cp "$tests:$classes:$loader" "dev.aqualumen.bench.$test"
done
"$java_bin/jar" --create --file "$output" -C "$classes" .
sha256sum "$output"
rm -rf "$work"
printf 'Built %s (private forest-light build; nothing installed)\n' "$output"
