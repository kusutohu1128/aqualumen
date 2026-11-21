"""Pinned reversible source transforms and NEW deterministic CPU-only profile JARs."""
import argparse
import hashlib
import json
import pathlib
import subprocess
import zipfile

ROOT=pathlib.Path(__file__).resolve().parents[1]
PRISM=pathlib.Path('/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher')
BENCH='tools/benchmark-mod/'
SUN='tools/water-sun-test-mod/'
HELPER='tools/water-sun-profile-mod/dev/aqualumen/bench/SunPerformance.java'
PINS={
 BENCH+'dev/aqualumen/bench/BathymetryMixin.java':'328bda55347b7ead2987ed374357820ce2e88781482b3c4e771fcdc80e3f2c24',
 BENCH+'dev/aqualumen/bench/BathymetrySnapshot.java':'38a27b286e74816e0d009353218200ba70c3fb6a86b117e5e3f442e974b591b8',
 BENCH+'dev/aqualumen/bench/CameraMixin.java':'42461448e03adbcf5155a79c775d224fea6b6d325d3c73c69ae6487872fdb686',
 BENCH+'dev/aqualumen/bench/FrameMixin.java':'4cb1185b2cd98964f30048e2fa858b8d7ec93ba14a099df406fdc56d9e2ad248',
 BENCH+'dev/aqualumen/bench/OcclusionFixture.java':'6c338dc6112f87f9c0192cffde8644f568c7682abb65afa80a26e8ec34a4734f',
 BENCH+'dev/aqualumen/bench/Recorder.java':'98dc953802ed850efe6e0b8704a0d90236647346c939bd171ac2f934b2e3e678',
 BENCH+'dev/aqualumen/bench/RenderTargetSnapshot.java':'63abc9f494104a3c4d8ff67c93c07cbca05a5e783f2fa5ace3fad8d4790e879e',
 BENCH+'dev/aqualumen/bench/ScreenshotCompletion.java':'6c2e32e731870b21264b15b1ad8bff8e1158eeeb22b524cd419fbd9377a66e46',
 BENCH+'dev/aqualumen/bench/ShoreFinalMixin.java':'c5f656c0823b65feee205fcc58df8877272d95be5a1c24dba15819f8bd83dc58',
 BENCH+'dev/aqualumen/bench/ShoreRuntimeObserver.java':'e3f86cebe9b2cfac741b776b7152be5781d0073dff84358dd0248c735bdbb02d',
 BENCH+'dev/aqualumen/bench/ShoreSamplerSnapshot.java':'ff9d6e64442fd1554260b2e0b6e5ff3355d5460916f3e7d475923f19caf833b4',
 BENCH+'dev/aqualumen/bench/SolarCacheSnapshot.java':'fa8a10afa44898652c85950899856746a13ed06354bc51317b226ed072a10a7d',
 BENCH+'dev/aqualumen/bench/UnderwaterScene.java':'3196960694970a626f02445e8d8a6c6138d5fe50a71baab2b737c89bca5eba33',
 BENCH+'aqualumen-benchmark.mixins.json':'4aa06f439c3a75c6794fd64459455a3008fb8c58298ca1ec976e0e888faf7be1',
 BENCH+'fabric.mod.json':'69f7aeb7de7292a8a54335b74a368b0786c286edf3574b063393ee7e5bcd0572',
 SUN+'dev/aqualumen/suntest/SunAuthorization.java':'e22b57d9f840eeb9198cfa40d9801bd63aabb993b3ed3087885e98634461ddba',
 SUN+'dev/aqualumen/suntest/SunGuardObserver.java':'b91bd97e61a48ba08028028c9c39ec20d1fb8eaf446c96b18c66bf24ac18ad67',
 SUN+'dev/aqualumen/suntest/SunGuardSnapshot.java':'d95932bcb06985ae0b06cc84ae3b67844456e26292cddd0ca61dd79699ccaef0',
 SUN+'dev/aqualumen/suntest/SunRequestGate.java':'4ecd6dab97e2d0ecb585cb1636a4368afd2591f3a783cbb91393fec503f9135e',
 SUN+'dev/aqualumen/suntest/SunUniforms.java':'0cc67b0cd0a49ef42192dd5a6d8cdeb2fafdcbfbbb4bd4495f225d92e8f258e3',
 SUN+'dev/aqualumen/suntest/mixin/SunGuardMixin.java':'6b543ed337133ee5ef2837695446090ec0571ab95af1d758849905600cfc8e93',
 SUN+'dev/aqualumen/suntest/mixin/SunUniformMixin.java':'ba64fd03abfe847c686a31c30dd9543ad5ba6ad9a3d133f335cef34692450951',
 SUN+'aqualumen-water-sun-test.mixins.json':'c386a5911ebec8284017202094b4893fa95434a98b94ff68ac219f1fdf63c608',
 SUN+'fabric.mod.json':'450cf89996d8860fb954064bc802331df9a949746c2393928908c6cc4567fd41',
}
OLD_SUPPLIER='IntSupplier supplier=()->SunAuthorization.value(SunAuthorization.runtime(\n                FabricLoader.getInstance().getGameDir().toAbsolutePath().normalize()));'
NEW_SUPPLIER='IntSupplier supplier=dev.aqualumen.bench.SunPerformance.wrap(()->SunAuthorization.value(SunAuthorization.runtime(\n                FabricLoader.getInstance().getGameDir().toAbsolutePath().normalize())));'
OLD_HASH='if(packMatches)packMatches=hex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(game.resolve("shaderpacks").resolve(expectedPack))))\n                    .equals(config.getProperty("expected_pack_sha256"));'
HASH_READ='Files.readAllBytes(game.resolve("shaderpacks").resolve(expectedPack))'
HASH_BODY=OLD_HASH[len('if(packMatches)packMatches='):-1]
NEW_HASH='if(packMatches)packMatches=SunPerformance.hash(()->'+HASH_BODY.replace(HASH_READ,'SunPerformance.bytes('+HASH_READ+')')+');'
OLD_READY='if (state.equals("preparing")) { guard(mc, true); runMetadata(mc); next(mc); return; }'
NEW_READY='if (state.equals("preparing")) { guard(mc, true); SunPerformance.onRunReady(runId,runDir,config); runMetadata(mc); next(mc); return; }'
OLD_FINISH='state = "complete"; status("All requested natural-world scenes, raw timings and screenshots recorded");'
NEW_FINISH=OLD_FINISH+'\n                    SunPerformance.finish(state,runId,runDir);'
TRANSFORMS={
 SUN+'dev/aqualumen/suntest/SunUniforms.java':[(OLD_SUPPLIER,NEW_SUPPLIER)],
 BENCH+'dev/aqualumen/bench/BathymetrySnapshot.java':[(OLD_HASH,NEW_HASH)],
 BENCH+'dev/aqualumen/bench/Recorder.java':[(OLD_READY,NEW_READY),(OLD_FINISH,NEW_FINISH)],
}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def replace_once(data,old,new):
    old,new=old.encode(),new.encode()
    if data.count(old)!=1:
        raise ValueError('exact unique source seam missing')
    return data.replace(old,new)

