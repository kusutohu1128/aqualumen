"""Exclusive actual queried-format atlas retry; failed producer/evidence remain intact."""
from pathlib import Path
import water_receiver_atlas_lifecycle as atlas
base=atlas.base
base.OUT=base.ROOT/"reports/2026-10-06-water-receiver-atlas-v2"
base.JAR="aqualumen-receiver-material-probe-0.1.2-atlas-v3.jar"
base.HASH="908feae33c6d20c5d395eadb7856ce5dfffbc20c8af24beb87d64e519dc2ce12"
def baseline():
    base.baseline()
    # The immediately preceding clean exit belongs to the failed TEST client.
    (base.OUT/"normal-clean-save-exit.log").rename(base.OUT/"preceding-TEST-clean-save-exit.log")
    base.copy(base.ROOT/"reports/2026-10-06-water-receiver-atlas/normal-clean-save-exit.log","prior-ordinary-clean-save-exit.log")
if __name__=="__main__":
    import sys
    action=sys.argv[1]
    if action in ("test","normal"):base.launch(action)
    else:{"baseline":baseline,"install":atlas.install,"collect":base.collect,"restore":base.restore}[action]()
