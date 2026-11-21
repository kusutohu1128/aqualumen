"""Real 1.8.0 client play test: Overworld outpost with a warm torch and a soul torch -> lit Nether portal -> Nether -> back -> same outpost.

  python3 -I run.py <label> [--lock-wait SECONDS]

Adapted from reports/2026-11-21-lava-light/cavern/run.py (explicit-path helpers, copied patterns; that file is untouched).
Private TMP Lab clone (3 normal production jars, no test mod), private Xvfb DISPLAY >= 260, VirtualGL egl0, xdotool input to that window only
(automated, not a human). No commands, no teleport, no datapack while playing; F3/F2/F1 are ordinary keys in the private window.
The render lock /tmp/aql-render21-<uid>.lock is taken SHARED (non-blocking, bounded wait) BEFORE anything is created; if it stays exclusive nothing starts.
"""
import argparse, fcntl, gzip, hashlib, json, math, os, re, shutil, signal, string, subprocess, sys, tempfile, time
from pathlib import Path
from zipfile import ZipFile
import numpy as np
from PIL import Image

here = Path(__file__).resolve().parent
root = here.parents[1]
for sub in ('reports/2026-11-21-rain-eaves/journey', 'reports/2026-11-21-rain-eaves/fixture', 'reports/2026-11-21-door-light/playable', 'tools'):
    sys.path.insert(0, str(root / sub))
import hud, route_fps, anvil          # noqa: E402,F401
import ground_shadow_lab as g         # noqa: E402  (paths + option editing helpers only)
from validate_world import parse_nbt  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('label'); ap.add_argument('--lock-wait', type=int, default=0)
ap.add_argument('--no-video', action='store_true')
args = ap.parse_args()
assert re.fullmatch('[a-z0-9-]+', args.label)
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
write = lambda p, v: Path(p).write_text(json.dumps(v, indent=2, ensure_ascii=False, default=str) + '\n')
NAME = 'Aqualumen-Portal-Return'
W, H, DISPLAY_MIN = 1600, 900, 260
PLAYER, PLAYER_UUID = 'Outposter', '00000000000040008000000000000310'
build = root / 'build/aql-portal-return'
world_zip = build / (NAME + '.zip')
fix = json.loads((build / 'fixture.json').read_text())
assert sha(world_zip) == fix['sha256']
pack_src = root / 'dist/Aqualumen-1.8.0.zip'
pack = build / 'Aqualumen-1.8.0.zip'
if not pack.exists():
    shutil.copyfile(pack_src, pack)
assert sha(pack) == sha(pack_src)
notefile = here / 'progress.txt'
def note(t):
    with notefile.open('a') as f: f.write('%s %s\n' % (time.strftime('%Y-%m-%dT%H:%M:%S%z'), t))

# ---- 1. render lock FIRST: shared, non-blocking, bounded wait; never start while exclusive ----
lock = open('/tmp/aql-render21-%d.lock' % os.getuid(), 'a+b')
t0 = time.monotonic(); lock_wait_s = None
while True:
    try:
        fcntl.flock(lock, fcntl.LOCK_SH | fcntl.LOCK_NB); lock_wait_s = round(time.monotonic() - t0, 1); break
    except BlockingIOError:
        if time.monotonic() - t0 >= args.lock_wait:
            note('%s: render lock held exclusive; NOT started (waited %ds)' % (args.label, args.lock_wait)); print('LOCK_EXCLUSIVE_HELD'); sys.exit(3)
        time.sleep(10)
note('%s: shared lock acquired after %ss' % (args.label, lock_wait_s))

def private_sessions():
    n = []
    for p in Path('/proc').iterdir():
        if p.name.isdigit():
            try: cl = (p / 'cmdline').read_bytes().split(b'\0')
            except OSError: continue
            if b'net.fabricmc.loader.impl.launch.knot.KnotClient' in cl and any(c.startswith(b'/tmp/aql-') for c in cl): n.append(int(p.name))
    return n