def recover(name,data):
    for old,new in reversed(TRANSFORMS.get(name,[])):
        data=replace_once(data,new,old)
    return data

def construct(repo=ROOT):
    result={}
    for name,pin in PINS.items():
        path=repo/name
        if path.is_symlink() or not path.is_file():
            raise ValueError('missing/symlinked source input: '+name)
        raw=path.read_bytes()
        if sha(raw)!=pin:
            raise ValueError('source pin mismatch: '+name)
        data=raw
        for old,new in TRANSFORMS.get(name,[]):
            data=replace_once(data,old,new)
        if recover(name,data)!=raw:
            raise ValueError('source recovery mismatch: '+name)
        result[name]=data
    return result

def dependencies():
    loader=PRISM/'libraries/net/fabricmc/fabric-loader/0.19.5/fabric-loader-0.19.5.jar'
    mixin=PRISM/'libraries/net/fabricmc/sponge-mixin/0.17.4+mixin.0.8.7/sponge-mixin-0.17.4+mixin.0.8.7.jar'
    for path,pin in [(loader,'93044e4dd46de5d8136701292f05e868da096d2c9fddb4793e4fdbcc63efc695'),
                     (mixin,'1f0ae44db7295f8626f33b1dc0ad7f043d8954a8d6847247875fcc5dfcecc934'),
                     (ROOT/'build/aqualumen-benchmark-0.3.9-projection-guards.jar','ef303d4b53a1299e64e562e81cf3ed70dfaffe96d99f5b8cbb58ff864cfd7b29'),
                     (ROOT/'build/aqualumen-water-sun-test-0.1.0-observer-v2.jar','e942f1a193e1a1f5875cd5041a59b67e88414655b124ec8fd5ae2d721ec8edaf')]:
        if path.is_symlink() or not path.is_file() or sha(path.read_bytes())!=pin:
            raise ValueError('dependency pin mismatch: '+str(path))
    return loader,mixin,PRISM/'java/java-runtime-delta/bin'

