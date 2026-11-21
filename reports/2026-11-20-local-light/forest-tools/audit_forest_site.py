"""Read-only persisted-save audit of the forest torch site (run before and after a capture; no writes, no game).

Checks against forest-site.json: exact save marker (name/UUID/seed/generator), reserved exact-AIR cells (torch slot, the cell
above it and the three camera cells), every verified existing bark/leaf/support cell, and that no fixture journal is pending.
Exit status 0 only when everything holds. Minecraft only persists changed chunks on save, so run it with the game closed.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from worldread import SEED, UUID, WORLD, World  # noqa: E402

INSTANCE = WORLD.parent.parent


def main():
    site = json.loads((HERE / "forest-site.json").read_text())
    world = World()
    bad = []
    for item in site["reserved_exact_air_cells"]:
        if world.state(*item["cell"]) != {"Name": "minecraft:air"}:
            bad.append({"kind": "reserved_not_air", "cell": item["cell"], "state": world.state(*item["cell"])})
    for item in site["existing_verified_cells"]:
        state = world.state(*item["cell"])
        props = state.get("Properties", {}) if state else {}
        flat = ",".join(f"{k}={v}" for k, v in sorted(props.items()))
        if not state or state["Name"] != item["id"] or any(need not in flat for need in item["required_state_substrings"]):
            bad.append({"kind": "existing_changed", "cell": item["cell"], "expected": item["id"], "state": state})
    journals = {n: (INSTANCE / "aqualumen-benchmark" / n).exists() for n in ("opaque-fixture-journal.json", "local-light-fixture-journal.json")}
    result = {"world": WORLD.name, "world_id": UUID, "seed": SEED, "reserved_cells": len(site["reserved_exact_air_cells"]),
              "existing_cells": len(site["existing_verified_cells"]), "problems": bad, "pending_journals": journals,
              "save_unchanged_while_reading": world.unchanged(),
              "ok": not bad and not any(journals.values()) and world.unchanged()}
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