t1 = time.monotonic()
while len(private_sessions()) >= 2:
    assert time.monotonic() - t1 < 900, 'two private sessions still running'
    time.sleep(10)

out = here / args.label; out.mkdir()
orig = g.GAME.resolve()
guards = ['config/iris.properties', 'options.txt', 'config/sodium-options.json']
original = {n: sha(orig / n) for n in guards}
mods = {n: sha(orig / 'mods' / n) for n in g.lab.NORMAL_MODS}
lab_world = orig / 'saves' / g.lab.WORLD
tree = lambda: {str(p.relative_to(lab_world)): p.stat().st_mtime_ns for p in lab_world.rglob('*') if p.is_file() and p.name != 'session.lock'} if lab_world.exists() else {}
lab_world_tree = tree()

base = Path(tempfile.mkdtemp(prefix='aql-portal-return-run-', dir='/tmp'))
game = base / 'minecraft'
for d in ('saves', 'mods', 'config', 'shaderpacks', 'screenshots'): (game / d).mkdir(parents=True)
for n in mods: shutil.copyfile(orig / 'mods' / n, game / 'mods' / n)
assert {p.name for p in (game / 'mods').iterdir()} == g.lab.NORMAL_MODS
shutil.copyfile(pack, game / 'shaderpacks' / pack.name)
for n in ('config/iris.properties', 'config/sodium-options.json'): shutil.copyfile(orig / n, game / n)
iris = game / 'config/iris.properties'
iris.write_bytes(g.lab.replace_values(iris.read_bytes(), {'shaderPack': pack.name}, '='))
opt = dict(g.lab.OPTIONS, fullscreen='false', maxFps='60', enableVsync='false', overrideWidth=str(W), overrideHeight=str(H), rawMouseInput='false',
           mouseSensitivity='0.5', guiScale='2', lang='en_us', forceUnicodeFont='false', pauseOnLostFocus='false', fov='0.0', fovEffectScale='0.0',
           bobView='false', reducedDebugInfo='false', autoJump='true', screenEffectScale='0.0', chatVisibility='2')
(game / 'options.txt').write_bytes(g.lab.replace_values((orig / 'options.txt').read_bytes(), opt, ':'))
with ZipFile(world_zip) as z: z.extractall(game / 'saves')
save = game / 'saves' / NAME
pristine = base / 'pristine'
with ZipFile(world_zip) as z: z.extractall(pristine)
pristine = pristine / NAME
lv0 = parse_nbt(gzip.decompress((save / 'level.dat').read_bytes()))['Data']
assert lv0['allowCommands'] == 0 and lv0['GameType'] == 0 and 'Player' not in lv0
runtime = json.loads((root / 'reports/2026-11-20-underwater-refinement/local-launch.json').read_text())
vgl = Path((root / 'reports/2026-11-21-lava-light/runtime-v190/vgl-dir.txt').read_text().strip()) / 'x/usr/lib'
assert (vgl / 'libvglfaker.so').is_file() and (vgl / 'libdlfaker.so').is_file()
glcache = base / 'glcache'
src_cache = Path.home() / '.cache/aqualumen-lab-shader-driver'
if src_cache.is_dir(): shutil.copytree(src_cache, glcache)   # read-only seed copy, shared cache never written
else: glcache.mkdir()

def start_xvfb():
    for n in range(DISPLAY_MIN, DISPLAY_MIN + 40):
        if Path('/tmp/.X11-unix/X%d' % n).exists() or Path('/tmp/.X%d-lock' % n).exists(): continue
        log = (base / 'xvfb.log').open('wb')
        proc = subprocess.Popen(['Xvfb', ':%d' % n, '-screen', '0', '%dx%dx24' % (W, H), '+extension', 'GLX', '+extension', 'RENDER', '-nolisten', 'tcp', '-noreset'],
                                stdout=log, stderr=log, start_new_session=True)
        for _ in range(100):
            if Path('/tmp/.X11-unix/X%d' % n).exists() or proc.poll() is not None: break
            time.sleep(.1)
        if proc.poll() is None and Path('/tmp/.X11-unix/X%d' % n).exists(): return proc, ':%d' % n
    raise RuntimeError('no free private display')
