"""Guarded actual-game runner for the mixed torch/lava/pillar study on a PRIVATE display.

    python3 run.py <pack.zip> <label> [--backend vgl|llvmpipe] [--stages a,b,c | --set core|all] [--dry-run]

* Starts its OWN Xvfb (display number >= 171, never :0/:1/$DISPLAY) and never talks to any other display.
* backend vgl: NVIDIA RTX 3080 Ti through user-local VirtualGL 3.1.5 (libvglfaker, EGL device egl0) -> Xvfb.
  backend llvmpipe: CPU Mesa software GL (smoke only; label results as software).
* Exact private clone of the guarded V2 world (UUID/seed checked), private game dir, only the three normal mods,
  Lab options/Iris/Sodium configs copied (read only), original Lab/world/config/packs verified unchanged.
* Screenshots: game-side F2 (framebuffer read by the game) AND x11grab of the private window, per stage,
  only accepted when READY ... STILL are logged with no BEGIN/DRIFT/FAIL in between.
Progress is appended to ../progress.txt-style file (progress.txt next to this script); result.json is merged per label.
"""
from pathlib import Path
import argparse
import fcntl
import gzip
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time

here = Path(__file__).resolve().parent
root = here.parents[2]
sys.path.insert(0, str(here))
sys.path.insert(0, str(root / 'tools'))
import ground_shadow_lab as g  # noqa: E402
sys.path.insert(0, str(root / 'reports/2026-11-21-indirect-light'))
import capture as base  # noqa: E402
import scene  # noqa: E402

VGL_DIR_FILE = here / 'vgl-dir.txt'
SCREEN = (1280, 720)
ERROR_ALLOW_DEFAULT = []
PRIVATE_DISPLAY_MIN = 171


def note(text):
    with (here / 'progress.txt').open('a') as f:
        f.write('%s %s\n' % (time.strftime('%Y-%m-%dT%H:%M:%S%z'), text))


def merge_result(label, entry):
    path = here / 'result.json'
    data = json.loads(path.read_text()) if path.exists() else {'runs': {}}
    data['runs'][label] = entry
    data['updated'] = time.strftime('%Y-%m-%dT%H:%M:%S%z')
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    os.replace(tmp, path)


def clean_env(display):
    assert display not in (':0', ':1') and display != os.environ.get('DISPLAY') and int(display[1:].split('.')[0]) >= PRIVATE_DISPLAY_MIN
    env = {k: v for k, v in os.environ.items() if k not in ('WAYLAND_DISPLAY', 'XAUTHORITY', 'DISPLAY', 'XDG_SESSION_TYPE', 'LD_PRELOAD')}
    env['DISPLAY'] = display
    return env


def start_xvfb(work):
    for n in range(PRIVATE_DISPLAY_MIN, PRIVATE_DISPLAY_MIN + 60):
        if Path('/tmp/.X11-unix/X%d' % n).exists() or Path('/tmp/.X%d-lock' % n).exists():
            continue
        log = (work / 'xvfb.log').open('wb')
        proc = subprocess.Popen(['Xvfb', ':%d' % n, '-screen', '0', '%dx%dx24' % SCREEN, '+extension', 'GLX', '+extension', 'RENDER',
                                 '-nolisten', 'tcp', '-noreset'], stdout=log, stderr=log, start_new_session=True)
        for _ in range(100):
            if Path('/tmp/.X11-unix/X%d' % n).exists() or proc.poll() is not None:
                break
            time.sleep(.1)
        if proc.poll() is None and Path('/tmp/.X11-unix/X%d' % n).exists():
            return proc, ':%d' % n
    raise RuntimeError('no free private display')


def window_ids(env, pid):
    out = subprocess.run(['xdotool', 'search', '--all', '--onlyvisible', '--pid', str(pid), '--name', 'Minecraft'], env=env,
                         capture_output=True, text=True).stdout.split()
    return out


def acquire_lock(seconds):
    handle = open(base.LOCK, 'a+b')
    end = time.monotonic() + seconds
    while True:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return handle
        except BlockingIOError:
            if time.monotonic() > end:
                raise RuntimeError('render lock %s still held after %ds' % (base.LOCK, seconds))
            time.sleep(2)


def error_lines(txt, allow):
    bad = []
    for line in txt.splitlines():
        if '/ERROR]' in line and not any(re.search(a, line) for a in allow):
            bad.append(line)
    if 'reverting to default' in txt.lower():
        bad += [l for l in txt.splitlines() if 'reverting to default' in l.lower()]
    return bad


