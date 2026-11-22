"""All elapsed quantities here are timestamp differences; units are explicit at export."""
from collections import Counter, defaultdict
import csv
import math
from statistics import mean


def percentile(values, fraction):
    return sorted(values)[math.ceil(len(values) * fraction) - 1]


def account(rows):
    if not rows or rows[0][0] != "frame" or sum(row[0] == "frame" for row in rows) != 1:
        raise ValueError("missing or duplicated frame")
    inclusive, exclusive, calls = Counter(), Counter(), Counter()
    stack = []
    root_start, root_end = rows[0][1:3]
    draws = Counter()
    uncovered = 0
    cursor = root_start
    # Rows are in submission order, with each parent preceding its children.
    for index, row in enumerate(rows):
        name, start, end = row[:3]
        if len(row)>=5:
            parent_index, draw_count = row[3:5]
            draws[name] += draw_count
            if draw_count < 0 or (index==0 and parent_index!=-1):
                raise ValueError("invalid event metadata")
        if end < start or start < root_start or end > root_end:
            raise ValueError("invalid timestamp interval")
        while stack and ((len(row)>=5 and stack[-1][3]!=parent_index)
                         or (len(row)==3 and start>=stack[-1][2])):
            stack.pop()
        if name != "frame":
            if not stack or end > stack[-1][2] or start < cursor:
                raise ValueError("orphan, overlapping siblings, or timestamp regression")
            if len(row)>=5 and start < last_end.get(parent_index, start):
                raise ValueError("overlap within recorded parent")
            parent = stack[-1][0]
            if parent != "frame":
                exclusive[parent] -= end - start
            else:
                uncovered += start - last_root_end
                last_root_end = end
            exclusive[name] += end - start
        else:
            last_root_end = root_start
            last_end = {}
        cursor = start
        inclusive[name] += end - start
        calls[name] += 1
        if len(row)>=5: last_end[parent_index] = end
        stack.append((name, start, end, index))
    uncovered += root_end - last_root_end
    error = abs(sum(exclusive.values()) + uncovered - (root_end - root_start))
    if error > 20000 or uncovered < 0 or min(exclusive.values(), default=0) < 0:
        raise ValueError("frame reconciliation failed")
    return dict(exclusive=dict(exclusive), inclusive=dict(inclusive), calls=dict(calls),
                draws=dict(draws), residual=uncovered, error=error)


def read_rows(stream):
    frames = defaultdict(list)
    for row in csv.DictReader(stream):
        frames[int(row["epoch"]), int(row["frame"])].append(
            (row["range"], int(row["start_ns"]), int(row["end_ns"])) +
            ((int(row["parent"]), int(row["draws"])) if "parent" in row else ()) +
            ((row["empty_slots"],) if "empty_slots" in row else ()))
    return frames


def collect_window(frames, ids):
    if not ids or list(ids) != list(range(ids[0], ids[0] + len(ids))):
        raise ValueError("invalid interval ordinals")
    keys = {epoch for epoch, frame in frames if ids[0] <= frame <= ids[-1]}
    if len(keys) != 1:
        raise ValueError("window spans a reload or has no samples")
    epoch = keys.pop()
    if any((epoch, i) not in frames for i in ids):
        raise ValueError("dropped or unavailable frame in selected window")
    return [account(frames[epoch, i]) for i in ids]


MEAN_OVERHEAD_PERCENT = 5
P95_OVERHEAD_PERCENT = 8


def overhead(off, on):
    m, p = mean(on) / mean(off), percentile(on, .95) / percentile(off, .95)
    return dict(meanPercent=(m-1)*100, p95Percent=(p-1)*100, **{"pass": m <= 1 + MEAN_OVERHEAD_PERCENT/100 and p <= 1 + P95_OVERHEAD_PERCENT/100})


def calibration(repeated, single, controls, baseline, roi):
    differences = [abs(a-b) for a, b in zip(controls, baseline, strict=True)]
    limits = [max(.10, .10*b) for b in baseline]
    ratio = repeated / single
    return dict(ratio=ratio, controlsMs=controls, baselineMs=baseline, differencesMs=differences,
                limitsMs=limits, roiMaxCode=roi,
                **{"pass": 3 <= ratio <= 5 and roi <= 1 and all(d <= t for d,t in zip(differences,limits))})
