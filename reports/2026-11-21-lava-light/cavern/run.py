"""Natural lava cavern, ordinary survival play on a PRIVATE Xvfb display (never :0/:1/$DISPLAY), NVIDIA via user-local VirtualGL.

  python3 -I run.py <label> <pack.zip> <world.zip> [--video] [--probe]

Real keyboard/mouse (xdotool) to the private display only. No commands, no datapack, no benchmark mod. Positions, facing and the targeted
block/fluid are read from the vanilla F3 overlay in the private window. After a clean quit the saved region files are diffed against the
same-seed terrain surveyed beforehand (before-window.json). No render lock (optical + game-state only); at most two private sessions.
"""
import argparse, fcntl, gzip, hashlib, json, math, os, re, shutil, signal, string, subprocess, sys, tempfile, time
from pathlib import Path
from zipfile import ZipFile

import numpy as np
from PIL import Image

here = Path(__file__).resolve().parent
root = here.parents[2]
sys.path.insert(0, str(root / 'reports/2026-11-21-rain-eaves/journey'))
sys.path.insert(0, str(root / 'reports/2026-11-21-rain-eaves/fixture'))
sys.path.insert(0, str(root / 'reports/2026-11-21-door-light/playable'))
sys.path.insert(0, str(root / 'tools'))
import hud            # noqa: E402
import route_fps      # noqa: E402
import anvil          # noqa: E402
import ground_shadow_lab as g  # noqa: E402  (paths + option editing helpers only)
from validate_world import parse_nbt  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('label'); ap.add_argument('pack', type=Path); ap.add_argument('world', type=Path)
ap.add_argument('--video', action='store_true'); ap.add_argument('--probe', action='store_true', help='stop after the shelf walk + torch')
ap.add_argument('--no-cache-seed', action='store_true')
ap.add_argument('--shelf-route', action='store_true', help='walk to the verified shelf when the fixed camera reaches at least 12 FPS')
ap.add_argument('--stay-at-spawn', action='store_true', help='never walk; also chosen automatically when the first F3 FPS is below 20')
ap.add_argument('--cache-from', action='append', default=[], help='extra driver-cache dirs (copied, never written) merged into the private cache')
ap.add_argument('--pipeline-timeout', type=int, default=1800)
ap.add_argument('--compiler-mod', type=Path, help='optional verified area-light compiler for this private client')
ap.add_argument('--mine-face', action='store_true', help='partly mine the lit tuff and release before it breaks')
ap.add_argument('--revisit', type=Path, help='resume this recorded private gameplay checkpoint and relight the saved shelf')
ap.add_argument('--profile-spot', action='store_true', help='sample the fixed natural spawn and exit before any changes')
ap.add_argument('--timing-mod', type=Path, help='private Iris GPU timestamps for a fixed-camera profile')
args = ap.parse_args()
assert not args.timing_mod or args.profile_spot
assert re.fullmatch('[a-z0-9-]+', args.label)
site = json.loads((here / 'site.json').read_text())
WORLD = 'Aqualumen-Lava-Cavern'
W, H = 1600, 900
DISPLAY_MIN = 240
PLAYER, PLAYER_UUID = 'Cavewalker', '00000000000040008000000000000309'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
write = lambda p, v: Path(p).write_text(json.dumps(v, indent=2, ensure_ascii=False) + '\n')
out = here / args.label
out.mkdir()
pack, world = args.pack.resolve(strict=True), args.world.resolve(strict=True)
assert pack.name.endswith('.zip') and not pack.is_symlink() and 'dist' not in pack.parts[-2:-1]


def note(text):
    with (here / 'progress.txt').open('a') as f:
        f.write('%s %s\n' % (time.strftime('%Y-%m-%dT%H:%M:%S%z'), text))


# ---- refuse to start a 3rd private session (user's own Prism client is never counted/touched) ----
def private_sessions():
    n = []
    for p in Path('/proc').iterdir():
        if p.name.isdigit():
            try:
                cl = (p / 'cmdline').read_bytes().split(b'\0')
            except OSError:
                continue
            if b'net.fabricmc.loader.impl.launch.knot.KnotClient' in cl and any(c.startswith(b'/tmp/aql-') for c in cl):
                n.append(int(p.name))
    return n
t0 = time.monotonic()
while len(private_sessions()) >= 2:
    assert time.monotonic() - t0 < 1500, 'two private sessions still running'
    time.sleep(10)

