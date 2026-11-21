"""Actual original MAIN with extra external paired-Sun inputs and independent gates.

Freeze the original closed-box source, then add only input setup, extra draws,
readbacks and assertions. Production shader and original observer are unchanged.
Never overwrite any previous binary, raw field, receipt or report packet.
"""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/2026-10-06-water-receiver-sun"

EXTRA = r'''
    // External paired-world-Sun controls: homogeneous dry radiance, flat water.
    std::ofstream solarReceipt(out/"world-sun.csv");
    solarReceipt<<std::setprecision(17)<<"role,red,green,blue,expectedRed,firstTravel,verticalDepth,observerDifference\n";
    auto uploadSource=[&]() {
        glActiveTexture(GL_TEXTURE8);glBindTexture(GL_TEXTURE_2D,inputs[2]);
        glTexSubImage2D(GL_TEXTURE_2D,0,0,0,16,96,GL_RGBA,GL_FLOAT,source.data());
    };
    auto changeTotal=[&](bool added) {
        for(size_t p=0;p<source.size();p+=4) if(cells[p]==3)source[p]=added?.30f:.25f;
        uploadSource();
    };
    auto uploadSun=[&](float red,float alpha,bool available=true) {
        for(size_t p=0;p<directSource.size();p+=4) {
            directSource[p]=red;directSource[p+1]=0;directSource[p+2]=0;directSource[p+3]=alpha;
        }
        const float missing[4]={0,0,0,0};
        texture(9,inputs[3],available?16:1,available?96:1,GL_RGBA32F,GL_RGBA,available?directSource.data():missing);
    };
    const double outgoingF=facetFresnel(-normalized(origin)[1]);
    const double verticalDepth=origin[1]-first.point[1];
    const double sunEntry=1-facetFresnel(1.0);
    const double exitEtendue=1/(1.333*1.333);
    const double expectedRed=.05*sunEntry*std::exp(-.32*verticalDepth)*exitEtendue
        *std::exp(-.32*first.travel)*(1-outgoingF);
    // Add matching total/direct red source power, retaining all scene/sky inputs.
    changeTotal(true);uploadSun(.05f,1);
    save(out/"world-sun-positive-source.rgba32f",source);
    save(out/"world-sun-positive-direct.rgba32f",directSource);
    auto sunPositive=draw(base,false,"world-sun-positive");
    auto sunWitness=draw(base,true,"world-sun-positive-witness");
    double solarObserver=difference(sunPositive.colour,sunWitness.colour);
    double deltaRed=sunPositive.colour[q]-neutral.colour[q];
    double deltaGreen=sunPositive.colour[q+1]-neutral.colour[q+1];
    double deltaBlue=sunPositive.colour[q+2]-neutral.colour[q+2];
    solarReceipt<<"paired-positive,"<<deltaRed<<","<<deltaGreen<<","<<deltaBlue<<","<<expectedRed<<","<<first.travel<<","<<verticalDepth<<","<<solarObserver<<"\n";
    require(solarObserver<1e-6,"positive world-Sun observer C0 passivity");
    require(expectedRed>1e-4&&std::abs(deltaRed-expectedRed)<=.02*expectedRed,
        "positive world-Sun independent entry Fresnel/incident Beer/exit etendue/outgoing Beer");
    require(std::abs(deltaGreen)<1e-6&&std::abs(deltaBlue)<1e-6,"world Sun affects only its paired red source");
    // Known first geometry cannot take a total source with missing/malformed
    // direct attribution when the actual receiver admits nonzero solar power.
    for(const auto& rejected:std::array<std::pair<std::string,int>,4>{{
        {"missing-direct",0},{"unready-direct",1},{"negative-direct",2},{"excess-direct",3}}}) {
        const int mode=rejected.second;
        changeTotal(false);
        uploadSun(mode==2?-.01f:mode==3?.5f:.05f,mode==1?0:1,mode!=0);
        auto noTag=draw(base,false,rejected.first+"-neutral");
        changeTotal(true);
        auto tag=draw(base,false,rejected.first+"-tag");
        double dr=tag.colour[q]-noTag.colour[q],dg=tag.colour[q+1]-noTag.colour[q+1],db=tag.colour[q+2]-noTag.colour[q+2];
        solarReceipt<<rejected.first<<","<<dr<<","<<dg<<","<<db<<",0,"<<first.travel<<","<<verticalDepth<<",0\n";
        require(std::max(std::abs(dr),std::max(std::abs(dg),std::abs(db)))<1e-6,
            "missing/malformed world Sun must not qualify a first material source");
    }
    changeTotal(false);uploadSun(0,1);
    solarReceipt.flush();require(bool(solarReceipt),"World Sun control receipt saved");
    std::cout<<"PASS original MAIN world-Sun: positive red "<<deltaRed<<" expected "<<expectedRed
        <<"; green/blue "<<deltaGreen<<"/"<<deltaBlue<<"; four unpaired/invalid first-source controls rejected.\n";
'''


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def once(source, old, new):
    if source.count(old) != 1:
        raise ValueError("Exclusive external fixture seam changed: " + old)
    return source.replace(old, new)


