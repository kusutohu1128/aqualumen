#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
java_bin="${AQUALUMEN_PRISM_ROOT:-/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher}/java/java-runtime-delta/bin"
classes=$(mktemp -d build/receiver-member-cache-test.XXXXXX)
"$java_bin/javac" -proc:none -d "$classes" physics-mod/dev/aqualumen/physics/ReceiverMemberCache.java physics-mod/test/dev/aqualumen/physics/ReceiverMemberCacheTest.java
"$java_bin/java" -cp "$classes" dev.aqualumen.physics.ReceiverMemberCacheTest