orig = g.GAME.resolve()
# Multiple visual observations may share the GPU. A frame-time recording acquires the exclusive lock.
timing_lock = open('/tmp/aql-render21-%d.lock' % os.getuid(), 'a+b')
fcntl.flock(timing_lock, fcntl.LOCK_EX if args.profile_spot else fcntl.LOCK_SH)
guards = ['config/iris.properties', 'options.txt', 'config/sodium-options.json']
original = {n: sha(orig / n) for n in guards}
mods = {n: sha(orig / 'mods' / n) for n in g.lab.NORMAL_MODS}
lab_world = orig / 'saves' / g.lab.WORLD
lab_world_tree = {str(p.relative_to(lab_world)): p.stat().st_mtime_ns for p in lab_world.rglob('*') if p.is_file() and p.name != 'session.lock'} if lab_world.exists() else {}

base = Path(tempfile.mkdtemp(prefix='aql-cavern-'))
game = base / 'minecraft'
for d in ('saves', 'mods', 'config', 'shaderpacks', 'screenshots'):
    (game / d).mkdir(parents=True)
for n in mods:
    shutil.copyfile(orig / 'mods' / n, game / 'mods' / n)
assert {p.name for p in (game / 'mods').iterdir()} == g.lab.NORMAL_MODS
compiler_digest = None
if args.compiler_mod:
    companion = args.compiler_mod.resolve(strict=True)
    assert companion.name in ('aqualumen-lighting-compiler-0.2.1.jar','aqualumen-lighting-compiler-0.3.0.jar')
    compiler_digest = sha(Path(shutil.copy2(companion, game / 'mods')))
if args.timing_mod:
    profiler = args.timing_mod.resolve(strict=True)
    assert profiler.name == 'aqualumen-private-gpu-clock.jar' and base.name.startswith('aql-cavern-')
    shutil.copy2(profiler, game / 'mods')
shutil.copyfile(pack, game / 'shaderpacks' / pack.name)
for n in ('config/iris.properties', 'config/sodium-options.json'):
    shutil.copyfile(orig / n, game / n)
iris = game / 'config/iris.properties'
iris.write_bytes(g.lab.replace_values(iris.read_bytes(), {'shaderPack': pack.name}, '='))
opt = dict(g.lab.OPTIONS, fullscreen='false', maxFps='60', enableVsync='false', overrideWidth=str(W), overrideHeight=str(H), rawMouseInput='false',
           mouseSensitivity='0.5', guiScale='2', lang='en_us', forceUnicodeFont='false', pauseOnLostFocus='false', fov='0.0', fovEffectScale='0.0',
           bobView='false', reducedDebugInfo='false', autoJump='true', screenEffectScale='0.0', chatVisibility='2')
(game / 'options.txt').write_bytes(g.lab.replace_values((orig / 'options.txt').read_bytes(), opt, ':'))
checkpoint = None
archive = world
if args.revisit:
    receipt_path = args.revisit.resolve(strict=True)
    assert receipt_path.parent.parent == here and receipt_path.name == 'checkpoint.json'
    checkpoint = json.loads(receipt_path.read_text())
    last_run = json.loads((receipt_path.parent / 'complete.json').read_text())
    assert last_run['cleanExit'] and not last_run['failure'] and last_run['worldZipSha256'] == sha(world)
    assert last_run['packSha256'] == checkpoint['packSha256'] == sha(pack)
    assert checkpoint['sourceWorld'] == WORLD and checkpoint['file'] == 'survival-checkpoint.zip'
    archive = receipt_path.parent / checkpoint['file']
    assert sha(archive) == checkpoint['sha256']
with ZipFile(archive) as z:
    if checkpoint:
        assert all(Path(n).parts[0] == WORLD and '..' not in Path(n).parts for n in z.namelist())
        assert WORLD + '/level.dat' in z.namelist()
    else:
        assert z.namelist() == [WORLD + '/level.dat']
    z.extractall(game / 'saves')
save = game / 'saves' / WORLD
lv0 = parse_nbt(gzip.decompress((save / 'level.dat').read_bytes()))['Data']
assert lv0['WorldGenSettings']['seed'] == 308060 and lv0['allowCommands'] == 0 and lv0['GameType'] == 0
runtime = json.loads((root / 'reports/2026-11-20-underwater-refinement/local-launch.json').read_text())
vgl = Path((root / 'reports/2026-11-21-lava-light/runtime-v190/vgl-dir.txt').read_text().strip()) / 'x/usr/lib'
assert (vgl / 'libvglfaker.so').is_file() and (vgl / 'libdlfaker.so').is_file()
glcache = base / 'glcache'
src_cache = Path.home() / '.cache/aqualumen-lab-shader-driver'
if src_cache.is_dir() and not args.no_cache_seed:
    shutil.copytree(src_cache, glcache)   # seeded read-only copy; the shared driver cache is never written
else:
    glcache.mkdir()
for extra in args.cache_from:
    extra = Path(extra)
    assert extra.is_dir()
    for f in extra.rglob('*'):
        if f.is_file():
            dst = glcache / f.relative_to(extra)
            dst.parent.mkdir(parents=True, exist_ok=True)
            if not dst.exists():
                shutil.copy2(f, dst)


