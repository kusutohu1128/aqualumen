#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
prism_root='/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher'
java_bin="$prism_root/java/java-runtime-delta/bin"
loader="$prism_root/libraries/net/fabricmc/fabric-loader/0.19.5/fabric-loader-0.19.5.jar"
mixin="$prism_root/libraries/net/fabricmc/sponge-mixin/0.17.4+mixin.0.8.7/sponge-mixin-0.17.4+mixin.0.8.7.jar"
benchmark=${AQUALUMEN_PAIRED_BENCHMARK_JAR:-build/aqualumen-benchmark-0.3.9-projection-guards.jar}
output=${1:-build/aqualumen-paired-water-probe-0.1.0.jar}
[[ "$output" == build/aqualumen-paired-water-probe-*.jar && "$output" != *'/'*'/'* && ! -e "$output" && ! -L "$output" ]] || { printf '%s\n' 'Refusing existing or out-of-scope output'; exit 1; }
[[ $(sha256sum "$benchmark" | cut -d' ' -f1) == ef303d4b53a1299e64e562e81cf3ed70dfaffe96d99f5b8cbb58ff864cfd7b29 ]] || { printf '%s\n' 'Pinned benchmark jar differs'; exit 1; }
mkdir -p build
classes=$(mktemp -d build/paired-water-classes.XXXXXX)
tests=$(mktemp -d build/paired-water-tests.XXXXXX)
"$java_bin/javac" -proc:none -cp "$loader:$mixin:$benchmark" -d "$classes" tools/paired-water-probe/dev/aqualumen/paired/*.java tools/paired-water-probe/dev/aqualumen/paired/mixin/*.java
"$java_bin/javac" -proc:none -cp "$classes" -d "$tests" tools/paired-water-probe/test/dev/aqualumen/paired/CaptureRulesTest.java
"$java_bin/java" -Djava.awt.headless=true -cp "$tests:$classes" dev.aqualumen.paired.CaptureRulesTest
cp tools/paired-water-probe/*.json "$classes/"
"$java_bin/jar" --create --file "$output" -C "$classes" .
sha256sum "$output"
