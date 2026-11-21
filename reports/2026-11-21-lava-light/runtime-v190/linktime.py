"""Per-program NVIDIA link-time probe: runs `glcheck <shaders> --compile-only` on the NVIDIA EGL device (render lock held),
timestamps every stdout line and kills the probe after --limit seconds. Usage: linktime.py <shaders-dir> <out.json> [--limit S]"""
import fcntl, json, os, subprocess, sys, time
sys.path.insert(0, '/home/kusutohu/repos/aqualumen/reports/2026-11-21-indirect-light')
shaders, out = sys.argv[1], sys.argv[2]
limit = int(sys.argv[sys.argv.index('--limit') + 1]) if '--limit' in sys.argv else 600
lock = open('/tmp/aql-render21-1000.lock', 'a+b')
t0 = time.monotonic()
while True:
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB); break
    except BlockingIOError:
        if time.monotonic() - t0 > 900: raise SystemExit('lock timeout')
        time.sleep(2)
env = dict(os.environ); env.pop('DISPLAY', None); env.pop('WAYLAND_DISPLAY', None)
env['__GL_SHADER_DISK_CACHE_PATH'] = '/tmp/aql-v190-glcache-linktime'
os.makedirs(env['__GL_SHADER_DISK_CACHE_PATH'], exist_ok=True)
env['__GL_SHADER_DISK_CACHE'] = '0'  # cold compile every time
proc = subprocess.Popen(['stdbuf', '-oL', '/home/kusutohu/repos/aqualumen/build/glcheck', shaders, '--compile-only'], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
start = time.monotonic(); rows = []; last = start
import threading
def reader():
    global last
    for line in proc.stdout:
        now = time.monotonic(); rows.append(dict(t=round(now - start, 2), dt=round(now - last, 2), line=line.rstrip())); last = now
th = threading.Thread(target=reader, daemon=True); th.start()
while proc.poll() is None and time.monotonic() - start < limit: time.sleep(.5)
killed = proc.poll() is None
if killed: proc.kill()
proc.wait(); th.join(2)
res = dict(shaders=shaders, killedAtLimit=killed, limit=limit, rc=proc.returncode, seconds=round(time.monotonic() - start, 1), rows=rows,
           lastLineAgeSeconds=round(time.monotonic() - last, 1))
json.dump(res, open(out, 'w'), indent=2, ensure_ascii=False)
print('killed' if killed else 'finished', 'rows', len(rows), 'slowest', sorted(rows, key=lambda r: -r['dt'])[:6])
