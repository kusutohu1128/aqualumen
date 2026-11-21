"""Run the optical room on a private copy of the UUID-checked QA world."""
import importlib.util
from pathlib import Path
import scene
here=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("optics",here.parent/"2026-11-21-lava-light/runtime-v190/run.py")
runner=importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
runner.here=here
runner.scene=scene
runner.PRIVATE_DISPLAY_MIN=231
if __name__=="__main__":
    runner.main()