xvfb, display = start_xvfb()
assert int(display[1:]) >= DISPLAY_MIN and display != os.environ.get('DISPLAY')
env = {k: v for k, v in os.environ.items() if k not in ('WAYLAND_DISPLAY', 'XAUTHORITY', 'DISPLAY', 'XDG_SESSION_TYPE', 'LD_PRELOAD', 'JAVA_TOOL_OPTIONS', 'JDK_JAVA_OPTIONS')}
env.update(DISPLAY=display, ALSOFT_DRIVERS='null', __GL_SHADER_DISK_CACHE_PATH=str(glcache), XDG_CACHE_HOME=str(base / 'cache'),
           LD_PRELOAD='%s:%s' % (vgl / 'libdlfaker.so', vgl / 'libvglfaker.so'), VGL_DISPLAY='egl0', VGL_LOGO='0', VGL_COMPRESS='0', VGL_SPOIL='0', VGL_VERBOSE='1')
cmd = [runtime['java'], '-Xms512m', '-Xmx2600m', '-XX:ActiveProcessorCount=4', '-Dorg.lwjgl.openal.libname=libopenal.so.1', '-cp', ':'.join(runtime['cp']),
       'net.fabricmc.loader.impl.launch.knot.KnotClient', '--username', PLAYER, '--version', '1.21.1', '--gameDir', str(game), '--assetsDir', str(orig.parents[2] / 'assets'),
       '--assetIndex', '17', '--uuid', PLAYER_UUID, '--accessToken', '0', '--userType', 'legacy', '--width', str(W), '--height', str(H), '--quickPlaySingleplayer', NAME]
logpath = out / 'client.log'
obs, shots, fpsrec, events = [], {}, [], []
st = {'start': None, 'wid': None, 'debug': False, 'proc': None, 'hud': True}
(out / 'private-game.txt').write_text('%s\n%s\n' % (game, display))
note('%s: prepared display=%s game=%s' % (args.label, display, game))

def x(*a, timeout=6): return subprocess.check_output(['xdotool', *a], env=env, timeout=timeout, text=True, stderr=subprocess.DEVNULL).strip()
def log(): return logpath.read_text(errors='replace')
def guard_ok():
    p = st['proc']; assert p.poll() is None
    assert Path('/proc', str(p.pid), 'cwd').resolve() == game.resolve()
    assert x('getwindowpid', st['wid']) == str(p.pid) and x('getwindowfocus') == st['wid']
def key(k): guard_ok(); x('key', k)
def f3(active):
    if st['debug'] != active: key('F3'); time.sleep(.5 if active else .3); st['debug'] = active
def hide_hud(hidden):
    if st['hud'] == hidden: key('F1'); time.sleep(.4); st['hud'] = not hidden
def grab():
    d = subprocess.check_output(['ffmpeg', '-v', 'error', '-f', 'x11grab', '-window_id', st['wid'], '-i', display, '-frames:v', '1', '-threads', '1', '-pix_fmt', 'bgr0', '-f', 'rawvideo', 'pipe:1'], env=env, timeout=8)
    assert len(d) == W * H * 4
    return Image.frombytes('RGB', (W, H), d, 'raw', 'BGRX')
def stage(m): note('%s: %s' % (args.label, m)); events.append({'t': round(time.monotonic() - st['start'], 1) if st['start'] else None, 'event': m})

