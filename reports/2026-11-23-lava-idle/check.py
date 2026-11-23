"""Run one renderer-specific fullscreen replay under the private benchmark render lock."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys

from diagnostics import R, ROOT, OUT, P3, P8, P9, P9_SHA256, digest, entries

sys.path.insert(0, str(R.parent/'2026-11-22-gpu-profile'))
import run as guarded


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('renderer',choices=('nvidia','mesa'))
    parser.add_argument('label')
    parser.add_argument('--mode',choices=('witness','route-red','candidate','historical','regression'),default='witness')
    checks={'check':'--play-release','check-lava':'--lava-light-probe','check-ground':'--ground-return-probe',
            'check-canopy':'--canopy-sky-probe','check-animal':'--animal-light-probe',
            'check-ceiling':'--ceiling-light-probe','check-eye':'--eye-exposure-probe'}
    parser.add_argument('--check',choices=checks)
    args=parser.parse_args()
    if not args.label.startswith(args.mode+'-') or not args.label.replace('-','').isalnum():
        raise ValueError(args.label)
    path=R/(args.label+'.log')
    if path.exists(): raise FileExistsError(path)
    pack={'witness':P3,'regression':P9}.get(args.mode,P8)
    packs=OUT/('reference-'+pack.stem)
    for name,data in entries(pack).items():
        entry=packs/name
        if not entry.exists():
            entry.parent.mkdir(parents=True,exist_ok=True)
            entry.write_bytes(data)
        assert entry.read_bytes()==data
    dist=json.loads((OUT/'dist-before.json').read_text())
    def check_dist():
        assert {p.relative_to(ROOT/'dist').as_posix():digest(p) for p in (ROOT/'dist').rglob('*') if p.is_file()}==dist
    check_dist()
    before=guarded.lab_check()
    assert before==json.loads((guarded.RUNS/'gp-p7-a/preflight.json').read_text())['labAfter']
    pre=guarded.inspect_gpu()
    assert not pre['foreign'],pre
    with open(f'/tmp/aql-render21-{os.getuid()}.lock','a+b') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        under=guarded.inspect_gpu()
        assert not under['foreign'],under
        vendor='10_nvidia' if args.renderer=='nvidia' else '50_mesa'
        env={**os.environ,'__EGL_VENDOR_LIBRARY_FILENAMES':f'/usr/share/glvnd/egl_vendor.d/{vendor}.json'}
        if args.renderer=='mesa': env['LIBGL_ALWAYS_SOFTWARE']='1'
        cmd=[str(ROOT/'build/glcheck'),str(packs/'shaders'),'--lava-idle-diagnostic',str(OUT/'submitted')]
        if args.mode in ('candidate','route-red'):
            assert digest(P9)==P9_SHA256
            ref=OUT/'submitted/gp-idle-src-p8'
            test=ref if args.mode=='route-red' else OUT/'submitted/gp-idle-src-p9'
            for folder in (ref,test):
                receipt=json.loads((R/'runs'/folder.name/'summary.json').read_text())
                assert receipt['validated'] and all(digest(folder/name)==pin for name,pin in receipt['sources'].items())
            cmd=[str(ROOT/'build/glcheck'),str(packs/'shaders'),'--lava-idle-probe',str(ref),str(test)]
        if args.mode in ('historical','regression'):
            assert args.check and digest(P9)==P9_SHA256
            if args.mode=='historical':
                # Make invokes its shell separately for both recipes in the historical check target.
                shell=OUT/'preflight-sh'
                shell.write_text('#!/usr/bin/env python3\nimport os,sys\nsys.path.insert(0,'+repr(str(guarded.R))+')\nfrom run import inspect_gpu\ns=inspect_gpu()\nassert not s["foreign"],s\nos.execv("/bin/sh",["sh",*sys.argv[1:]])\n')
                shell.chmod(0o755)
                cmd=['make','SHELL='+str(shell),args.check]
            else:
                cmd=[str(ROOT/'build/glcheck'),str(packs/'shaders'),checks[args.check]]
                if args.check=='check-lava': cmd.append(str(ROOT/'release/shaders'))
        with path.open('x') as stream:
            proc=subprocess.Popen(cmd,env=env,stdout=stream,stderr=subprocess.STDOUT)
            while True:
                try:
                    code=proc.wait(timeout=4)
                    break
                except subprocess.TimeoutExpired:
                    state=guarded.inspect_gpu()
                    def owned(pid):
                        while pid>1:
                            if pid==proc.pid: return True
                            try: pid=int(Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[1])
                            except FileNotFoundError: return True
                        return False
                    foreign={pid:name for pid,name in state['foreign'].items() if not owned(pid)}
                    if foreign:
                        proc.terminate()
                        proc.wait()
                        raise RuntimeError(f'foreign job {foreign}')
        check_dist()
        after=guarded.lab_check()
        guarded.save(path.with_suffix('.json'),dict(before=pre,underLock=under,exit=code,labBefore=before,labAfter=after,distFiles=len(dist)))
        assert after==before and not guarded.inspect_gpu()['foreign']
        if args.mode=='route-red':
            log=path.read_text()
            assert code and 'empty deferred heavy entry=1' in log and 'empty frame still enters heavy-capable deferred body' in log
        elif code: sys.exit(code)
        assert ('RTX 3080 Ti' if args.renderer=='nvidia' else 'llvmpipe') in path.read_text()


if __name__=='__main__':
    main()
