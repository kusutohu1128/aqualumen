"""Carry forward the two existing survival timelines and add the first excursion on seed 20261123."""
import json
from pathlib import Path

here=Path(__file__).resolve().parent
previous=here.parent/"2026-11-22-ceiling-return/playtime.json"


def main():
    old=json.loads(previous.read_text())
    spans=[]
    for entry in old["chains"]:
        row=dict(entry)
        row["receipt"]=str((previous.parent/entry["receipt"]).resolve().relative_to(here.parents[1]))
        spans.append(row)
    runs=(("2026-11-22-ceiling-return/village/lamp-road",20261139),
          ("2026-11-22-forest-cave/rainy-descent",20261123))
    for path,seed in runs:
        directory=here.parent/path
        result=json.loads((directory/"complete.json").read_text())
        identity=json.loads((directory/"identity.json").read_text())
        assert identity["seed"]==seed and not result["logErrors"] and not result["results"].get("failed")
        assert result["cleanExit"] and result["previousSaveUnchanged"] and not result["benchmarkSentinelPresent"]
        assert result["pack"] in ("Aqualumen-1.9.0-preview.7.zip","Aqualumen-1.9.0-preview.8.zip")
        assert result["savedLevel"]["allowCommands"]==result["savedLevel"]["GameType"]==0
        start=result["revisit"]["sourceSavedTime"]
        earlier=[v for v in spans if v["seed"]==seed]
        if earlier:assert earlier[-1]["lastTick"]==start
        spans.append(dict(seed=seed,firstTick=start,lastTick=result["savedLevel"]["Time"],
                          walkedMetres=result["walkedAfterReloadMetres"],receipt=str((directory/"complete.json").relative_to(here.parents[1]))))
    total=sum(row["lastTick"]-row["firstTick"] for row in spans)
    meters=round(sum(row["walkedMetres"] for row in spans),2)
    data={"chains":spans,"seeds":sorted({row["seed"] for row in spans}),"ticks":total,"gameDays":total/24000,
          "walkedMetres":meters,"basis":"Continuous saved world time during survival play. Diagnostic branches, fixed-time fixtures and offline survey are excluded."}
    (here/"playtime.json").write_text(json.dumps(data,indent=2)+"\n")
    print(data["seeds"],total,total/24000,meters)


if __name__=="__main__":
    main()
