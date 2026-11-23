import json,subprocess,sys,time
from pathlib import Path
p=Path(__file__).resolve().parent
variants=['combined','baseline'] # Debug remains available if same-scene photography is ambiguous.
for v in variants:
 def accepted():
  for f in p.glob('water-'+v+'-*/complete.json'):
   if json.loads(f.read_text()).get('complete'):return True
  return False
 i=0
 while not accepted():
  i+=1;label=f'water-{v}-retry{i}'
  if (p/label).exists():continue
  with (p/f'{v}-retry.log').open('w') as out:
   r=subprocess.run([sys.executable,'capture.py',v,label],cwd=p,stdout=out,stderr=out)
  if r.returncode==0:break
  log=(p/f'{v}-retry.log').read_text()
  pre=p/label/'preflight.json'
  foreign=pre.exists() and bool(json.loads(pre.read_text()).get('foreignObservations'))
  if not (foreign or 'GPU busy' in log or 'still held after' in log):raise RuntimeError(log)
  time.sleep(8)