ALPHA = string.ascii_letters + '0123456789-.()/ :_'
def read(rgb):
    pos = hud.position(rgb)
    ang = hud.row_text(rgb, 'Facing: ', ALPHA)
    m = re.search(r'\((-?[0-9.]+) / (-?[0-9.]+)\)', ang or '')
    dim = hud.row_text(rgb, 'minecraft:', ALPHA)
    return pos, (list(map(float, m.groups())) if m else None), dim
def observe(label, keep=False):
    f3(True)
    for _ in range(10):
        im = grab(); rgb = np.asarray(im); pos, ang, dim = read(rgb)
        if pos and ang: break
        time.sleep(.3)
    else:
        im.save(out / 'unreadable-hud.png'); raise RuntimeError('cannot read F3')
    rec = {'label': label, 't': round(time.monotonic() - st['start'], 2), 'xyz': pos, 'angle': ang, 'dimensionRow': dim, 'fps': route_fps.fps(rgb[:80, :320])}
    if keep:
        f = 'f3-%03d-%s.png' % (len(obs), label); im.save(out / f); rec['f3Image'] = f
    obs.append(rec); write(out / 'positions.json', obs)
    if rec['fps'] is not None: fpsrec.append(rec['fps'])
    f3(False)
    return rec
def turn(yaw, pitch, rec):
    dyaw = (yaw - rec['angle'][0] + 180) % 360 - 180
    dx = round(max(-470, min(470, dyaw / .15))); dy = round(max(-250, min(250, (pitch - rec['angle'][1]) / .15)))
    guard_ok(); x('mousemove_relative', '--', str(dx), str(dy)); time.sleep(.3)
def aim(point, label, tries=6, keep=False):
    for _ in range(tries):
        o = observe(label); px, py, pz = o['xyz']; dx, dz = point[0] - px, point[2] - pz
        yaw = math.degrees(math.atan2(-dx, dz)); pitch = math.degrees(math.atan2(py + 1.62 - point[1], math.hypot(dx, dz)))
        if abs((yaw - o['angle'][0] + 180) % 360 - 180) < .3 and abs(pitch - o['angle'][1]) < .3:
            return observe(label, keep=True) if keep else o
        turn(yaw, pitch, o)
    return observe(label + '-final', keep=keep)
def walk_to(target, label, tol, leash=None, iters=16):
    """Hold W toward target (feet xz). leash=(cx,cz,r): abort if the player strays farther than r from the arrival point."""
    for _ in range(iters):
        o = observe(label); px, py, pz = o['xyz']; dx, dz = target[0] - px, target[1] - pz; d = math.hypot(dx, dz)
        if leash and math.hypot(px - leash[0], pz - leash[1]) > leash[2]: raise RuntimeError('left leash at %s' % (o['xyz'],))
        if d < tol: return o
        heading = math.degrees(math.atan2(-dx, dz)); err = (heading - o['angle'][0] + 180) % 360 - 180
        turn(heading, 6.0, o)
        if abs(err) > 65: continue
        guard_ok(); x('keydown', 'w')
        try: time.sleep(max(.12, min(d, 1.5) / 4.317 * .62))
        finally: x('keyup', 'w')
        time.sleep(.5)
    raise RuntimeError('walk stalled before %s: %s' % (label, obs[-1]))
def wait_dim(want, timeout, label):
    """Stand still with F3 open (no key spam) until the F3 dimension row shows `want`."""
    f3(True); end = time.monotonic() + timeout; last = None
    while time.monotonic() < end:
        guard_ok(); rgb = np.asarray(grab()); pos, ang, dim = read(rgb)
        last = (pos, dim)
        if dim and want in dim and pos: return time.monotonic()
        time.sleep(1.0)
    grab().save(out / ('timeout-%s.png' % label)); raise RuntimeError('no %s within %ds, last=%s' % (want, timeout, last))
