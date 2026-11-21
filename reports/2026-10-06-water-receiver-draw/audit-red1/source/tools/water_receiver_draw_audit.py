"""Independent saved actual draw/VS decoder audit; no Java module or live GL."""
import json
from pathlib import Path
from water_receiver_sun_audit import ROOT, sha

OUT = ROOT / 'reports/2026-10-06-water-receiver-draw'

def audit(out=OUT):
    raise ValueError('Independent actual draw reader not implemented')

if __name__ == '__main__':
    result = audit()
    with (OUT / 'independent-draw-audit.json').open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
    print(json.dumps(result, sort_keys=True))
