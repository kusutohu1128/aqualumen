"""Add the established radiometry strip to the exact optional distribution."""
import sys
from make_pack import HERE, ROOT, SHIP, snippet, sha256, ZipFile
sys.path.insert(0,str(ROOT/"tools"))
from land_shadow_pack import ArchiveEntry, zip_bytes

WORK = ROOT / "build/stone-display"
DIST = WORK / "Aqualumen-Diffuse-Full.zip"
FLEX = ROOT / "dist/Aqualumen-Diffuse-Display.zip"

def full_strength_pack():
    with ZipFile(SHIP) as original:
        data=zip_bytes(tuple(ArchiveEntry(name,(HERE/"full-strength-final.fsh").read_bytes()
                            if name=="shaders/final.fsh" else original.read(name)) for name in original.namelist()))
    assert sha256(data).hexdigest()=="e5964a858e8c6f671c84cdea6b71c905b58b13a8cef2ca5f655adee2ca8966b9"
    if DIST.exists():
        assert DIST.read_bytes()==data
    else:
        DIST.write_bytes(data)


def metered(pack=DIST):
    assert pack in (FLEX,DIST)
    dest = WORK / ("Aqualumen-Midtones-Meter.zip" if pack==FLEX else "Aqualumen-Diffuse-Meter.zip")
    with ZipFile(SHIP) as old, ZipFile(pack) as new, ZipFile(dest,"w") as result:
        assert new.namelist()==old.namelist()
        changed={n for n in new.namelist() if old.read(n)!=new.read(n)}
        expected={"shaders/final.fsh"}
        if pack==FLEX:
            expected.update(("shaders/lang/en_US.lang","shaders/lang/ja_JP.lang","shaders/shaders.properties"))
        assert changed==expected
        for item in new.infolist():
            payload=new.read(item)
            if item.filename=="shaders/final.fsh":
                assert payload.count(b"void main() {")==1
                payload=payload.replace(b"void main() {",snippet.encode())
            result.writestr(item,payload)
    return dest


if __name__=="__main__":
    full_strength_pack()
    for path in (DIST,metered(),FLEX,metered(FLEX)):
        print(path.name,sha256(path.read_bytes()).hexdigest())