def run():
    if subprocess.run(["rtk", "proxy", "pgrep", "-x", "java"], stdout=subprocess.DEVNULL).returncode != 1:
        raise ValueError("Live Java prevents native GPU validation")
    target = OUT / "native-v1"
    target.mkdir(exist_ok=False)
    frozen = target / "source"
    paths = [ROOT / "tools/water_occluded_receiver_main.cpp", ROOT / "tools/glcheck.cpp", Path(__file__).resolve(),
             *sorted((ROOT / "tools").glob("*probe.h")), *sorted((ROOT / "shaders").rglob("*"))]
    hashes = {}
    for path in paths:
        if not path.is_file():
            continue
        name = path.relative_to(ROOT)
        copy = frozen / name
        copy.parent.mkdir(parents=True, exist_ok=True)
        with copy.open("xb") as stream:
            stream.write(path.read_bytes())
        hashes[str(name)] = sha(path)
    original = (frozen / "tools/water_occluded_receiver_main.cpp").read_text()
    changes = [
        ("GLuint inputs[3];glGenTextures(3,inputs);", "GLuint inputs[4];glGenTextures(4,inputs);"),
        ("glDeleteTextures(3,p);", "glDeleteTextures(4,p);"),
        ("std::fill(sky.end()-skyWidth*4,sky.end(),0); // no Sun/cache/direct receiver source",
         "std::fill(sky.end()-skyWidth*4,sky.end(),0);\n    for(int x=0;x<skyWidth;x++)sky[(skyHeight-1)*skyWidth*4+x*4]=.04f;\n    save(out/\"positive-solar-cache.rgba32f\",sky);"),
        ("save(out/\"receiver-cells.rgba32f\",cells);save(out/\"receiver-source-neutral.rgba32f\",source);",
         "std::vector<float> directSource(source.size(),0);\n    for(size_t q=3;q<directSource.size();q+=4)directSource[q]=1;\n    texture(9,inputs[3],16,96,GL_RGBA32F,GL_RGBA,directSource.data());\n    save(out/\"world-sun-zero-direct.rgba32f\",directSource);\n    save(out/\"receiver-cells.rgba32f\",cells);save(out/\"receiver-source-neutral.rgba32f\",source);"),
        ('glUniform1i(glGetUniformLocation(program,"aqualumenReceiverReady"),1);',
         'glUniform1i(glGetUniformLocation(program,"aqualumenReceiverSun"),9);\n        glUniform1i(glGetUniformLocation(program,"aqualumenReceiverReady"),1);'),
        ("    for(int yy=0;yy<4;yy++) for(int zz=0;zz<24;zz++) for(int xx=0;xx<16;xx++) {\n        int p=((yy*24+zz)*16+xx)*4;V3 center={-8+xx+.5,-4+yy+.5,-24+zz+.5};",
         EXTRA + "\n    for(int yy=0;yy<4;yy++) for(int zz=0;zz<24;zz++) for(int xx=0;xx<16;xx++) {\n        int p=((yy*24+zz)*16+xx)*4;V3 center={-8+xx+.5,-4+yy+.5,-24+zz+.5};"),
    ]
    source = original
    for before, after in changes:
        source = once(source, before, after)
    fixture = frozen / "tools/water_receiver_sun_fixture.cpp"
    with fixture.open("x") as stream:
        stream.write(source)
    with (target / "external-input-edits.json").open("x") as stream:
        json.dump(changes, stream, indent=2)
    binary = target / "probe"
    build = subprocess.run(["rtk", "proxy", "g++", "-std=c++17", "-O2", "-Wall", "-Wextra", str(fixture), "-o", str(binary), "-lepoxy", "-lEGL"],
                           cwd=ROOT, capture_output=True, text=True)
    with (target / "compile.log").open("x") as stream:
        stream.write(build.stdout + build.stderr)
    if build.returncode != 0:
        raise ValueError("Compiler failed; never run an old binary")
    result = subprocess.run(["rtk", "proxy", str(binary), str(frozen / "shaders"), str(target / "raw")], cwd=ROOT, capture_output=True, text=True)
    with (target / "native.log").open("x") as stream:
        stream.write(result.stdout + result.stderr)
    receipt = dict(exitCode=result.returncode, compilerExitCode=build.returncode, nativeBinarySHA256=sha(binary),
                   synchronousExclusiveBinaryBuild=True, externalFixtureSHA256=sha(fixture), sourceSHA256=hashes,
                   sourceUnchangedDuringRun=all(sha(ROOT / name) == digest for name, digest in hashes.items()),
                   worldSourceIsSynthetic=True, actualMinecraftFrameTiming=False, fullGoalAchieved=False)
    with (target / "receipt.json").open("x") as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True)
    print(result.stdout + result.stderr, end="")
    print("World-Sun native exit:", result.returncode)
    if result.returncode != 0:
        raise SystemExit(1)


if __name__ == "__main__":
    run()