def shot(name, still=.8):
    f3(False); hide_hud(True); time.sleep(still)
    p = out / (name + '.png'); grab().save(p); shots[name] = sha(p)
    before = set((game / 'screenshots').glob('*.png')); key('F2'); new = set()
    for _ in range(60):
        new = set((game / 'screenshots').glob('*.png')) - before
        if new: break
        time.sleep(.1)
    if len(new) == 1:
        src = new.pop(); last = -1
        for _ in range(60):
            s = src.stat().st_size
            if s > 0 and s == last: break
            last = s; time.sleep(.2)
        shutil.copy2(src, out / (name + '-F2.png')); shots[name + '-F2'] = sha(out / (name + '-F2.png'))
    hide_hud(False)

TORCH_WARM, TORCH_SOUL = (-4.0, -58.55, 10.0), (6.0, -58.55, 10.0)
WIDE = (1.0, -58.7, 10.5)
def still_set(tag):
    aim(WIDE, tag + '-wide'); shot(tag + '-wide')
    aim(TORCH_WARM, tag + '-warm'); shot(tag + '-warm')
    aim(TORCH_SOUL, tag + '-soul'); shot(tag + '-soul')

results, failure = {}, None
video = vlog = None
with logpath.open('xb') as stream:
    proc = subprocess.Popen(cmd, cwd=game, env=env, stdout=stream, stderr=stream, start_new_session=True)
    st['proc'] = proc
    try:
        dl = time.monotonic() + 600
        while 'logged in with entity id' not in log():
            assert proc.poll() is None and time.monotonic() < dl, 'never joined'; time.sleep(.5)
        t_join = time.monotonic()
        assert 'OpenGL Renderer: NVIDIA GeForce RTX 3080 Ti' in log(), 'not NVIDIA'
        assert 'Using shaderpack: ' + pack.name in log()
        dl = time.monotonic() + 1200
        while 'contact bridge initialized' not in log():
            assert proc.poll() is None and time.monotonic() < dl and 'disabling shaders' not in log().lower(), 'pipeline'; time.sleep(.6)
        results['pipelineSecondsAfterJoin'] = round(time.monotonic() - t_join, 1)
        time.sleep(8)
        ids = x('search', '--all', '--onlyvisible', '--pid', str(proc.pid), '--name', 'Minecraft').split()
        assert len(ids) == 1
        st['wid'] = ids[0]; x('windowfocus', '--sync', st['wid']); guard_ok(); st['start'] = time.monotonic()
        stage('window ok pipeline=%ss' % results['pipelineSecondsAfterJoin'])
        if not args.no_video:
            vlog = (out / 'video.log').open('xb')
            video = subprocess.Popen(['ffmpeg', '-v', 'error', '-n', '-f', 'x11grab', '-framerate', '20', '-window_id', st['wid'], '-i', display, '-c:v', 'libx264', '-preset', 'veryfast',
                                      '-crf', '22', '-threads', '2', '-pix_fmt', 'yuv420p', str(out / 'journey.mkv')], stdin=subprocess.PIPE, stdout=vlog, stderr=vlog, env=env)
        log_join_end = len(log())
        results['spawn'] = observe('overworld-spawn', keep=True)
        stage('overworld spawn %s dim=%s' % (results['spawn']['xyz'], results['spawn']['dimensionRow']))
        still_set('A-overworld-before')
        pre_pose = observe('overworld-pre-pose', keep=True); results['prePose'] = pre_pose
        # ---- trip 1: Overworld -> Nether (walk into the lit portal, stand in it) ----
        log_mark = len(log())
        results['walkToPortal'] = walk_to((1.0, -2.5), 'to-portal', .35)
        events.append({'event': 'in portal', 'xyz': obs[-1]['xyz']}); t_in = time.monotonic()
        wait_dim('the_nether', 60, 'nether'); results['portalSecondsToNether'] = round(time.monotonic() - t_in, 1)
        time.sleep(2.5)
        results['netherArrival'] = observe('nether-arrival', keep=True)
        stage('nether arrival %s dim=%s' % (results['netherArrival']['xyz'], results['netherArrival']['dimensionRow']))
        na = results['netherArrival']; ax, _, az = na['xyz']
        # step out ~2 blocks along the facing direction (leashed 6), photograph, step back in
        fy = math.radians(na['angle'][0]); out_pt = (ax - 2.2 * math.sin(fy), az + 2.2 * math.cos(fy))
        results['netherOut'] = walk_to(out_pt, 'nether-out', .45, leash=(ax, az, 6))
        time.sleep(1.5)
        results['netherStill'] = observe('nether-out-pose', keep=True)
        shot('N-nether-outside'); results['netherLog'] = log()[log_mark:]
        results['netherBack'] = walk_to((ax, az), 'nether-back', .35, leash=(ax, az, 6))
        t_in = time.monotonic()
        wait_dim('overworld', 60, 'overworld'); results['portalSecondsToOverworld'] = round(time.monotonic() - t_in, 1)
        time.sleep(2.5)
        results['overworldArrival'] = observe('overworld-return-arrival', keep=True)
        stage('overworld return %s dim=%s' % (results['overworldArrival']['xyz'], results['overworldArrival']['dimensionRow']))
        results['walkBack'] = walk_to((pre_pose['xyz'][0], pre_pose['xyz'][2]), 'walk-back', .3, iters=24)
        results['postPose'] = observe('overworld-post-pose', keep=True)
        still_set('B-overworld-after')
        results['end'] = observe('end', keep=True)
        results['poseDeltaBlocks'] = [round(a - b, 3) for a, b in zip(results['postPose']['xyz'], pre_pose['xyz'])]
    except Exception as exc:  # noqa: BLE001
        failure = '%s: %s' % (type(exc).__name__, exc); stage('FAILED: ' + failure)
        try:
            if st['wid'] and proc.poll() is None: grab().save(out / 'failure.png')
        except Exception: pass
    finally:
        if video and video.poll() is None:
            try: video.stdin.write(b'q\n'); video.stdin.flush(); video.wait(timeout=30)
            except Exception: video.kill()
        if vlog: vlog.close()
        if st['wid'] and proc.poll() is None: subprocess.run(['/tmp/aqualumen-wm-close', hex(int(st['wid']))], env=env, timeout=8)
        try: proc.wait(timeout=90)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGTERM)
            try: proc.wait(timeout=20)
            except subprocess.TimeoutExpired: os.killpg(proc.pid, signal.SIGKILL)
        xvfb.terminate()
        try: xvfb.wait(timeout=10)
        except subprocess.TimeoutExpired: xvfb.kill()

