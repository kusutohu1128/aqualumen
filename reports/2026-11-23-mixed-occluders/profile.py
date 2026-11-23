"""Measure the same passes for the one-box and two-box packs on the birch route."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "2026-11-23-torch-density"))
import measure_density as density

if __name__ == "__main__":
    density.gpu.EXPECTED |= {"dispatch/shadowcomp5", "dispatch/shadowcomp6"}
    density.main()