def main(prepare_private_client=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pack', type=Path)
    parser.add_argument('label')
    parser.add_argument('--backend', choices=('vgl', 'llvmpipe'), default='vgl')
    parser.add_argument('--set', choices=('core', 'all'), default='core')
    parser.add_argument('--stages', help='comma separated stage subset (ordered as given)')
    parser.add_argument('--dry-run', action='store_true', help='build + validate datapack only; no lock, no world, no launch')
    parser.add_argument('--lock-timeout', type=int, default=900)
    parser.add_argument('--load-timeout', type=int, default=420)
    parser.add_argument('--allow-error', action='append', default=list(ERROR_ALLOW_DEFAULT), help='regex of benign ERROR log lines')
    parser.add_argument('--keep-work', action='store_true')
    parser.add_argument('--compiler-mod', type=Path, help='copy the optional Aqualumen lighting compiler into this private client')
    parser.add_argument('--glcache', default='/tmp/aql-v190-glcache')
    parser.add_argument('--size', default='1280x720', help='window size WxH (software smoke uses a small one)')
    parser.add_argument('--period-ticks', type=int, default=200, help='ticks per stage (stretch for slow clients)')
    parser.add_argument('--settle', type=float, default=2.5, help='seconds after READY before the first frame')
    parser.add_argument('--shot-gap', type=float, default=.5, help='seconds between the three frames')
    parser.add_argument('--vgl-dir', help='dir containing x/usr/lib/libvglfaker.so (default: contents of vgl-dir.txt)')
    args = parser.parse_args()
    assert re.fullmatch('[a-z0-9-]+', args.label)
    global SCREEN
    SCREEN = tuple(int(v) for v in args.size.split('x'))
    scene.configure(args.period_ticks)
    names = args.stages.split(',') if args.stages else (scene.ALL if args.set == 'all' else scene.CORE)
    unknown = [n for n in names if n not in scene.STAGE_TABLE]
    assert not unknown, unknown
    scene.self_test(names)
    pack = args.pack.resolve(strict=True) if not args.dry_run or args.pack.exists() else args.pack
    if args.dry_run:
        files = scene.datapack(names)
        print('dry-run OK: %d datapack files, %d stages: %s' % (len(files), len(names), ','.join(names)))
        return
    assert re.fullmatch('[A-Za-z0-9._-]+\\.zip', pack.name) and not pack.is_symlink()
    out = here / args.label
    t_start = time.time()
    lock = None
    vgl = None
    if args.backend == 'vgl':
        vgl = Path(args.vgl_dir or VGL_DIR_FILE.read_text().strip()) / 'x/usr/lib'
        assert (vgl / 'libvglfaker.so').is_file() and (vgl / 'libdlfaker.so').is_file(), 'run setup-vgl.sh first'
    if args.backend == 'vgl':
        note('%s: 描画ロック待ち (%s)' % (args.label, base.LOCK))
        lock = acquire_lock(args.lock_timeout)
    out.mkdir()
    orig = g.GAME
    source = orig / 'saves' / g.lab.WORLD
    work = Path(tempfile.mkdtemp(prefix='aql-v190-run-'))
    game = work / 'minecraft'
    for folder in ('mods', 'saves', 'config', 'shaderpacks', 'screenshots'):
        (game / folder).mkdir(parents=True)
    g.lab.shared.world_marker()
    clone = game / 'saves' / g.lab.WORLD
    with (source / 'session.lock').open('r+b') as handle:
        fcntl.lockf(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        manifest = base.copy_world(source, clone)
    assert base.tree(clone) == manifest
    assert g.lab.pairs((clone / 'aqualumen-world.properties').read_bytes())['world_id'] == g.lab.WORLD_ID
    assert base.nbt(gzip.decompress((clone / 'level.dat').read_bytes()))['Data']['WorldGenSettings']['seed'] == 308060
    orig_digest = {n: g.lab.sha(orig / n) for n in ('options.txt', 'config/iris.properties', 'config/sodium-options.json')}
    for name in g.lab.NORMAL_MODS:
        shutil.copy2(orig / 'mods' / name, game / 'mods')
    compiler_digest = None
    if args.compiler_mod:
        compiler = args.compiler_mod.resolve(strict=True)
        assert compiler.name in ('aqualumen-lighting-compiler-0.1.0.jar','aqualumen-lighting-compiler-0.2.1.jar','aqualumen-lighting-compiler-0.3.0.jar')
        installed = Path(shutil.copy2(compiler, game / 'mods'))
        compiler_digest = g.lab.sha(installed)
    for name in ('iris.properties', 'sodium-options.json'):
        shutil.copy2(orig / 'config' / name, game / 'config')
    shutil.copy(pack, game / 'shaderpacks')
    pack_sha = g.lab.sha(game / 'shaderpacks' / pack.name)  # identity of the bytes actually used
    cfg = game / 'config/iris.properties'
    cfg.write_bytes(g.lab.replace_values(cfg.read_bytes(), {'shaderPack': pack.name}, '='))
    config = dict(g.lab.OPTIONS, maxFps='120', overrideWidth=str(SCREEN[0]), overrideHeight=str(SCREEN[1]), chatVisibility='2', fov='0.0',
                  pauseOnLostFocus='false', bobView='false', fovEffectScale='0.0', fullscreen='false', enableVsync='false',
                  screenEffectScale='0.0')
    (game / 'options.txt').write_bytes(g.lab.replace_values((orig / 'options.txt').read_bytes(), config, ':'))
    kit = clone / 'datapacks/AqualumenLavaRuntime'
    assert not kit.exists()
    for rel, text in scene.datapack(names).items():
        p = kit / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    (out / 'geometry.json').write_text(json.dumps(scene.geometry(names), indent=2))
    (out / 'private-game.txt').write_text(str(game))
    if prepare_private_client is not None:
        prepare_private_client(game, clone, out)
    runtime = json.loads((root / 'reports/2026-11-20-underwater-refinement/local-launch.json').read_text())
    java = [runtime['java'], '-Xms512m', '-Xmx2600m', '-XX:ActiveProcessorCount=4', '-Dorg.lwjgl.openal.libname=libopenal.so.1', '-cp',
            ':'.join(runtime['cp']), 'net.fabricmc.loader.impl.launch.knot.KnotClient', '--username', scene.PLAYER, '--version', '1.21.1',
            '--gameDir', str(game), '--assetsDir', str(orig.parents[2] / 'assets'), '--assetIndex', '17', '--uuid', scene.PLAYER_UUID,
            '--accessToken', '0', '--userType', 'legacy', '--width', str(SCREEN[0]), '--height', str(SCREEN[1]),
            '--quickPlaySingleplayer', g.lab.WORLD]
    xvfb, display = start_xvfb(work)
    env = clean_env(display)
    env['ALSOFT_DRIVERS'] = 'null'
    cache = Path(args.glcache)  # private, persistent across MY runs only (never the Lab cache); affects compile time, not output
    cache.mkdir(parents=True, exist_ok=True)
    env['__GL_SHADER_DISK_CACHE_PATH'] = str(cache)
    gl_label = {}
    if args.backend == 'vgl':
        env.update(LD_PRELOAD='%s:%s' % (vgl / 'libdlfaker.so', vgl / 'libvglfaker.so'), VGL_DISPLAY='egl0', VGL_LOGO='0',
                   VGL_COMPRESS='0', VGL_SPOIL='0', VGL_VERBOSE='1')
        gl_label = dict(path='VirtualGL 3.1.5 (user-local, EGL device egl0) -> Xvfb %s, X11 uncompressed transport' % display, expected='NVIDIA GeForce RTX 3080 Ti')
    else:
        env.update(LIBGL_ALWAYS_SOFTWARE='1', __EGL_VENDOR_LIBRARY_FILENAMES='/usr/share/glvnd/egl_vendor.d/50_mesa.json',
                   MESA_LOADER_DRIVER_OVERRIDE='llvmpipe', LP_NUM_THREADS='8')
        gl_label = dict(path='Mesa llvmpipe (CPU software) on Xvfb %s' % display, expected='llvmpipe')
    note('%s: 起動 backend=%s display=%s game=%s pack=%s' % (args.label, args.backend, display, game, pack.name))

    def xd(*a, **kw):
        return subprocess.run(['xdotool', *a], env=env, check=True, capture_output=True, text=True, **kw)

    log = out / 'client.log'
    events = []
    done = {}
    failure = None
    proc = None
    wid = None
    t_launch = time.monotonic()
    try:
        with log.open('xb') as sink:
            proc = subprocess.Popen(java, cwd=game, env=env, stdout=sink, stderr=sink, start_new_session=True)
            armed = False
            last_swap = 0.0
            until = time.monotonic() + args.load_timeout
            pending = None  # (name, log offset of READY)
            seen = {}
            last_cpu = time.monotonic()
            while len(done) < len(names):
                txt = log.read_text(errors='replace')
                if proc.poll() is not None:
                    raise RuntimeError('client exited early rc=%s' % proc.returncode)
                if time.monotonic() > until:
                    raise RuntimeError('timeout; captured so far: %s' % ','.join(done))
                if not armed and time.monotonic() - last_cpu > 60:
                    last_cpu = time.monotonic()
                    try:
                        f = Path('/proc/%d/stat' % proc.pid).read_text().rsplit(')', 1)[1].split()
                        note('%s: 待機中 経過%ds javaCPU=%.0fs ログ最終行=%s' % (args.label, time.monotonic() - t_launch, (int(f[11]) + int(f[12])) / os.sysconf('SC_CLK_TCK'),
                                                                        txt.strip().splitlines()[-1][:100]))
                    except OSError:
                        pass
                bad = error_lines(txt, args.allow_error)
                if bad:
                    raise RuntimeError('client log error: ' + bad[0])
                if not wid:
                    w = window_ids(env, proc.pid)
                    if len(w) == 1:
                        wid = w[0]
                if wid and not armed and 'AQLAVA_ARM_END' in txt and re.search(
                        r'Creating pipeline for dimension minecraft:overworld.*?Started [1-9]\d* worker threads', txt, re.S):
                    xd('windowfocus', '--sync', wid, timeout=6)
                    assert xd('getwindowfocus').stdout.strip() == wid
                    time.sleep(2)
                    xd('key', 'F1')
                    time.sleep(.5)
                    xd('key', 'f')  # swap paper to offhand -> datapack starts the stage loop
                    last_swap = time.monotonic()
                    armed = True
                    until = time.monotonic() + 60 + (scene.PERIOD / 20.0 + 30) * len(names) * 1.5
                    note('%s: 描画開始を確認しステージ開始 (renderer log: %s)' % (args.label, (re.findall(r'OpenGL Renderer: .*', txt) or ['?'])[0]))
                if armed:
                    if 'AQLAVA_BEGIN_' not in txt and 'contact bridge initialized' in txt and time.monotonic() - last_swap > 7:
                        assert xd('getwindowfocus').stdout.strip() == wid
                        xd('keydown', 'f')
                        time.sleep(.35)
                        xd('keyup', 'f')
                        last_swap = time.monotonic()
                    for m in scene.EVENT_RE.finditer(txt):
                        key = (m.start(), m.group(1), m.group(2))
                        if key not in seen:
                            seen[key] = len(events)
                            events.append(dict(kind=m.group(1), stage=m.group(2), at=m.start()))
                    for ev in events:
                        if ev['kind'] == 'READY' and ev['stage'] in names and ev['stage'] not in done and not ev.get('used'):
                            ev['used'] = True
                            name = ev['stage']
                            time.sleep(args.settle)
                            shots = {}
                            def still_capturing():
                                # Bracket every image by this READY and its matching STILL.
                                window = log.read_text(errors='replace')[ev['at']:]
                                return scene.EVENT_RE.findall(window) == [('READY', name)]

                            before = set((game / 'screenshots').glob('*.png'))
                            for tag in ('x11-a', 'ingame', 'x11-b'):
                                if not still_capturing():
                                    break
                                if tag == 'ingame':
                                    # A slow frame can miss a short key press. Keep the
                                    # retry in this stage, and accept one complete F2 only.
                                    new = set()
                                    retry_at = 0
                                    key_deadline = min(until, time.monotonic() + 15)
                                    while time.monotonic() < key_deadline and still_capturing() and not new:
                                        if time.monotonic() >= retry_at:
                                            assert xd('getwindowfocus').stdout.strip() == wid
                                            xd('keydown', 'F2')
                                            time.sleep(.4)
                                            xd('keyup', 'F2')
                                            retry_at = time.monotonic() + 3
                                        time.sleep(.1)
                                        new = set((game / 'screenshots').glob('*.png')) - before
                                    if len(new) != 1:
                                        break
                                    shot = next(iter(new))
                                    last = -1
                                    for _ in range(80):  # the game writes asynchronously: wait for size to settle and the IEND chunk
                                        size = shot.stat().st_size
                                        if size == last and shot.read_bytes()[-8:-4] == b'IEND':
                                            break
                                        last = size
                                        time.sleep(.15)
                                    if shot.read_bytes()[-8:-4] != b'IEND':
                                        break
                                    p = out / (name + '-ingame.png')
                                    shutil.copy2(shot, p)
                                else:
                                    p = out / ('%s-%s.png' % (name, tag))
                                    subprocess.run(['ffmpeg', '-v', 'error', '-n', '-f', 'x11grab', '-draw_mouse', '0', '-window_id', wid, '-i', display,
                                                    '-frames:v', '1', str(p)], env=env, check=True, timeout=10)
                                assert base.png_size(p) == SCREEN, (p, base.png_size(p))
                                shots[tag] = g.lab.sha(p)
                                if not still_capturing():
                                    break
                                time.sleep(args.shot_gap)
                            if len(shots) != 3 or not still_capturing():
                                note('%s: stage %s missed its capture window; retrying next cycle' % (args.label, name))
                                for tag in shots:
                                    p = out / ('%s-%s.png' % (name, tag))
                                    p.rename(out / ('%s-%s.discarded%d.png' % (name, tag, time.time_ns())))
                                continue
                            # wait for the STILL re-verification of this very stage window
                            end = time.monotonic() + max(25, (scene.STILL_AT - scene.READY_AT) / 20 + 20)
                            verdict = None
                            while time.monotonic() < end and verdict is None:
                                t2 = log.read_text(errors='replace')
                                after = t2[ev['at']:]
                                tail = scene.EVENT_RE.findall(after)
                                for kind, st in tail[1:]:
                                    if kind in ('BEGIN', 'DRIFT', 'FAIL') or (kind == 'READY' and st != name):
                                        verdict = 'discarded:%s_%s' % (kind, st)
                                        break
                                    if kind == 'STILL' and st == name:
                                        verdict = 'valid'
                                        break
                                time.sleep(.3)
                            note('%s: stage %s -> %s' % (args.label, name, verdict))
                            if verdict == 'valid':
                                # Retain the original log-addressable F2 file even when
                                # the private instance is removed after a successful run.
                                originals = out / 'f2'
                                originals.mkdir(exist_ok=True)
                                (originals / shot.name).hardlink_to(out / (name + '-ingame.png'))
                                done[name] = shots
                            else:
                                for tag in ('x11-a', 'ingame', 'x11-b'):
                                    q = out / ('%s-%s.png' % (name, tag))
                                    if q.exists() or tag == 'ingame':
                                        (out / (name + ('-ingame.png' if tag == 'ingame' else '-%s.png' % tag))).rename(
                                            out / (name + '-' + tag + '.discarded%d.png' % int(time.time())))
                                ev['used'] = False if verdict is None else True
                        elif ev['kind'] == 'FAIL' and not ev.get('seen'):
                            ev['seen'] = True
                            note('%s: FAIL (%s) 状態検証失敗 ※次周回で再試行' % (args.label, ev['stage']))
                time.sleep(.15)
    except Exception as exc:  # noqa: BLE001
        failure = '%s: %s' % (type(exc).__name__, exc)
        note('%s: 失敗: %s' % (args.label, failure))
    finally:
        if proc and proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
                proc.wait(timeout=25)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=10)
        xvfb.terminate()
        try:
            xvfb.wait(timeout=10)
        except subprocess.TimeoutExpired:
            xvfb.kill()
        if lock:
            lock.close()
    txt = log.read_text(errors='replace') if log.exists() else ''
    renderer = (re.findall(r'OpenGL Renderer: (.*)', txt) or [None])[0]
    gl_version = (re.findall(r'OpenGL Version: (.*)', txt) or [None])[0]
    shader_used = ('Using shaderpack: ' + pack.name) in txt
    unchanged = base.tree(source) == manifest and all(g.lab.sha(orig / n) == d for n, d in orig_digest.items())
    entry = dict(label=args.label, pack=pack.name, packSha256=pack_sha, sourcePackShaNow=g.lab.sha(pack), compilerModSha256=compiler_digest, backend=args.backend, display=display, gl=dict(gl_label, renderer=renderer, version=gl_version),
                 shaderpackLogged=shader_used, stages=names, screenshots=done, complete=(len(done) == len(names) and failure is None),
                 failure=failure, originalWorldAndConfigUnchanged=unchanged, sourceDigest=base.digest(manifest),
                 privateGameDir=str(game), size=list(SCREEN), periodTicks=scene.PERIOD, settleSeconds=args.settle, seconds=round(time.time() - t_start, 1))
    if failure:
        entry['errorLines'] = [l for l in txt.splitlines() if '/ERROR]' in l or 'Exception' in l or 'compile' in l.lower()][:40]
        entry['logTail'] = txt.splitlines()[-40:]
    (out / 'complete.json').write_text(json.dumps(entry, indent=2, ensure_ascii=False))
    merge_result(args.label, entry)
    note('%s: 終了 complete=%s renderer=%s unchanged=%s' % (args.label, entry['complete'], renderer, unchanged))
    if not args.keep_work and entry['complete']:
        shutil.rmtree(work, ignore_errors=True)
    sys.exit(0 if entry['complete'] and unchanged else 1)


if __name__ == '__main__':
    main()
