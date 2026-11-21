"""Native receiver-source candidate: fresh ordinary baseline, no TEST install."""
import water_receiver_texture_lifecycle as base

base.OUT = base.ROOT / "reports/2026-10-06-water-receiver-main"

if __name__ == "__main__":
    import sys
    action = sys.argv[1]
    if action == "baseline":
        base.baseline()
    elif action == "normal":
        base.launch("normal")
    else:
        raise ValueError("Native-only cycle: no install or world commands")
