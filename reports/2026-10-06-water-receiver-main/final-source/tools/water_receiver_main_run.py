"""Reuse the unchanged qualified closed-box MAIN fixture in an exclusive packet."""
import water_occluded_receiver_run as retained

retained.OUT = retained.ROOT / "reports/2026-10-06-water-receiver-main"

if __name__ == "__main__":
    retained.main()
