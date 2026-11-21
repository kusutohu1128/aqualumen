#!/usr/bin/env python3
"""Negative controls for tools/rain-film-probe.h: each mutation of the parent's real GLSL must make the probe FAIL.
Usage: run_mutants.py GLCHECK_BINARY OUT_JSON [name ...]   (OUT_JSON must not exist)
Each run is a ~10 s headless EGL test, not a screenshot: it does NOT queue behind the shared render lock
(/tmp/aql-render21-1000.lock, held by Minecraft capture campaigns); whether the lock was busy is recorded per run."""
import fcntl, json, os, re, subprocess, sys, tempfile, time, shutil
from pathlib import Path
here = Path(__file__).resolve().parent
sys.path.insert(0, str(here))
import film_mock
binary, out_json = sys.argv[1], Path(sys.argv[2])
if out_json.exists(): sys.exit("refusing to overwrite " + str(out_json))
names = sys.argv[3:] or list(film_mock.MUTATIONS)
env = dict(os.environ, __EGL_VENDOR_LIBRARY_FILENAMES="/usr/share/glvnd/egl_vendor.d/10_nvidia.json")
results = {}
def lock_busy():
    with open("/tmp/aql-render21-1000.lock", "a+b") as f:
        try: fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB); fcntl.flock(f, fcntl.LOCK_UN); return False
        except OSError: return True
for name in names:
    tmp = Path(tempfile.mkdtemp(prefix="aql-rainfilm-mut-")) / "tree"
    shaders = film_mock.build(tmp, name)
    busy = lock_busy()
    t0 = time.time()
    p = subprocess.run([binary, str(shaders), "--rain-film-probe"], env=env, capture_output=True, text=True, timeout=300)
    text = p.stdout + p.stderr
    failing = re.findall(r"^FAIL (.+?): \d+/\d+ checks", text, re.M)
    renderer = re.search(r"^Renderer: (.+)$", text, re.M)
    summary = re.search(r"RAIN-FILM QA summary: (\d+) checks, (\d+) failed", text)
    compile_error = "error" in text.lower() and not summary
    results[name] = {
        "what": film_mock.MUTATIONS[name][3], "file": film_mock.MUTATIONS[name][0],
        "detected": p.returncode != 0, "exit": p.returncode,
        "failing_groups": failing, "summary": summary.group(0) if summary else None,
        "compile_or_runtime_error": text.strip().splitlines()[-1][:300] if compile_error else None,
        "renderer": renderer.group(1) if renderer else None, "render_lock_busy_at_start": busy, "seconds": round(time.time() - t0, 1),
    }
    print(f"{'DETECTED' if p.returncode else 'MISSED  '} {name}: {len(failing)} failing groups" + (" [error before tests]" if compile_error else ""), flush=True)
    shutil.rmtree(tmp.parent)
out_json.write_text(json.dumps(results, indent=1, ensure_ascii=False))
missed = [n for n, r in results.items() if not r["detected"]]
print("MISSED:", missed if missed else "none")
sys.exit(1 if missed else 0)
