#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
prism_root="${AQUALUMEN_PRISM_ROOT:-/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher}"
java_bin="$prism_root/java/java-runtime-delta/bin"
loader="$prism_root/libraries/net/fabricmc/fabric-loader/0.19.5/fabric-loader-0.19.5.jar"
mixin="$prism_root/libraries/net/fabricmc/sponge-mixin/0.17.4+mixin.0.8.7/sponge-mixin-0.17.4+mixin.0.8.7.jar"
benchmark='build/aqualumen-benchmark-0.3.9-projection-guards.jar'
expected_benchmark_sha='ef303d4b53a1299e64e562e81cf3ed70dfaffe96d99f5b8cbb58ff864cfd7b29'
output="${1:-build/aqualumen-water-sun-test-0.1.0.jar}"
if [[ ! "$output" =~ ^build/aqualumen-water-sun-test-0\.1\.0([a-zA-Z0-9._-]*)\.jar$ ]]; then
    printf '%s\n' 'Expected a NEW versioned build/aqualumen-water-sun-test-0.1.0*.jar output' >&2
    exit 1
fi
if [[ -e "$output" || -L "$output" ]]; then
    printf '%s\n' 'Refusing to overwrite an existing artifact' >&2
    exit 1
fi
for dependency in "$benchmark" "$loader" "$mixin"; do
    if [[ ! -f "$dependency" || -L "$dependency" ]]; then
        printf '%s\n' 'Missing or symlinked pinned local dependency' >&2
        exit 1
    fi
done
actual_benchmark_sha=$(sha256sum "$benchmark")
if [[ "${actual_benchmark_sha%% *}" != "$expected_benchmark_sha" ]]; then
    printf '%s\n' 'Pinned benchmark JAR hash mismatch' >&2
    exit 1
fi
classes=$(mktemp -d build/water-sun-test-classes.XXXXXX)
test_classes=$(mktemp -d build/water-sun-test-tests.XXXXXX)
"$java_bin/javac" -proc:none -Xlint:all -cp "$benchmark:$loader:$mixin" -d "$classes" \
    tools/water-sun-test-mod/dev/aqualumen/suntest/*.java \
    tools/water-sun-test-mod/dev/aqualumen/suntest/mixin/*.java
"$java_bin/javac" -proc:none -Xlint:all -cp "$classes:$benchmark:$loader" -d "$test_classes" \
    tools/water-sun-test-mod/test/dev/aqualumen/suntest/*.java
"$java_bin/java" -cp "$test_classes:$classes:$benchmark:$loader" dev.aqualumen.suntest.SunAuthorizationTest
"$java_bin/java" -cp "$test_classes:$classes:$benchmark:$loader" dev.aqualumen.suntest.SunFilesystemTest \
    reports/2026-10-03-water-residual-sun-iris/cpu-guard
"$java_bin/java" -cp "$test_classes:$classes:$benchmark:$loader" dev.aqualumen.suntest.SunGuardSnapshotTest
"$java_bin/java" -cp "$test_classes:$classes:$benchmark:$loader" dev.aqualumen.suntest.SunRequestGateTest
cp tools/water-sun-test-mod/fabric.mod.json tools/water-sun-test-mod/aqualumen-water-sun-test.mixins.json "$classes/"
"$java_bin/jar" --create --file "$output" -C "$classes" .
printf '%s\n' 'Built TEST-only Sun guard; no installation, Minecraft, or GL execution'
sha256sum "$output" "$benchmark"
