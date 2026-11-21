#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
prism_root="${AQUALUMEN_PRISM_ROOT:-/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher}"
java_bin="$prism_root/java/java-runtime-delta/bin"
loader="$prism_root/libraries/net/fabricmc/fabric-loader/0.19.5/fabric-loader-0.19.5.jar"
mixin="$prism_root/libraries/net/fabricmc/sponge-mixin/0.17.4+mixin.0.8.7/sponge-mixin-0.17.4+mixin.0.8.7.jar"
benchmark='build/aqualumen-benchmark-0.3.9-projection-guards.jar'
expected_benchmark_sha='ef303d4b53a1299e64e562e81cf3ed70dfaffe96d99f5b8cbb58ff864cfd7b29'
output='build/aqualumen-water-stage-probe-0.1.0.jar'
if [[ -e "$output" || -L "$output" ]]; then
    printf '%s\n' "Refusing to overwrite $output" >&2
    exit 1
fi
for dependency in "$benchmark" "$loader" "$mixin"; do
    if [[ ! -f "$dependency" || -L "$dependency" ]]; then
        printf '%s\n' 'Missing or symlinked pinned local build dependency' >&2
        exit 1
    fi
done
actual_benchmark_sha=$(sha256sum "$benchmark")
if [[ "${actual_benchmark_sha%% *}" != "$expected_benchmark_sha" ]]; then
    printf '%s\n' 'Pinned existing benchmark JAR SHA mismatch; no build performed' >&2
    exit 1
fi
mkdir -p build
stage_classes=$(mktemp -d build/water-stage-classes.XXXXXX)
stage_test_classes=$(mktemp -d build/water-stage-test.XXXXXX)
"$java_bin/javac" -proc:none -cp "$benchmark:$loader:$mixin" -d "$stage_classes" \
    tools/water-stage-probe/dev/aqualumen/stageprobe/StageSnapshot.java \
    tools/water-stage-probe/dev/aqualumen/stageprobe/RequestGate.java \
    tools/water-stage-probe/dev/aqualumen/stageprobe/WaterStageObserver.java \
    tools/water-stage-probe/dev/aqualumen/stageprobe/mixin/WaterStageMixin.java
"$java_bin/javac" -proc:none -cp "$stage_classes:$benchmark:$loader" -d "$stage_test_classes" \
    tools/water-stage-probe/test/dev/aqualumen/stageprobe/StageSnapshotTest.java \
    tools/water-stage-probe/test/dev/aqualumen/stageprobe/RequestGateTest.java
"$java_bin/java" -cp "$stage_test_classes:$stage_classes:$benchmark:$loader" dev.aqualumen.stageprobe.StageSnapshotTest
"$java_bin/java" -cp "$stage_test_classes:$stage_classes:$benchmark:$loader" dev.aqualumen.stageprobe.RequestGateTest
cp tools/water-stage-probe/fabric.mod.json tools/water-stage-probe/aqualumen-water-stage-probe.mixins.json "$stage_classes/"
"$java_bin/jar" --create --file "$output" -C "$stage_classes" .
printf '%s\n' 'Built TEST-only build/aqualumen-water-stage-probe-0.1.0.jar; no installation or GL execution'
sha256sum "$output" "$benchmark"
