#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
java_bin="${AQUALUMEN_PRISM_ROOT:-/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher}/java/java-runtime-delta/bin"
classes=$(mktemp -d build/receiver-pack-eligibility.XXXXXX)
"$java_bin/javac" -proc:none -d "$classes" physics-mod/dev/aqualumen/physics/ReceiverPackEligibility.java physics-mod/test/dev/aqualumen/physics/ReceiverPackEligibilityTest.java
"$java_bin/java" -cp "$classes" dev.aqualumen.physics.ReceiverPackEligibilityTest
