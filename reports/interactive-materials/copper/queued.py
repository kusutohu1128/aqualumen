import json,subprocess,time
from pathlib import Path
here=Path(__file__).resolve().parent
gold=here.parent/'gold-scene'
def verified():
 for r in gold.glob('control-*/complete.json'):
  try:
   if json.loads(r.read_text()).get('complete'):return True
  except (ValueError,OSError):pass
 return False
start=time.monotonic()
while not verified():
 if time.monotonic()-start>1800:raise SystemExit('Control not captured')
 time.sleep(2)
for i in range(1,180):
 label=f'copper-v{i}'
 if (here/label).exists():continue
 with (here/'latest-run.log').open('w') as out:
  result=subprocess.run(['python3','-B',str(here/'capture.py'),label],cwd=here,stdout=out,stderr=subprocess.STDOUT)
 if result.returncode==0:
  (here/'verified-run.txt').write_text(label+'\n')
  subprocess.run(['python3',str(here/'screenshots.py'),label],cwd=here,check=True);break
 log=(here/'latest-run.log').read_text()
 meta=(here/label/'complete.json')
 reason=meta.read_text() if meta.exists() else ''
 if ('GPU busy' not in log and 'foreign GPU' not in reason and 'foreign GPU' not in log):
  print(log[-1200:]+reason[-900:]);raise SystemExit(1)
 time.sleep(7)
else:raise SystemExit(2)