t = log(); clean = 'All dimensions are saved' in t
# ---- saved-world comparison against the pristine fixture ----
CELLS = [(xx, yy, zz) for xx in range(-7, 9) for yy in range(-61, -55) for zz in range(-6, 13)]
verify = {}
try:
    a, b = anvil.World(pristine), anvil.World(save)
    diff = {'%d,%d,%d' % c: [a.block(*c), b.block(*c)] for c in CELLS if a.block(*c) != b.block(*c)}
    key_cells = {k: [a.block(*c), b.block(*c)] for k, c in {'warmTorch': (-4, -59, 9), 'soulTorch': (6, -59, 9), 'warmWall': (-4, -59, 10), 'soulWall': (6, -59, 10), 'portalLow': (0, -60, -3), 'portalHigh': (1, -58, -3)}.items()}
    key_cells = {k: [a.block(*c), b.block(*c)] for k, c in {'warmTorch': (-4, -59, 9), 'soulTorch': (6, -59, 9), 'warmWall': (-4, -59, 10), 'soulWall': (6, -59, 10), 'portalLow': (0, -60, -3), 'portalHigh': (1, -58, -3)}.items()}
    nether = anvil.World(save, 'DIM-1/region')
    na = results.get('netherArrival', {}).get('xyz')
    portal_cells = []
    if na:
        for xx in range(int(na[0]) - 8, int(na[0]) + 9):
            for zz in range(int(na[2]) - 8, int(na[2]) + 9):
                for yy in range(int(na[1]) - 4, int(na[1]) + 6):
                    v = nether.block(xx, yy, zz)
                    if v and 'nether_portal' in v: portal_cells.append([xx, yy, zz, v])
    verify = {'windowCells': len(CELLS), 'changedCells': len(diff), 'changed': diff, 'keyCellsBeforeAfter': key_cells, 'netherPortalCellsNearArrival': portal_cells,
              'netherRegionFiles': sorted(p.name for p in (save / 'DIM-1/region').glob('*.mca')) if (save / 'DIM-1/region').is_dir() else []}
