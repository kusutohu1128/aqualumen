"""Compare the same two guard-verified rooms using consecutive actual render intervals."""
import importlib.util
import json
from pathlib import Path
here=Path(__file__).resolve().parent
previous=here.parent/"2026-11-21-animal-light"
spec=importlib.util.spec_from_file_location("intervals",previous/"timing/measure.py")
timing=importlib.util.module_from_spec(spec)
spec.loader.exec_module(timing)
baseline=json.loads((previous/"frame-times.json").read_text())
frames={}
for stage in ("both-west","day-white"):
    frames[stage]={
        "6":baseline["results"]["6"][stage],
        "7":timing.extract("ceiling-isolated",stage,7),
        "7ConcurrentNativeCheck":timing.extract("ceiling-cost",stage,7),
    }
    for v,item in frames[stage].items():
        print(stage,v,item["meanFps"],round(item["p99Ms"],2),item["frames"])
out={k:v for k,v in baseline.items() if k!="results"}
out["results"]=frames
out["comparison"]="Use 6 and 7 for the comparison. The exploratory 7ConcurrentNativeCheck measurement overlapped with other GPU work."
(here/"frame-times.json").write_text(json.dumps(out,indent=2)+"\n")