def jar(path,classes,resources):
    items={p.relative_to(classes).as_posix():p.read_bytes() for p in classes.rglob('*.class')}
    items.update(resources)
    with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name,data in sorted(items.items()):
            info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644<<16;archive.writestr(info,data,compresslevel=9)

def build(output,repo=ROOT):
    output=pathlib.Path(output).absolute()
    allowed=(repo/'reports/2026-10-03-water-performance/cpu-profile').resolve()
    if output.is_symlink() or output.exists() or not output.resolve().is_relative_to(allowed):
        raise ValueError('expected NEW output under performance/cpu-profile')
    generated=construct(repo);loader,mixin,java=dependencies()
    helper=(repo/HELPER).read_bytes()
    output.mkdir(parents=True)
    for name,data in generated.items():
        parent=output/'parents'/name;parent.parent.mkdir(parents=True,exist_ok=True);parent.write_bytes((repo/name).read_bytes())
        target=output/'sources'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    target=output/'sources'/HELPER;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(helper)
    bench_classes=output/'classes/benchmark';sun_classes=output/'classes/sun'
    bench_classes.mkdir(parents=True);sun_classes.mkdir(parents=True)
    cp=str(loader)+':'+str(mixin)
    subprocess.run([str(java/'javac'),'-proc:none','-Xlint:all','-cp',cp,'-d',str(bench_classes)]
        +[str(output/'sources'/n) for n in generated if n.startswith(BENCH) and n.endswith('.java')]
        +[str(target)],check=True,timeout=60)
    subprocess.run([str(java/'javac'),'-proc:none','-Xlint:all','-cp',str(bench_classes)+':'+cp,'-d',str(sun_classes)]
        +[str(output/'sources'/n) for n in generated if n.startswith(SUN) and n.endswith('.java')],check=True,timeout=60)
    products={}
    for prefix,classes,name in [(BENCH,bench_classes,'aqualumen-benchmark-0.3.9-profile-v1.jar'),
                                (SUN,sun_classes,'aqualumen-water-sun-test-0.1.0-profile-v1.jar')]:
        resources={pathlib.PurePosixPath(n).name:data for n,data in generated.items() if n.startswith(prefix) and n.endswith('.json')}
        product=output/name;jar(product,classes,resources);products[name]=sha(product.read_bytes())
    manifest={'schema':'aqualumen-sun-profile-build-v1','originalSourcePins':PINS,
        'generatedSourcePins':{n:sha(data) for n,data in generated.items()},'helperSourceSha256':sha(helper),
        'products':products,'changedParentFiles':list(TRANSFORMS),'sourceRecovery':'reverse four exact spans -> all parent bytes',
        'modeProperty':'sun_profile=control|profile; default control; parsed once per run after original setup guard',
        'control':'full authorization/hash unchanged; timer/counter off; no measured timings or counts',
        'hashMetric':'getInstance/readAllBytes/digest/hex/equals; nested in total authorization, not isolated SHA',
        'export':'runDir/sun-profile.json CREATE_NEW after complete.json, before optional quit',
        'runtimeVerified':False,'GLExecuted':False,'opticsChanged':False,'originalArtifactsChanged':False}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    return manifest

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=pathlib.Path)
    args=parser.parse_args();print(json.dumps(build(args.output),indent=2,sort_keys=True))
