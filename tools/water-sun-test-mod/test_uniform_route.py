#!/usr/bin/env python3
"""Bounded actual-Iris bytecode/compiled-Mod integration contract, not GL proof."""
import argparse
import hashlib
import pathlib
import re
import subprocess

IRIS_SHA = "b5ad39a6cb113ca0a1765f06689f9f4b29ccd0c81247de90b06c42f5da1092f5"

def check(iris, product, javap):
    if iris.is_symlink() or not iris.is_file() or iris.stat().st_size > 32 * 1024 * 1024:
        raise ValueError("Expected bounded pinned local Iris JAR")
    if hashlib.sha256(iris.read_bytes()).hexdigest() != IRIS_SHA:
        raise ValueError("Actual Iris bytecode pin mismatch")
    def inspect(classpath, owner, *flags):
        result = subprocess.run([str(javap), "-p", *flags, "-classpath", str(classpath), owner],
                                check=True, capture_output=True, text=True, timeout=15)
        if len(result.stdout) > 512 * 1024:
            raise ValueError("Oversized javap output")
        return result.stdout
    sodium = inspect(iris, "net.irisshaders.iris.pipeline.programs.SodiumShader", "-c")
    build = sodium.split("private net.irisshaders.iris.gl.program.ProgramUniforms buildUniforms", 1)[1]
    build = build.split("private net.irisshaders.iris.gl.program.ProgramSamplers buildSamplers", 1)[0]
    called = set(re.findall(r"CommonUniforms\.(\w+):", build))
    compiled = inspect(product, "dev.aqualumen.suntest.mixin.SunUniformMixin", "-v")
    targets = re.findall(r'method=\["(\w+)"\]', compiled)
    if len(targets) != 1 or targets[0] not in called:
        raise AssertionError(f"Guard registration target {targets} is not on actual Sodium uniform path {sorted(called)}")
    common = inspect(iris, "net.irisshaders.iris.uniforms.CommonUniforms")
    if targets[0] == "addDynamicUniforms":
        if "void addDynamicUniforms(net.irisshaders.iris.gl.uniform.DynamicUniformHolder, net.irisshaders.iris.gl.state.FogMode)" not in common:
            raise AssertionError("Pinned dynamic uniform signature missing")
        if "(java.lang.Object, java.lang.Object, org.spongepowered.asm.mixin.injection.callback.CallbackInfo)" not in compiled:
            raise AssertionError("Injection handler arity does not match actual dynamic method")
    if 'value="TAIL"' not in compiled or "ACC_STATIC" not in compiled:
        raise AssertionError("Expected static TAIL registration")
    print("PASS CPU actual pinned Iris + compiled-Mod routing: " + targets[0] + "; runtime mixin/GL unverified")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("iris", type=pathlib.Path); p.add_argument("product", type=pathlib.Path)
    p.add_argument("javap", type=pathlib.Path)
    a = p.parse_args(); check(a.iris, a.product, a.javap)