except Exception as exc:  # noqa: BLE001
    verify = {'error': '%s: %s' % (type(exc).__name__, exc)}
level = parse_nbt(gzip.decompress((save / 'level.dat').read_bytes()))['Data']
pf = sorted((save / 'playerdata').glob('*.dat'))
player = parse_nbt(gzip.decompress(pf[0].read_bytes())) if pf else None
interesting = [l for l in t.splitlines() if re.search(r'dimension|Iris|pipeline|Aqualumen|contact bridge|shaderpack|Nether|portal|Reload|reload', l, re.I)]
fpsv = fpsrec
record = {
    'label': args.label, 'client': 'Minecraft 1.21.1 Fabric + Iris (Lab clone, 3 normal production jars, no test mod): ' + ', '.join(sorted(g.lab.NORMAL_MODS)),
    'renderer': (re.findall(r'OpenGL Renderer: ([^\n]+)', t) or [None])[0], 'glVersion': (re.findall(r'OpenGL Version: ([^\n]+)', t) or [None])[0],
    'path': 'VirtualGL (user-local, VGL_DISPLAY=egl0 i.e. device 0) -> private Xvfb %s, %dx%d, maxFps 60, no strict FPS target' % (display, W, H),
    'pack': pack.name, 'packSha256': sha(pack), 'worldZip': world_zip.name, 'worldZipSha256': sha(world_zip), 'lockSharedWaitSeconds': lock_wait_s,
    'failure': failure, 'cleanExit': clean, 'results': results, 'events': events, 'screens': shots,
    'logErrors': [l for l in t.splitlines() if re.search(r'/(ERROR|FATAL)\]|Exception', l)][:20], 'logInteresting': interesting[:80],
    'displayedFps': {'samples': len(fpsv), 'min': min(fpsv) if fpsv else None, 'median': float(np.median(fpsv)) if fpsv else None, 'max': max(fpsv) if fpsv else None,
                     'note': 'F3 integer FPS at ~1 s intervals, private VGL display; NOT a performance measurement'},
    'savedWorldVerification': verify, 'savedLevel': {k: level.get(k) for k in ('Time', 'DayTime', 'GameType', 'allowCommands', 'Difficulty')},
    'savedPlayer': {'Pos': player['Pos'], 'Dimension': player.get('Dimension'), 'Rotation': player['Rotation']} if player else None,
    'inputs': 'AUTOMATED xdotool keyboard+mouse to the private Xvfb window only (PID/cwd/focus checked before every input); no commands, teleport, datapack or test mod during play',
    'originalsUnchanged': {'labFiles': all(sha(orig / n) == v for n, v in original.items()), 'mods': all(sha(orig / 'mods' / n) == v for n, v in mods.items()), 'labWorldTouched': tree() != lab_world_tree},
    'privateGameDir': str(game), 'display': display}
write(out / 'complete.json', record)
stage('done clean=%s failure=%s changed=%s' % (clean, failure, verify.get('changedCells')))
print(json.dumps({k: record[k] for k in ('renderer', 'cleanExit', 'failure')}, indent=1))
sys.exit(0 if (clean and not failure) else 1)
