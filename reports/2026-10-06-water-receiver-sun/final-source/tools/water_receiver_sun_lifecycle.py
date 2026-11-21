"""Native world-Sun validation only; exclusive ordinary-state baseline."""
import water_receiver_texture_lifecycle as base

base.OUT = base.ROOT / "reports/2026-10-06-water-receiver-sun"

if __name__ == "__main__":
    import sys
    if sys.argv[1] == "baseline":
        base.baseline()
    elif sys.argv[1] == "normal":
        base.launch("normal")
    else:
        raise ValueError("No TEST install or ordinary-world commands")
