"""Driver for an isolated, CPU-only, loopback-bound vanilla 1.21.1 dedicated server.

The server code is the unmodified Mojang client.jar (sha1 30c73b1c...) that the Prism
launcher already caches: it contains net.minecraft.server.Main. Nothing is downloaded and
nothing outside the fresh work directory is written. Mods, shaders and the GPU are not involved.
"""
import json, os, queue, re, socket, subprocess, threading, time

PRISM = os.path.expanduser('~/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher')
CLIENT_JAR = f'{PRISM}/libraries/com/mojang/minecraft/1.21.1/minecraft-1.21.1-client.jar'
JAVA21 = f'{PRISM}/java/java-runtime-delta/bin/java'
CLIENT_JAR_SHA1 = '30c73b1c5da787909b2f73340419fdf13b9def88'
SKIP = ('lwjgl', 'java-objc-bridge', 'oshi', 'text2speech', 'jorbis', 'netty-transport-native-epoll')

def library_paths():
    meta = json.load(open(f'{PRISM}/meta/net.minecraft/1.21.1.json'))
    out = []
    for lib in meta['libraries']:
        name = lib['name']
        if any(s in name for s in SKIP): continue
        parts = name.split(':')
        g, a, v = parts[:3]
        p = f"{PRISM}/libraries/{g.replace('.', '/')}/{a}/{v}/{a}-{v}.jar"
        if not os.path.exists(p): raise FileNotFoundError(p)
        out.append(p)
    return out

def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p

PROPS = """server-ip=127.0.0.1
server-port={port}
online-mode=false
enable-status=false
enable-query=false
enable-rcon=false
use-native-transport=false
level-name=world
level-seed={seed}
level-type=minecraft\\:normal
generate-structures=true
gamemode=survival
difficulty=peaceful
spawn-monsters=false
spawn-animals=false
spawn-npcs=false
max-players=1
view-distance=3
simulation-distance=3
spawn-protection=0
sync-chunk-writes=false
max-tick-time=-1
white-list=false
motd=aqualumen-offline-probe
"""

class Server:
    def __init__(self, workdir, seed, cpus='0-3', heap='2G', nice=15, reuse=False):
        assert os.path.isdir(workdir)
        # reuse=True only re-opens a world this tool itself generated in /tmp.
        assert reuse or not os.listdir(workdir), 'workdir must be brand new and empty'
        self.dir, self.seed = workdir, seed
        self.q = queue.Queue(); self.log = []
        # EULA: required by the unmodified server for any start. Set only inside the throw-away dir.
        open(f'{workdir}/eula.txt', 'w').write('eula=true\n')
        open(f'{workdir}/server.properties', 'w').write(PROPS.format(port=free_port(), seed=seed))
        cmd = ['nice', '-n', str(nice), 'taskset', '-c', cpus, JAVA21, f'-Xmx{heap}', '-Xms512M',
               '-XX:+UseSerialGC', '-XX:ActiveProcessorCount=4', '-Dmax.bg.threads=3',
               '-Djava.net.preferIPv4Stack=true', '-cp', ':'.join([CLIENT_JAR] + library_paths()),
               'net.minecraft.server.Main', '--nogui']
        self.p = subprocess.Popen(cmd, cwd=workdir, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, text=True, bufsize=1)
        threading.Thread(target=self._pump, daemon=True).start()
        self.wait(r'Done \(', 180)

    def _pump(self):
        for line in self.p.stdout:
            line = line.rstrip('\n'); self.log.append(line); self.q.put(line)
        self.q.put(None)

    def wait(self, pattern, timeout):
        rx = re.compile(pattern); end = time.time() + timeout
        while time.time() < end:
            try: line = self.q.get(timeout=1)
            except queue.Empty: continue
            if line is None: raise RuntimeError('server exited:\n' + '\n'.join(self.log[-20:]))
            m = rx.search(line)
            if m: return m
        raise TimeoutError(pattern)

    def cmd(self, text, pattern, timeout=120):
        while not self.q.empty(): self.q.get_nowait()
        self.p.stdin.write(text + '\n'); self.p.stdin.flush()
        return self.wait(pattern, timeout)

    def stop(self):
        if self.p.poll() is None:
            try: self.p.stdin.write('stop\n'); self.p.stdin.flush()
            except BrokenPipeError: pass
            try: self.p.wait(120)
            except subprocess.TimeoutExpired:
                self.p.terminate(); self.p.wait(30)
        return self.p.returncode
