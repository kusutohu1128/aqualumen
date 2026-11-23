"""List directly observed Nsight events for the verified Minecraft process."""
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent


def summarize(folder):
    proof=json.loads((folder/"receipt.json").read_text())
    assert proof["cleanExit"] and proof["originalLabUnchanged"] and proof["sourceSaveUnchanged"]
    with sqlite3.connect(Path(proof["sqlite"]).as_uri()+"?mode=ro",uri=True) as db:
        tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        process=db.execute("SELECT globalPid,name FROM PROCESSES WHERE pid=?",(proof["javaPid"],)).fetchone()
        assert process and ("java" in process[1].lower() or "minecraft" in process[1].lower())
        # Nsight stores the OS thread ID in the low 24 bits of a global thread ID.
        pid=process[0]
        observations={}
        for table in ("OPENGL_API","OSRT_API"):
            if table not in tables:continue
            rows=db.execute(f"""SELECT s.value,COUNT(*),sum(a.end-a.start)/1e6,max(a.end-a.start)/1e6
                                  FROM {table} a JOIN StringIds s ON s.id=a.nameId
                                  WHERE (a.globalTid & ~16777215)=? GROUP BY s.value ORDER BY COUNT(*) DESC""",(pid,)).fetchall()
            observations[table]={name:dict(count=n,totalCallMs=round(total,3),maxCallMs=round(maximum,3))
                                 for name,n,total,maximum in rows}
        gl=observations.get("OPENGL_API",{})
        assert any(name.startswith(("glDraw","glMultiDraw")) for name in gl) and "glDispatchCompute" in gl
        gl_threads=db.execute("""SELECT a.globalTid,count(*) FROM OPENGL_API a WHERE (a.globalTid & ~16777215)=?
                                  GROUP BY a.globalTid ORDER BY count(*) DESC""",(pid,)).fetchall()
        threads=[]
        for tid,count in gl_threads:
            names=[r[0] for r in db.execute("""SELECT DISTINCT s.value FROM ThreadNames t JOIN StringIds s ON s.id=t.nameId
                                        WHERE t.globalTid=?""",(tid,))]
            threads.append(dict(threadId=tid & 16777215,name=names,glCalls=count))
        gpu_tables={}
        for table in sorted(t for t in tables if t.startswith("OPENGL_") and t!="OPENGL_API"):
            gpu_tables[table]=db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        gl_total=sum(s['count'] for s in gl.values())
    return dict(**proof,openglCalls=gl_total,glThreads=threads,captureTables=gpu_tables,
                counts=observations,sha256=hashlib.file_digest(Path(proof["report"]).open("rb"),"sha256").hexdigest(),
                scope="One stationary private survival scene; GL API durations are host-side instrumented timings. No A/B performance inference.")


if __name__=="__main__":
    result=summarize(Path(sys.argv[1]))
    (HERE/"nsight-minecraft.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({k:result[k] for k in ("openglCalls","glThreads","captureTables")},indent=2))