def start_xvfb():
    for n in range(DISPLAY_MIN, DISPLAY_MIN + 40):
        if Path('/tmp/.X11-unix/X%d' % n).exists() or Path('/tmp/.X%d-lock' % n).exists():
            continue
        log = (base / 'xvfb.log').open('wb')
        proc = subprocess.Popen(['Xvfb', ':%d' % n, '-screen', '0', '%dx%dx24' % (W, H), '+extension', 'GLX', '+extension', 'RENDER', '-nolisten', 'tcp', '-noreset'],
                                stdout=log, stderr=log, start_new_session=True)
        for _ in range(100):
            if Path('/tmp/.X11-unix/X%d' % n).exists() or proc.poll() is not None:
                break
            time.sleep(.1)
        if proc.poll() is None and Path('/tmp/.X11-unix/X%d' % n).exists():
            return proc, ':%d' % n
    raise RuntimeError('no free private display')


xvfb, display = start_xvfb()
assert int(display[1:]) >= DISPLAY_MIN and display != os.environ.get('DISPLAY')
env = {k: v for k, v in os.environ.items() if k not in ('WAYLAND_DISPLAY', 'XAUTHORITY', 'DISPLAY', 'XDG_SESSION_TYPE', 'LD_PRELOAD', 'JAVA_TOOL_OPTIONS', 'JDK_JAVA_OPTIONS')}
env.update(DISPLAY=display, ALSOFT_DRIVERS='null', __GL_SHADER_DISK_CACHE_PATH=str(glcache), XDG_CACHE_HOME=str(base / 'cache'),
           LD_PRELOAD='%s:%s' % (vgl / 'libdlfaker.so', vgl / 'libvglfaker.so'), VGL_DISPLAY='egl0', VGL_LOGO='0', VGL_COMPRESS='0', VGL_SPOIL='0', VGL_VERBOSE='1')
cmd = [runtime['java'], '-Xms512m', '-Xmx2600m', '-XX:ActiveProcessorCount=4', '-Dorg.lwjgl.openal.libname=libopenal.so.1', '-cp', ':'.join(runtime['cp']),
       'net.fabricmc.loader.impl.launch.knot.KnotClient', '--username', PLAYER, '--version', '1.21.1', '--gameDir', str(game), '--assetsDir', str(orig.parents[2] / 'assets'),
       '--assetIndex', '17', '--uuid', PLAYER_UUID, '--accessToken', '0', '--userType', 'legacy', '--width', str(W), '--height', str(H), '--quickPlaySingleplayer', WORLD]
logpath = out / 'client.log'
obs, actions, fpsrec, shots = [], [], [], {}
st = {'start': None, 'wid': None, 'debug': False, 'proc': None, 'hud': True}
(out / 'private-game.txt').write_text('%s\n%s\n' % (game, display))
note('%s: 起動準備完了 display=%s game=%s pack=%s world=%s' % (args.label, display, game, pack.name, sha(world)[:12]))


def x(*a, timeout=6):
    return subprocess.check_output(['xdotool', *a], env=env, timeout=timeout, text=True, stderr=subprocess.DEVNULL).strip()


def log():
    return logpath.read_text(errors='replace')


def guard_ok():
    p = st['proc']
    assert p.poll() is None
    assert Path('/proc', str(p.pid), 'cwd').resolve() == game.resolve()
    assert x('getwindowpid', st['wid']) == str(p.pid) and x('getwindowfocus') == st['wid']


def key(k):
    guard_ok(); x('key', k)


def click(button, wait=.6):
    guard_ok(); x('click', button); time.sleep(wait)


def f3(active):
    if st['debug'] != active:
        key('F3'); time.sleep(.5 if active else .3); st['debug'] = active


def hide_hud(hidden):
    if st['hud'] == hidden:   # st['hud'] True = HUD visible
        key('F1'); time.sleep(.4); st['hud'] = not hidden


def grab():
    d = subprocess.check_output(['ffmpeg', '-v', 'error', '-f', 'x11grab', '-window_id', st['wid'], '-i', display, '-frames:v', '1', '-threads', '1',
                                 '-pix_fmt', 'bgr0', '-f', 'rawvideo', 'pipe:1'], env=env, timeout=8)
    assert len(d) == W * H * 4
    return Image.frombytes('RGB', (W, H), d, 'raw', 'BGRX')


