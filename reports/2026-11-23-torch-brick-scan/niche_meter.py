"""Add a small bottom-edge readout to a private copy of the published shader."""
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile
from make_rows import HERE, ROOT, WORK
from niche_pixels import REGIONS

SHIP = ROOT / "dist/Aqualumen-Torch-Shadow-Rows.zip"
assert sha256(SHIP.read_bytes()).hexdigest()=="d9a740d78c612634a5c197bb001a3bcc250f83d0e891d0cbb90363de334d7968"
source=(HERE.parent / "2026-11-22-eye-adaptation/meter.glsl").read_text()
checkword=source[source.index("vec3 meterBytes"):source.index("vec3 meterTile")]
regions=", ".join("ivec4("+",".join(map(str,rect))+")" for rect in REGIONS.values())
snippet=checkword+"const ivec4 nicheRegion[6] = ivec4[6]("+regions+");\n"+"""
void main() {
    ivec2 local=ivec2(gl_FragCoord.xy)-ivec2(16,16);
    if(all(greaterThanEqual(local,ivec2(0))) && all(lessThan(local,ivec2(576,8)))) {
        int region=local.x/96, tap=(local.x%96)/8, field=local.x%8;
        ivec4 rect=nicheRegion[region];
        ivec2 target=rect.xy+ivec2((vec2(tap,local.y)+.5)*vec2(rect.zw-rect.xy)/vec2(12,8));
        ivec2 at=ivec2(target.x,textureSize(colortex0,0).y-1-target.y);
        vec3 scene=max(texelFetch(colortex0,at,0).rgb,vec3(0));
        vec4 material=texelFetch(colortex10,at,0);
        float depth=texelFetch(depthtex0,at,0).r;
        bool emitting=material.a<0. && depth<.999999 && depth==texelFetch(depthtex1,at,0).r;
        vec3 emission=emitting?min(material.rgb,scene):vec3(0.);
        float value;
        if(field<3) value=log2(1.+scene[field])/8.;
        else if(field<6) value=log2(1.+emission[field-3])/8.;
        else value=field==6?exposureScale()/32.:(emitting?.75:.25);
        gl_FragColor=vec4(meterBytes(value),1.);
        return;
    }
"""
if __name__=="__main__":
    dest=WORK/"Aqualumen-Niche-Meter.zip"
    with ZipFile(SHIP) as original, ZipFile(dest,"w") as target:
        for item in original.infolist():
            data=original.read(item)
            if item.filename=="shaders/final.fsh":
                marker=b"void main() {"
                assert data.count(marker)==1
                data=data.replace(marker,snippet.encode())
            target.writestr(item,data)
    print(sha256(dest.read_bytes()).hexdigest())
