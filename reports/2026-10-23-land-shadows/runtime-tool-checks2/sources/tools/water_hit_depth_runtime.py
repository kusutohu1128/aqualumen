import argparse
import os
from pathlib import Path
import sys

import water_paired_runtime as runtime


def references_game(value,game):
    if str(game) in value or 'Aqualumen Lab' in value:
        return True
    path=Path(value)
    if not path.is_absolute():
        return False
    for ancestor in (path,*path.parents):
        try:
            if os.path.samefile(ancestor,game):
                return True
        except (FileNotFoundError,NotADirectoryError):
            continue
    return False


def lab_java_processes(game, proc=Path('/proc')):
    owned=[]
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            if entry.stat().st_uid!=os.getuid() or (entry/'comm').read_text().strip()!='java':
                continue
            cwd=os.readlink(entry/'cwd')
            command=(entry/'cmdline').read_bytes().decode(errors='replace')
            if references_game(cwd,game) or any(references_game(arg,game) for arg in command.split('\x00') if arg):
                owned.append(int(entry.name))
                continue
            for fd in (entry/'fd').iterdir():
                try:
                    if references_game(os.readlink(fd),game):
                        owned.append(int(entry.name));break
                except FileNotFoundError:
                    continue
        except FileNotFoundError:
            continue
        except (PermissionError,OSError) as error:
            raise RuntimeError('Cannot establish same-user Java ownership') from error
    return sorted(owned)


def configure(mode,attempt=1,generation=2):
    root=Path(__file__).resolve().parents[1]
    report=root/'reports/2026-10-22-water-hit-depth'
    version=('0.1.0-hit1d' if mode=='baseline' else '0.1.0-depth')+str(generation)
    runtime.OUT=report/('runtime-'+mode+str(generation))
    runtime.PROBE=report/(mode+str(generation))/('aqualumen-paired-water-probe-'+version+'.jar')
    runtime.RUN_SUFFIX='depth-'+mode+'-obs'+str(generation)+('' if attempt==1 else '-r'+str(attempt))+'-20261022'

    def stopped():
        runtime.require(not lab_java_processes(runtime.GAME),'Lab Java is live; do not change runtime files')

    def live_owned():
        runtime.require(len(lab_java_processes(runtime.GAME))==1,'Exactly one owned Lab Java required')
        runtime.prepared()

    def scene(name):
        live_owned()
        runtime.prior.require_current_pipeline((runtime.GAME/'logs/latest.log').read_bytes(),
            runtime.json.loads((runtime.OUT/'launcher-start.json').read_text())['previousLog'])
        runtime.subprocess.run(['rtk','proxy',sys.executable,'tools/benchmark-control.py','start','--run-id',
            'paired-water-'+name+'-'+runtime.RUN_SUFFIX,'--scenes',name,'--warmup','10','--sample','20'],cwd=root,check=True)

    runtime.prior.stopped=stopped
    runtime.live_owned=live_owned
    runtime.scene=scene


if __name__=='__main__':
    parser=argparse.ArgumentParser(add_help=False)
    parser.add_argument('--mode',required=True,choices=('baseline','candidate'))
    parser.add_argument('--attempt',type=int,choices=(1,2,3),default=1)
    parser.add_argument('--generation',type=int,choices=(2,3),default=2)
    args,remaining=parser.parse_known_args()
    configure(args.mode,args.attempt,args.generation)
    sys.argv=[sys.argv[0],*remaining]
    runtime.main()
