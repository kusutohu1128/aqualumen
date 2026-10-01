#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
prism_root="${AQUALUMEN_PRISM_ROOT:-/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher}"
java_bin="$prism_root/java/java-runtime-delta/bin"
loader="$prism_root/libraries/net/fabricmc/fabric-loader/0.19.5/fabric-loader-0.19.5.jar"
mixin="$prism_root/libraries/net/fabricmc/sponge-mixin/0.17.4+mixin.0.8.7/sponge-mixin-0.17.4+mixin.0.8.7.jar"
mkdir -p build
task_classes=$(mktemp -d build/benchmark-classes.XXXXXX)
"$java_bin/javac" -proc:none -cp "$loader:$mixin" -d "$task_classes" tools/benchmark-mod/dev/aqualumen/bench/FrameMixin.java tools/benchmark-mod/dev/aqualumen/bench/CameraMixin.java tools/benchmark-mod/dev/aqualumen/bench/Recorder.java tools/benchmark-mod/dev/aqualumen/bench/OcclusionFixture.java
cp tools/benchmark-mod/fabric.mod.json tools/benchmark-mod/aqualumen-benchmark.mixins.json "$task_classes/"
task_test_classes=$(mktemp -d build/benchmark-test.XXXXXX)
"$java_bin/javac" -proc:none -cp "$task_classes:$loader" -d "$task_test_classes" tools/benchmark-mod/test/dev/aqualumen/bench/FinisherWaitTest.java tools/benchmark-mod/test/dev/aqualumen/bench/OcclusionFixtureTest.java
"$java_bin/java" -cp "$task_test_classes:$task_classes:$loader" dev.aqualumen.bench.FinisherWaitTest
"$java_bin/java" -cp "$task_test_classes:$task_classes:$loader" dev.aqualumen.bench.OcclusionFixtureTest
"$java_bin/jar" --create --file build/aqualumen-benchmark-0.3.1.jar -C "$task_classes" .
printf '%s\n' 'Built build/aqualumen-benchmark-0.3.1.jar'
