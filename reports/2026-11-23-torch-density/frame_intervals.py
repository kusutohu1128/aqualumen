"""Report render-interval means and tails separately for each instrument-free A/B order."""
import json

from compare_stages import EXPECTED, HERE


def collect():
    result = {}
    for order in ("a", "b"):
        sides = {}
        for label, digest in zip(("p8", "tiles"), EXPECTED, strict=True):
            folder = HERE / f"gp-density-frames-{label}-{order}"
            summary = json.loads((folder / "summary.json").read_text())
            observer = json.loads((folder / "observer.json").read_text())
            assert "gpuProfilerSha256" not in observer and summary["packSha"] == digest
            assert "RTX 3080 Ti" in summary["renderer"]["renderer"]
            sides[label] = summary["scenes"]
        assert set(sides["p8"]) == set(sides["tiles"]) == {"birch-1", "birch-4"}
        for scene in sides["p8"]:
            pair = {}
            for label in sides:
                window = sides[label][scene]
                assert window["frames"] == window["lastFrame"] - window["firstFrame"] + 1
                pair[label] = dict(meanMs=window["cpuMeanMs"], p99Ms=window["cpuP99Ms"],
                                   meanFps=1000/window["cpuMeanMs"], frames=window["frames"])
            result.setdefault(scene, {})[order] = pair
    return result


if __name__ == "__main__":
    data = collect()
    (HERE / "frame-intervals.json").write_text(json.dumps(data, indent=2)+"\n")
    for name, orders in data.items():
        for order, pair in orders.items():
            print(name, order, *[(v["frames"], round(v["meanMs"], 2), round(v["p99Ms"], 2)) for v in pair.values()])