def target_line(rgb, label, scale=2):
    """Right-aligned 'Targeted Block:' / 'Targeted Fluid:' panel; returns the x,y,z triple or None."""
    glyphs = hud.font()
    lab = np.hstack([glyphs[c] for c in label])
    bits = (rgb[scale // 2::scale, scale // 2::scale, :3] == 221).all(axis=2)
    bits = bits[:, bits.shape[1] // 2:]
    powers = 2 ** np.arange(8, dtype=np.uint8)
    mask = np.lib.stride_tricks.sliding_window_view(bits, 8, axis=0) @ powers
    needle = (lab.T @ powers).tobytes()
    for y, enc in enumerate(mask):
        xx = enc.tobytes().find(needle)
        if xx < 0:
            continue
        xx += len(needle)
        pos = ''
        for _ in range(35):
            for c in '0123456789-, ':
                gl = glyphs[c]
                if np.array_equal(bits[y:y + 8, xx:xx + gl.shape[1]], gl):
                    pos += c; xx += gl.shape[1]; break
            else:
                break
        v = re.findall(r'-?[0-9]+', pos)
        if len(v) == 3:
            return tuple(map(int, v))
    return None


def observe(label, keep=False):
    f3(True)
    for _ in range(8):
        im = grab(); rgb = np.asarray(im)
        pos = hud.position(rgb)
        ang = hud.row_text(rgb, 'Facing: ', string.ascii_letters + '0123456789-.()/ ')
        m = re.search(r'\((-?[0-9.]+) / (-?[0-9.]+)\)', ang or '')
        if pos and m:
            break
        time.sleep(.3)
    else:
        im.save(out / 'unreadable-hud.png'); raise RuntimeError('cannot read F3')
    rec = {'label': label, 't': round(time.monotonic() - st['start'], 2), 'xyz': pos, 'angle': list(map(float, m.groups())),
           'targetBlock': target_line(rgb, 'Targeted Block: '), 'targetFluid': target_line(rgb, 'Targeted Fluid: '), 'fps': route_fps.fps(rgb[:80, :320])}
    if keep:
        f = 'f3-%03d-%s.png' % (len(obs), label); im.save(out / f); rec['f3Image'] = f
    obs.append(rec); write(out / 'positions.json', obs)
    if rec['fps'] is not None:
        fpsrec.append({'label': label, 'fps': rec['fps'], 't': rec['t']})
    f3(False)
    return rec


def turn(yaw, pitch, rec):
    dyaw = (yaw - rec['angle'][0] + 180) % 360 - 180
    dx = round(max(-470, min(470, dyaw / .15))); dy = round(max(-250, min(250, (pitch - rec['angle'][1]) / .15)))
    guard_ok(); x('mousemove_relative', '--', str(dx), str(dy)); time.sleep(.3)


def aim(point, label, want_block=None, want_fluid='any', tries=6, keep=False):
    """Aim the crosshair at a world point; success = angle error < .3 deg and the F3 target(s) as wanted."""
    for _ in range(tries):
        o = observe(label)
        px, py, pz = o['xyz']
        dx, dz = point[0] - px, point[2] - pz
        yaw = math.degrees(math.atan2(-dx, dz)); pitch = math.degrees(math.atan2(py + 1.62 - point[1], math.hypot(dx, dz)))
        d = ((yaw - o['angle'][0] + 180) % 360 - 180, pitch - o['angle'][1])
        if abs(d[0]) < .3 and abs(d[1]) < .3 and (want_block is None or o['targetBlock'] == tuple(want_block)) and (want_fluid == 'any' or o['targetFluid'] == (tuple(want_fluid) if want_fluid else None)):
            return observe(label, keep=True) if keep else o
        turn(yaw, pitch, o)
    return observe(label + '-final', keep=True)


def goto(wp, label, tol=.3):
    tx, ty, tz = wp
    for _ in range(14):
        o = observe(label)
        px, py, pz = o['xyz']
        if py < -53.6 or pz < 374.9:
            raise RuntimeError('unsafe position, stopped before the lava edge: %s' % (o['xyz'],))
        dx, dz = tx - px, tz - pz; d = math.hypot(dx, dz)
        on_shelf = math.floor(px)==543 and math.floor(pz)==375 and abs(py-ty)<.09
        if on_shelf and d < .56:
            return o
        if d < tol and abs(py-ty)<.09:
            return o
        heading = math.degrees(math.atan2(-dx, dz))
        error = (heading - o['angle'][0] + 180) % 360 - 180
        turn(heading, 12.0, o)
        if abs(error) > 65:
            continue
        guard_ok(); x('keydown', 'w')
        try:
            time.sleep(min(d, 1.5) / 4.317 * .62)
        finally:
            x('keyup', 'w')
        time.sleep(.5)
    raise RuntimeError('walk stalled before %s: %s' % (label, obs[-1]))


def retain_f2(name, before):
    images = game / 'screenshots'
    deadline = time.monotonic() + 7
    while time.monotonic() < deadline:
        new = set(images.glob('*.png')) - before
        if len(new) == 1:
            src = next(iter(new))
            if src.stat().st_size > 0 and src.read_bytes()[-8:-4] == b'IEND':
                dest = out / (name + '-ingame.png')
                shutil.copy2(src, dest)
                shots[name + '-ingame'] = sha(dest)
                return
        time.sleep(.1)
    raise RuntimeError('no unique complete F2 screenshot for ' + name)


def shot(name, still=.8, f2=False):
    f3(False); hide_hud(True); time.sleep(still)
    p = out / (name + '.png'); grab().save(p); shots[name] = sha(p)
    if f2:
        before = set((game / 'screenshots').glob('*.png'))
        key('F2')
        retain_f2(name, before)
    hide_hud(False)
    return name + '.png'


def stage(msg):
    note('%s: %s' % (args.label, msg))


VIEW_BOTH = (543.5, -54.1, 371.5)   # yaw ~180: soul torch at the right edge, water flow at the left edge
VIEW_WATER = (541.0, -54.5, 373.0)
results, failure, pipeline_s = {}, None, None
video = vlog = None
proc = None
with logpath.open('xb') as stream:
    proc = subprocess.Popen(cmd, cwd=game, env=env, stdout=stream, stderr=stream, start_new_session=True)
    st['proc'] = proc
    try:
        dl = time.monotonic() + 600
        while 'logged in with entity id' not in log():
            assert proc.poll() is None and time.monotonic() < dl, 'never joined'
            time.sleep(.5)
        t_join = time.monotonic()
        stage('ワールドに参加(自前チャンク生成)')
        assert 'OpenGL Renderer: NVIDIA GeForce RTX 3080 Ti' in log(), 'not NVIDIA'
        assert 'Using shaderpack: ' + pack.name in log()
        dl = time.monotonic() + args.pipeline_timeout
        while 'contact bridge initialized' not in log():
            assert proc.poll() is None and time.monotonic() < dl and 'disabling shaders' not in log().lower(), 'pipeline'
            time.sleep(.6)
        pipeline_s = round(time.monotonic() - t_join, 1)
        time.sleep(8)
        ids = x('search', '--all', '--onlyvisible', '--pid', str(proc.pid), '--name', 'Minecraft').split()
        assert len(ids) == 1
        st['wid'] = ids[0]; x('windowfocus', '--sync', st['wid']); guard_ok()
        st['start'] = time.monotonic()
        stage('ウィンドウ確認 renderer=%s pipeline=%.1fs' % (re.search(r'OpenGL Renderer: ([^\n]+)', log()).group(1).strip(), pipeline_s))
        if args.video:
            vlog = (out / 'video.log').open('xb')
            video = subprocess.Popen(['ffmpeg', '-v', 'error', '-n', '-f', 'x11grab', '-framerate', '24', '-window_id', st['wid'], '-i', display, '-c:v', 'libx264',
                                      '-preset', 'veryfast', '-crf', '20', '-threads', '3', '-pix_fmt', 'yuv420p', str(out / 'journey.mkv')],
                                     stdin=subprocess.PIPE, stdout=vlog, stderr=vlog, env=env)
        sp = site['spawn']
        first = observe('spawn', keep=True)
        results['spawnObservation'] = first
        expected = checkpoint['player'] if checkpoint else sp['feet']
        assert math.dist(first['xyz'], expected) < .1, first
        results['spawnShot'] = shot('01-spawn-before', 1.0, f2=True)
        stage('スポーン確認 xyz=%s angle=%s' % (first['xyz'], first['angle']))
        if checkpoint:
            assert lv0['Time'] == checkpoint['time'] and checkpoint['initialSavedChanges'] == {'lava->obsidian':25,'air->soul_torch':1}
            torch = (544, -53, 374)
            support = (544, -54, 374)
            aim(VIEW_BOTH, 'returned-pool')
            shot('reopened', still=2., f2=True)
            key('9')
            face = (544.5, -52.4, 374.5)
            found = aim(face,'saved-torch', want_block=torch, keep=True)
            assert found['targetBlock'] == torch
            click('1',1.)
            base_point = (544.2, -53., 374.2)
            cleared = aim(base_point, 'empty-support', want_block=support, keep=True)
            assert cleared['targetBlock'] == support
            aim(VIEW_BOTH, 'removed-light-view')
            shot('torch-removed', still=2., f2=True)
            key('3')
            assert aim(base_point, 'relight-support', want_block=support)['targetBlock'] == support
            click('3',1.)
            assert aim(face,'relit', want_block=torch, keep=True)['targetBlock'] == torch
            actions.extend([{'action':'remove saved soul torch','cell':torch},{'action':'relight the same shelf','cell':torch}])
            write(out / 'actions.json', actions)
            key('9')
            aim(VIEW_BOTH, 'relit-pool')
            shot('torch-restored', still=2., f2=True)
            length = time.monotonic() - st['start']
        elif args.profile_spot:
            for sample in range(8):
                time.sleep(1.1)
                observe('fixed-%02d' % sample)
            length = time.monotonic() - st['start']
        else:
            # exact BEFORE reading: crosshair on the shallow shore lava cell. Block ray ignores fluid -> deepslate floor; fluid ray -> lava cell.
            pour = site['pourCell']
            o = aim((pour[0] + .5, pour[1] + .0, pour[2] + .5), 'lava-before', want_block=(pour[0], pour[1] - 1, pour[2]), want_fluid=tuple(pour), keep=True)
            results['lavaBefore'] = o
            stage('溶岩の事前確認 F3 targetBlock=%s targetFluid=%s' % (o['targetBlock'], o['targetFluid']))
            # Slow frames (<20 fps) quantise key presses to whole frames and a walk can overshoot toward the lava: then do everything from the spawn.
            stay = args.stay_at_spawn or (first['fps'] or 0) < (12 if args.shelf_route else 20)
            results['stayAtSpawn'] = stay; results['spawnFps'] = first['fps']
            if stay:
                stage('歩行せずスポーン位置から操作 (fps=%s, 指定=%s)' % (first['fps'], args.stay_at_spawn))
                results['shelfObservation'] = first
                torch = (544, -52, 375); tpoint = (544.5, -52.0, 375.5); tread = (544.5, -51.7, 375.5)
            else:
                # step onto the lower tuff shelf
                sh = site['shelf']['feet']
                results['shelfObservation'] = goto(sh, 'to-shelf')
                stage('足場へ移動 xyz=%s' % (results['shelfObservation']['xyz'],))
                # soul torch on tuff (544,-54,374) top face -> cell (544,-53,374)
                torch = (544, -53, 374); tpoint = (torch[0] + .2, torch[1] + .0, torch[2] + .2); tread = (torch[0] + .5, torch[1] + .6, torch[2] + .5)
            o = aim(VIEW_BOTH, 'pool-view')
            results['shelfBeforeShot'] = shot('02-shelf-lava-before', 1.0, f2=True)
            key('3')
            o = aim(tpoint, 'aim-torch', want_block=(torch[0], torch[1] - 1, torch[2]), want_fluid='any')
            assert o['targetBlock'] == (torch[0], torch[1] - 1, torch[2]), o
            click('3', 1.0)
            o = aim(tread, 'torch-placed', want_block=torch, keep=True)
            assert o['targetBlock'] == torch, o
            actions.append({'action': 'place soul_torch', 'cell': list(torch), 'readback': o['targetBlock'], 'xyz': o['xyz'], 't': o['t']}); write(out / 'actions.json', actions)
            stage('ソウルトーチ設置 cell=%s' % (torch,))
            key('9')   # bare hand for photographs
            aim(VIEW_BOTH, 'pool-view-torch')
            results['torchShot'] = shot('03-soul-torch-lava', 1.5, f2=True)
            if args.mine_face:
                assert not stay
                rock = tuple(site['torchSupport'])
                pos = (rock[0] + .5, rock[1] + 1., rock[2] + .5)
                target = aim(pos, 'mining-target', want_block=rock, keep=True)
                assert target['targetBlock'] == rock
                shot('mining-before', f2=True)
                hide_hud(True)
                before = set((game / 'screenshots').glob('*.png'))
                # Release on the X input clock even if the screenshot writer stalls.
                guard_ok()
                try:
                    x('mousedown','1','sleep','2.6','key','F2','sleep','.25','mouseup','1')
                finally:
                    x('mouseup','1')
                retain_f2('mining-cracks', before)
                shot('mining-released', still=1., f2=True)
                target = observe('mining-cancelled', keep=True)
                assert target['targetBlock'] == rock
                actions.append({'action':'partly mine tuff with bare hand, release', 'cell':rock,
                                'heldSeconds':2.85, 'targetAfter':target['targetBlock']})
                write(out / 'actions.json', actions)
            if not args.probe and stay:
                # Slow-frame fallback: no walking, no flowing water. Take one NATURAL lava source with the empty bucket (liquid ray, reach 4.35 < 4.5).
                pour = (542, -55, 374)
                key('1')
                o = aim((pour[0] + .5, pour[1] + .5, pour[2] + .5), 'aim-lava-pickup', want_fluid=pour, tries=8, keep=True)
                assert o['targetFluid'] == pour, o
                results['lavaPickupBefore'] = o
                click('3', .4)
                t_pick = time.monotonic()
                actions.append({'action': 'pick up lava source (empty bucket)', 'cell': list(pour), 'readback': o['targetFluid'], 'xyz': o['xyz'], 't': o['t']}); write(out / 'actions.json', actions)
                stage('溶岩の天然ソースを回収 cell=%s' % (pour,))
                key('9')
                seq = []
                for i, when in enumerate((8, 14)):   # the 'Hot Stuff' advancement toast is gone by then
                    while time.monotonic() - t_pick < when:
                        time.sleep(.1)
                    aim(VIEW_BOTH, 'lava-pick-view-%d' % i)
                    seq.append(shot('04-lava-pickup-%d' % i, .2))
                results['pickupSeq'] = seq
                results['lavaPickupAfter'] = aim((pour[0] + .5, pour[1] + .5, pour[2] + .5), 'lava-after-pickup', keep=True)
                aim(VIEW_BOTH, 'after-view')
                results['afterShot'] = shot('05-lava-source-removed', 1.5, f2=True)
            elif not args.probe:
                # water source on tuff (542,-55,375) top face -> cell (542,-54,375); flowing water falls on / beside the shore lava
                wcell = (542, -55, 374) if stay else (542, -54, 375)   # stay: pour straight onto the shallow shore lava; else on the tuff above it
                key('2')
                o = aim((wcell[0] + .5, wcell[1] + .0, wcell[2] + .5), 'aim-water', want_block=(wcell[0], wcell[1] - 1, wcell[2]), want_fluid='any')
                assert o['targetBlock'] == (wcell[0], wcell[1] - 1, wcell[2]), o
                results['preWaterObs'] = observe('pre-water', keep=True)
                click('3', .2)
                t_pour = time.monotonic()
                actions.append({'action': 'place water_bucket', 'cell': list(wcell), 'xyz': o['xyz'], 't': o['t']}); write(out / 'actions.json', actions)
                stage('水を設置 cell=%s' % (wcell,))
                key('9')
                seq = []
                for i, when in enumerate((3, 8, 16, 30)):
                    while time.monotonic() - t_pour < when:
                        time.sleep(.1)
                    aim(VIEW_BOTH, 'water-view-%d' % i)
                    seq.append(shot('04-water-flow-%d' % i, .2))
                results['waterSeq'] = seq
                o = aim((542.5, -54.9, 374.5), 'converted-cell', keep=True)
                results['pourCellAfterWater'] = o
                # retrieve the water with the empty bucket (SOURCE_ONLY ray)
                key('1')
                o = aim((wcell[0] + .5, wcell[1] + .3, wcell[2] + .5), 'aim-pickup', want_fluid=wcell, tries=8, keep=True)
                assert o['targetFluid'] == wcell, o
                click('3', .8)
                actions.append({'action': 'pick up water (empty bucket)', 'cell': list(wcell), 'readback': o['targetFluid'], 't': o['t']}); write(out / 'actions.json', actions)
                stage('水を回収')
                key('9')
                time.sleep(14)
                aim(VIEW_BOTH, 'after-view')
                results['afterShot'] = shot('05-obsidian-after', 1.5, f2=True)
                aim(VIEW_WATER, 'after-view-close')
                results['afterCloseShot'] = shot('06-obsidian-after-close', 1.0)
                results['afterObs'] = observe('after', keep=True)
            results['endObservation'] = observe('end', keep=True)
            length = time.monotonic() - st['start']
    except Exception as exc:  # noqa: BLE001
        failure = '%s: %s' % (type(exc).__name__, exc)
        stage('失敗: ' + failure)
        length = time.monotonic() - st['start'] if st['start'] else 0
        try:
            if st['wid'] and proc.poll() is None:
                grab().save(out / 'failure.png')
        except Exception:  # noqa: BLE001
            pass
    finally:
        if video and video.poll() is None:
            try:
                video.stdin.write(b'q\n'); video.stdin.flush(); video.wait(timeout=30)
            except Exception:  # noqa: BLE001
                video.kill()
        if vlog:
            vlog.close()
        if st['wid'] and proc.poll() is None:
            subprocess.run(['/tmp/aqualumen-wm-close', hex(int(st['wid']))], env=env, timeout=8)
        try:
            proc.wait(timeout=60)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
        xvfb.terminate()
        try:
            xvfb.wait(timeout=10)
        except subprocess.TimeoutExpired:
            xvfb.kill()

t = log()
clean = 'All dimensions are saved' in t
# ---- saved-world verification against the same-seed survey ----
verify = {}
try:
    wd = anvil.World(save)
    before = json.loads((here / 'before-window.json').read_text())
    diff, unavailable, flowing_lava = {}, 0, {}
    for k, v0 in before.items():
        xx, yy, zz = map(int, k.split(','))
        raw = wd.block(xx, yy, zz) or 'unavailable'
        v1 = raw.split(':')[-1].split('[')[0]
        if v1 == 'lava' and raw != 'minecraft:lava[level=0]':
            flowing_lava[k] = raw
        if v1 == 'unavailable':
            unavailable += 1
        if v1 != v0:
            diff[k] = [v0, v1]
    summary = {}
    for k, (a, b) in diff.items():
        summary['%s->%s' % (a, b)] = summary.get('%s->%s' % (a, b), 0) + 1
    lava_before = sum(1 for v in before.values() if v == 'lava')
    verify = {'windowCells': len(before), 'lavaCellsBefore': lava_before, 'changedCells': len(diff), 'changeSummary': summary, 'unavailableAfter': unavailable, 'lavaCellsNotLevel0After': flowing_lava, 'pourCellRaw': wd.block(542, -55, 374), 'rawKeyCells': {k: wd.block(*map(int, k.split(','))) for k in ('541,-55,374', '542,-55,373', '542,-55,374', '544,-53,374', '544,-52,375', '542,-54,375')},
              'changed': diff, 'torchBlock': (wd.block(544, -53, 374) or '?'), 'waterCell': (wd.block(542, -54, 375) or '?')}
except Exception as exc:  # noqa: BLE001
    verify = {'error': '%s: %s' % (type(exc).__name__, exc)}
level = parse_nbt(gzip.decompress((save / 'level.dat').read_bytes()))['Data']
pfiles = sorted((save / 'playerdata').glob('*.dat'))
player = parse_nbt(gzip.decompress(pfiles[0].read_bytes())) if pfiles else None
if player:
    inv = [(i['Slot'], i['id'], i['count']) for i in player.get('Inventory', [])]
else:
    inv = None
fpsv = [r['fps'] for r in fpsrec]
labwtree = {str(p.relative_to(lab_world)): p.stat().st_mtime_ns for p in lab_world.rglob('*') if p.is_file() and p.name != 'session.lock'} if lab_world.exists() else {}
record = {
    'label': args.label, 'renderer': (re.findall(r'OpenGL Renderer: ([^\n]+)', t) or [None])[0].strip() if re.findall(r'OpenGL Renderer: ([^\n]+)', t) else None,
    'glVersion': (re.findall(r'OpenGL Version: ([^\n]+)', t) or [None])[0], 'path': 'VirtualGL 3.1.5 (user-local, EGL egl0) -> private Xvfb %s; maxFps 60' % display,
    'pack': pack.name, 'packSha256': sha(pack), 'worldZip': world.name, 'worldZipSha256': sha(world), 'seedFromLevelDat': lv0['WorldGenSettings']['seed'],
    'pipelineSecondsAfterJoin': pipeline_s, 'seconds': round(length, 1), 'video': bool(args.video), 'failure': failure, 'cleanExit': clean,
    'logErrors': [l for l in t.splitlines() if re.search(r'/(ERROR|FATAL)\]|Exception', l)][:20], 'results': results, 'actions': actions,
    'screens': shots, 'displayedFps': {'samples': len(fpsv), 'min': min(fpsv) if fpsv else None, 'median': float(np.median(fpsv)) if fpsv else None, 'max': max(fpsv) if fpsv else None,
                                       'note': 'F3 integer FPS, private VGL display, window 1600x900, 12 chunks, maxFps 60 cap: NOT a performance measurement'},
    'savedWorldVerification': verify, 'savedLevel': {k: level[k] for k in ('Time', 'DayTime', 'GameType', 'allowCommands', 'Difficulty')},
    'savedPlayer': {'Pos': player['Pos'], 'Rotation': player['Rotation'], 'inventory': inv} if player else None,
    'inputs': 'xdotool keyboard+mouse to the private Xvfb window only (PID/cwd/focus checked before every input); no commands, datapacks, benchmark mod; F3 only in the private window',
    'originalsUnchanged': {'labFiles': all(sha(orig / n) == v for n, v in original.items()), 'mods': all(sha(orig / 'mods' / n) == v for n, v in mods.items()),
                           'labWorldTouched': labwtree != lab_world_tree}, 'privateGameDir': str(game), 'display': display}
record['compilerModSha256'] = compiler_digest
record['fixedCameraProfile'] = args.profile_spot
if checkpoint:
    record['reopenedCheckpoint'] = checkpoint
record['gpuClockSha256'] = sha(args.timing_mod) if args.timing_mod else None
write(out / 'complete.json', record)
stage('終了 clean=%s failure=%s changed=%s' % (clean, failure, verify.get('changeSummary')))
print(json.dumps({k: record[k] for k in ('renderer', 'cleanExit', 'failure', 'savedWorldVerification')}, indent=1)[:3000])
sys.exit(0 if (clean and not failure) else 1)
