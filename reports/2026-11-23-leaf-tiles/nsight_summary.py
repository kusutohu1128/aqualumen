"""Extract only the identified private Minecraft process from an Nsight SQLite export."""

import json
import sqlite3
import sys
from pathlib import Path

folder = Path(sys.argv[1]).resolve()
receipt = json.loads((folder / "receipt.json").read_text())
db = sqlite3.connect((folder / "minecraft.sqlite").as_uri() + "?mode=ro", uri=True)
db.row_factory = sqlite3.Row
pid = receipt["javaPid"]


def rows(query, *args):
    return [dict(row) for row in db.execute(query, args)]


# Nsight encodes the process and native thread IDs in the upper/lower 24 bits.
where = "((a.globalTid>>24)&16777215)=?"
(process,) = rows("SELECT DISTINCT pid,name FROM PROCESSES WHERE pid=?", pid)
threads = rows(
    f"""SELECT a.globalTid,a.globalTid&16777215 AS tid, count(*) AS glCalls
                FROM OPENGL_API a WHERE {where} GROUP BY a.globalTid ORDER BY glCalls DESC""",
    pid,
)
render = threads[0]
thread_names = rows(
    """SELECT DISTINCT s.value AS name FROM ThreadNames t JOIN StringIds s ON s.id=t.nameId
                       WHERE t.globalTid=?""",
    render["globalTid"],
)
assert any(r["name"] == "Render thread" for r in thread_names), thread_names


def api_times(table):
    return rows(
        f"""SELECT s.value AS api,count(*) AS calls,round(sum(a.end-a.start)/1e6,3) AS sumMs,
                 round(max(a.end-a.start)/1e6,3) AS maxMs FROM {table} a JOIN StringIds s ON s.id=a.nameId
                 WHERE a.globalTid=? GROUP BY s.value ORDER BY sumMs DESC""",
        render["globalTid"],
    )


gl = api_times("OPENGL_API")
osrt = api_times("OSRT_API")
(stats,) = rows(
    f"""SELECT count(*) AS events,round((max(a.end)-min(a.start))/1e9,3) AS eventSpanSeconds
                        FROM OPENGL_API a WHERE {where}""",
    pid,
)
assert render["glCalls"] > 100 and any("Draw" in row["api"] for row in gl) and osrt
out = dict(
    **receipt,
    process=process,
    openGL=stats,
    renderThread=dict(tid=render["tid"], name=thread_names, calls=render["glCalls"], gl=gl, osrt=osrt),
    traceFile=str(folder / "minecraft.nsys-rep"),
)
Path(__file__).with_name("nsight-minecraft.json").write_text(json.dumps(out, indent=2) + "\n")
print(stats, process, render["tid"], render["glCalls"])
print("GL", gl[:5], "OSRT", osrt[:3])
