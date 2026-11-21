"""Run the isolated dual-lamp scene using the existing UUID-checked VirtualGL client."""
import importlib.util
import json
import shutil
import sys
from pathlib import Path
import scene as animals

here=Path(__file__).resolve().parent
# The reusable runner also imports its own scene; provide this scene explicitly.
target=here.parent/"2026-11-21-lava-light/runtime-v190/run.py"
spec=importlib.util.spec_from_file_location("private_optics",target)
runner=importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
runner.here=here
runner.scene=animals
runner.PRIVATE_DISPLAY_MIN=231

def add_frame_probe(game, clone, out):
    assert game.parent.name.startswith("aql-v190-run-") and clone==game/"saves"/runner.g.lab.WORLD
    marker=runner.g.lab.pairs((clone/"aqualumen-world.properties").read_bytes())
    assert marker["world_id"]==runner.g.lab.WORLD_ID
    jar=here.parents[1]/"build/animal-light/frame-sample.jar"
    private=Path(shutil.copy2(jar,game/"mods"))
    (game/"config/animal-frame-probe.enabled").write_text(str(game.resolve())+"\n")
    (out/"observer.json").write_text(json.dumps(dict(jar=private.name,sha256=runner.g.lab.sha(private),worldId=marker["world_id"])))

if __name__=="__main__":
    if "--glcache" in sys.argv:
        index=sys.argv.index("--glcache")+1
        sys.argv[index]=str(Path(sys.argv[index]).resolve())
    measure="--frame-intervals" in sys.argv
    if measure:
        sys.argv.remove("--frame-intervals")
    runner.main(prepare_private_client=add_frame_probe if measure else None)
