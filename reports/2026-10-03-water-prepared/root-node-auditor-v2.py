"""CPU-only verification of saved prepared-node output; never executes GL."""
import argparse
import hashlib
import json
from pathlib import Path
from fractions import Fraction
import re
import stat
import struct

ROLES = ("old", "wrapper", "reused")
SCALE = 1 << 24
LIMIT = (1 << 30) - 1
UNKNOWN = (0, 0, False)
PINS = {
    "old": "f9aa1c6763065f776d26b46385ecf82c2b16ac171783b19fa2353de1cef4be7a",
    "prepared": "ab88da48dee42c15a1cfd61514cad75c061a2d1841a15bfbbce21871b9b81441",
    "corpus": "24fdd6ed4ab983a99207883a22ec3b8140fc2aa3fbe364a023308a3b95916e48",
    "utilities": "f183963ee155c89dcbd8be3e36ccd7d313ccadccde4d1d9bb5b4c2ab16ae16f7",
    "fixtureSource": "f4abe4cbde553c44258e2c2f2f9e437809f67af9c350823ac4627dcfb1a5bb67",
}
INTERVALS = ["vx", "vy", "vz", "E", "K2", "downScale"]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read(path, maximum=8*1024*1024):
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= maximum, "Bounded regular file required: "+path.name)
    data = path.read_bytes()
    after = path.lstat()
    require((before.st_ino, before.st_size, before.st_mtime_ns) ==
            (after.st_ino, after.st_size, after.st_mtime_ns) and len(data) == before.st_size,
            "File changed while reading: "+path.name)
    return data


def load_json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "Duplicate JSON key")
            result[key] = value
        return result
    return json.loads(data, object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite JSON")))


def uints(values, length):
    require(isinstance(values, list) and len(values) == length and
            all(type(x) is int and 0 <= x <= 0xffffffff for x in values), "Typed uint32 array required")
    return values


def integers(values):
    return all(type(x) is int for x in values)


def words(data, count):
    require(len(data) == count*4, "Exact raw uint32 byte count required")
    return list(struct.unpack("<"+str(count)+"I", data))


def bytes_from_words(values):
    return struct.pack("<"+str(len(values))+"I", *values)


def require(okay, message):
    if not okay:
        raise ValueError(message)


def interval(lo, hi):
    return (lo, hi, True) if -LIMIT <= lo <= hi <= LIMIT else UNKNOWN


def point(bits):
    magnitude = bits & 0x7fffffff
    exponent = magnitude >> 23
    if magnitude > 0x40000000 or (exponent == 0 and magnitude):
        return UNKNOWN
    if not magnitude:
        return (0, 0, True)
    value = Fraction((magnitude & 0x7fffff) | 0x800000) * Fraction(2) ** (exponent - 126)
    if bits >> 31:
        value = -value
    lo = value.numerator // value.denominator
    return interval(lo, -((-value.numerator) // value.denominator))


def add(a, b):
    return interval(a[0]+b[0], a[1]+b[1]) if a[2] and b[2] else UNKNOWN


def sub(a, b):
    return interval(a[0]-b[1], a[1]-b[0]) if a[2] and b[2] else UNKNOWN


def mul(a, b):
    if not (a[2] and b[2]):
        return UNKNOWN
    products = [x*y for x in a[:2] for y in b[:2]]
    # Unbounded Python multiplication is independent of GLSL uint16 limbs.
    bounds = [interval(p // SCALE, -((-p) // SCALE)) for p in products]
    if not all(p[2] for p in bounds):
        return UNKNOWN
    return interval(min(p[0] for p in bounds), max(p[1] for p in bounds))


def context(bits):
    vx, vy, vz = [point(x) for x in bits[:3]]
    e = point(bits[6]); one = (SCALE, SCALE, True)
    E = mul(e, e)
    V = add(add(mul(vx, vx), mul(vy, vy)), mul(vz, vz))
    K2 = add(one, mul(E, sub(V, one)))
    down = mul(E, mul(vy, vy))
    valid = (all(p[2] for p in (vx, vy, vz, e, E, V, K2, down))
             and bits[1] >> 31 == 1 and bits[1] & 0x7fffffff != 0
             and 0x3f800000 < bits[6] <= 0x40000000 and V[0] > 0 and K2[0] > 0)
    return [vx, vy, vz, E, K2, down], bool(valid)


def classification(bits, ctx, valid):
    tx, ty, tz = [point(x) for x in bits[3:6]]
    if not valid or not all(p[2] for p in (tx, ty, tz)) or bits[4] >> 31 or not bits[4] & 0x7fffffff:
        return -1
    vx, vy, vz, E, K2, down = ctx
    U = add(add(mul(tx, tx), mul(ty, ty)), mul(tz, tz))
    B = add(add(mul(vx, tx), mul(vy, ty)), mul(vz, tz))
    comparisons = [mul(K2, mul(ty, ty)), mul(down, U), mul(K2, U), mul(E, mul(B, B))]
    if not U[2] or not B[2] or U[0] <= 0 or not all(p[2] for p in comparisons):
        return -1
    left, right, fleft, fright = comparisons
    down_yes, down_no = left[1] < right[0], left[0] > right[1]
    forward_yes, forward_no = fleft[1] < fright[0], fleft[0] > fright[1]
    negative, positive = B[1] < 0, B[0] > 0
    if not ((down_yes or down_no) and (forward_yes or forward_no) and (negative or positive)):
        return -1
    return 0 if down_no or forward_no or positive else 1


def groups(cases):
    result = []
    start = 0
    while start < len(cases):
        count = 1
        bits = cases[start][0]
        while start+count < len(cases) and count < 48:
            other = cases[start+count][0]
            if other[:3] != bits[:3] or other[6] != bits[6]:
                break
            count += 1
        result.append((start, count))
        start += count
    return result


def validate_maps(cases, maps):
    """Pure integer-record validation; no synthetic records become native proof."""
    count = len(cases)
    require(count > 0 and set(maps) == set(ROLES), "Missing required role")
    histogram = {"unknown": 0, "absent": 0, "supported": 0}
    interval_verified = 0
    records_verified = 0
    group_meta = {}
    for gi, (start, length) in enumerate(groups(cases)):
        checksum = sum((cases[start+i][1]+1)*(i+1) for i in range(length))
        for selected in range(length):
            group_meta[start+selected] = (gi, length, selected, checksum)
    for role in ROLES:
        captures = maps[role]
        require(len(captures) == 2 and all(len(x) == 8 for x in captures), "Expected eight maps and repeat")
        require(captures[0] == captures[1], "Repeat bytes differ")
        for capture in captures:
            require(all(len(row) == count*4 for row in capture), "Raw map shape differs")
            require(all(type(x) is int and 0 <= x <= 0xffffffff for row in capture for x in row), "Invalid uint32 record")
            for i, (bits, cpu_class) in enumerate(cases):
                require(len(bits) == 7 and all(type(x) is int and 0 <= x <= 0xffffffff for x in bits)
                        and type(cpu_class) is int and cpu_class in (-1, 0, 1), "Invalid input bits/CPU class")
                ctx, valid = context(bits)
                actual_class = classification(bits, ctx, valid)
                require(actual_class == cpu_class, "Pinned CPU class and independent arithmetic differ")
                rows = [slot[i*4:i*4+4] for slot in capture]
                require(rows[0] == [actual_class+1, *bits[:3]] and rows[1] == bits[3:], "Raw class/input echo differs")
                records_verified += 1
                _, length, _, checksum = group_meta[i]
                extras = [checksum, length, int(valid), 0, 0, 0]
                for triple, row, extra in zip(ctx, rows[2:], extras):
                    expected = [triple[0] & 0xffffffff, triple[1] & 0xffffffff, int(triple[2]), extra]
                    require(row == expected, "Interval endpoint, validity, context or checksum differs")
                    interval_verified += 1
    for _, expected in cases:
        histogram[("unknown", "absent", "supported")[expected+1]] += 1
    return {"classes": histogram, "count": count, "groupCount": len(groups(cases)),
            "intervalTriplesVerified": interval_verified, "rawRecordsVerified": records_verified,
            "nativeGLExecuted": False}


def fragment(module, role, probe_source):
    """Recover the generated attached source from pinned construction bytes."""
    fs = "#version 330 compatibility\n"+module+"\n"
    if role == "old":
        matches = re.findall(r'std::string oldContext=R"GLSL\((.*?)\)GLSL";', probe_source, re.S)
        require(len(matches) == 1, "Pinned original context source absent/ambiguous")
        fs += matches[0]
    fs += "uniform uvec3 wspViewBits; uniform uvec3 wspTargets[48]; uniform uint wspEtaBits;\n"
    fs += "uniform int wspCount; uniform int wspSelected;\n"
    fs += "".join("layout(location="+str(i)+") out uvec4 wsp"+str(i)+";\n" for i in range(8))
    fs += "void main(){vec3 v=uintBitsToFloat(wspViewBits);float eta=uintBitsToFloat(wspEtaBits);\n"
    fs += "WSPViewContext context="+("oldViewContext" if role == "old" else "waterSunSupportPrepareView")+"(v,eta);\n"
    fs += "int selectedClass=-2;uint checksum=0u;\nfor (int node=0;node<wspCount;++node){\nvec3 t=uintBitsToFloat(wspTargets[node]);int c="
    fs += "waterSunSupportClassPrepared(context,t);\n" if role == "reused" else "waterSunSupportClass(v,t,eta);\n"
    fs += "checksum+=uint(c+1)*uint(node+1);if(node==wspSelected)selectedClass=c;}\n"
    fs += "wsp0=uvec4(uint(selectedClass+1),floatBitsToUint(v));\nwsp1=uvec4(floatBitsToUint(uintBitsToFloat(wspTargets[wspSelected])),floatBitsToUint(eta));\n"
    for i, field in enumerate(INTERVALS):
        fs += f"wsp{i+2}=uvec4(uint(context.{field}.lo),uint(context.{field}.hi),uint(context.{field}.valid),"
        fs += ("checksum);\n", "uint(wspCount));\n", "uint(context.valid));\n", "0u);\n", "0u);\n", "0u);\n")[i]
    return (fs+"}\n").encode()


def receipt_sources(path):
    require(path is not None, "Frozen probe receipt is required")
    path = Path(path); data = load_json(read(path, 1024*1024))
    require(data["schema"] == "aqualumen-prepared-node-root-execution-v1", "Executed root probe receipt required")
    require(type(data["native_exit_code"]) is int and data["native_exit_code"] == 0 and
            data["native_gl_executed_by"] == "root" and data["agent_binary_is_executed_binary"] is False
            and type(data["compile_exit_code"]) is int and data["compile_exit_code"] == 0,
            "Completed root execution identity required; agent binary is not substituted")
    result = {}
    for key in ("probe_source", "binary"):
        name = data[key+"_file"]
        require(isinstance(name, str) and Path(name).name == name, "Receipt-relative basename required")
        content = read(path.parent/name, 4*1024*1024)
        require(digest(content) == data[key+"_sha256"], "Frozen "+key+" hash differs")
        result[key] = content
    for key, pin in (("old", PINS["old"]), ("prepared", PINS["prepared"]),
                     ("corpus", PINS["corpus"]), ("fixture_source", PINS["fixtureSource"]),
                     ("dependency_source", PINS["utilities"])):
        require(data[key+"_sha256"] == pin, "Probe receipt source pin differs")
    result["receipt_sha256"] = digest(read(path))
    result["native_output_directory"] = data["native_output_directory"]
    return result


def saved_cases(packet, probe_source):
    raw = read(packet/"cases.json", 1024*1024)
    require(digest(raw) == PINS["corpus"], "Frozen corpus differs")
    corpus = load_json(raw)
    require(corpus["count"] == 344 and len(corpus["cases"]) == 344, "Full frozen344 required")
    cases = [(list(int(x, 16) for x in c["inputBits"]), c["cpuClass"]) for c in corpus["cases"]]
    extra = load_json(read(packet/"additional-inputs.json", 65536))
    require(extra["schema"] == "aqualumen-prepared-node-additional-v1" and
            extra["fixtureSourceSHA256"] == PINS["fixtureSource"] and
            extra["CPUFixtureOnly"] is True and extra["physicalOracle"] is False,
            "Additional CPU fixture provenance differs")
    literal = re.search(r'const std::array<Extra,32> additional=\{\{(.*?)\}\};', probe_source, re.S)
    require(literal is not None, "Frozen32 literal source missing")
    records = re.findall(r'\{\{\{([^}]+)\}\},\s*(-1|1)\}', literal[1])
    require(len(records) == 32 and len(extra["cases"]) == 32, "Exact32 additional fixtures required")
    for i, ((bits_text, expected), record) in enumerate(zip(records, extra["cases"])):
        bits = [int(x, 16) for x in re.findall(r'0x([0-9a-f]+)u', bits_text)]
        uints(bits, 7)
        require(record == {"index": i, "origin": "invalid-boundary" if i < 24 else "signed-zero-nonunit",
                           "inputBits": bits, "cpuClass": int(expected)}, "Additional fixture literal differs")
        cases.append((bits, int(expected)))
    require(words(read(packet/"input-bits.u32", 376*7*4), 376*7) ==
            [x for bits, _ in cases for x in bits], "Packed input bits differ")
    return cases


def validate_programs(packet, result, modules, probe_source):
    programs = result["programs"]
    require(isinstance(programs, list) and len(programs) == 3, "Three actual linked programs required")
    uniform_names = ["wspViewBits", "wspTargets[0]", "wspEtaBits", "wspCount", "wspSelected"]
    vertex = b"#version 330 compatibility\nvoid main(){gl_Position=gl_Vertex;}\n"
    ids = {}
    for role, program in zip(ROLES, programs):
        require(program["role"] == role and type(program["program"]) is int and program["program"] > 0,
                "Program role/identity differs")
        require(program["attachedTypes"] == [35633, 35632], "Actual two shader types differ")
        require(program["actualOutputLocations"] == list(range(8)) and
                integers(program["actualOutputLocations"]), "Eight active output locations differ")
        actual_vs = read(packet/(role+"-attached-vertex.glsl"), 65536)
        actual_fs = read(packet/(role+"-attached-fragment.glsl"), 65536)
        expected_fs = fragment(modules["old" if role == "old" else "prepared"].decode(), role, probe_source)
        require(actual_vs == vertex and actual_fs == expected_fs, "Actual attached source differs from pinned construction")
        require(program["vertexSHA256"] == digest(actual_vs) and program["fragmentSHA256"] == digest(actual_fs),
                "Actual attached stage SHA differs")
        require(len(program["uniforms"]) == 5, "Exact five active typed inputs required")
        for i, uniform in enumerate(program["uniforms"]):
            require(integers([uniform["type"], uniform["size"], uniform["location"]]) and
                    uniform["name"] == uniform_names[i] and uniform["type"] == [36295, 36295, 5125, 5124, 5124][i]
                    and uniform["size"] == (48 if i == 1 else 1) and type(uniform["location"]) is int
                    and uniform["location"] >= 0, "Typed active uniform differs")
        ids[role] = program["program"]
    require(len(set(ids.values())) == 3, "Program identity aliases")
    return ids


def validate_storage(result):
    require(len(result["targets"]) == 8, "Eight actual integer targets required")
    textures = []
    for slot, target in enumerate(result["targets"]):
        require(integers(target.values()) and target["slot"] == slot and target["internalFormat"] == 36208 and
                target["width"] == 376 and target["height"] == 1 and target["componentType"] == 5125 and
                type(target["texture"]) is int and target["texture"] > 0 and
                target["attachmentObject"] == target["texture"], "Actual target storage/attachment differs")
        textures.append(target["texture"])
    require(len(set(textures)) == 8, "Target texture identities alias")


def validate_uploads(result, cases, ids):
    require(len(result["uploads"]) == 376*3*2, "Every role/repeat/input draw must be retained")
    ordered = iter(result["uploads"]); fbos = set()
    for role in ROLES:
        for repeat in range(2):
            for group, (start, count) in enumerate(groups(cases)):
                targets = [x for bits, _ in cases[start:start+count] for x in bits[3:6]] + [0]*(144-count*3)
                target_hash = digest(bytes_from_words(targets))
                for selected in range(count):
                    index = start+selected; upload = next(ordered); bits = cases[index][0]
                    require(integers([upload[k] for k in ("repeat", "index", "group", "count", "selected")]) and
                            (upload["role"], upload["repeat"], upload["index"], upload["group"],
                             upload["count"], upload["selected"]) == (role, repeat, index, group, count, selected),
                            "Actual draw chronology/group/count differs")
                    require(uints(upload["beforeBits"], 7) == bits and uints(upload["afterBits"], 7) == bits,
                            "Actual before/after uniform bits differ")
                    require(upload["all48TargetBitsSHA256"] == target_hash and
                            upload["allEightDrawRoutesQueriedExact"] is True, "Actual48 target upload or routing differs")
                    if selected == 0:
                        require(uints(upload["actual48TargetBits"], 144) == targets, "Actual48 target field differs")
                    else:
                        require("actual48TargetBits" not in upload, "Unexpected duplicated group payload")
                    state = upload["actualState"]
                    require(integers([state[k] for k in ("program", "drawFBO", "readFBO", "packAlignment", "pixelPackBuffer")])
                            and integers(state["viewport"]+state["drawBuffers"]+state["allEightDrawBuffers"])
                            and state["program"] == ids[role] and type(state["drawFBO"]) is int and state["drawFBO"] > 0
                            and state["readFBO"] == state["drawFBO"] and state["viewport"] == [index, 0, 1, 1]
                            and state["packAlignment"] == 1 and state["pixelPackBuffer"] == 0
                            and state["disabledRasterCapabilities"] is True
                            and state["drawBuffers"] == [36064, 36065]
                            and state["allEightDrawBuffers"] == list(range(36064, 36072)), "Actual queried draw state differs")
                    fbos.add(state["drawFBO"])
    require(len(fbos) == 1, "Framebuffer changed across fixed draws")


def audit(packet, probe_receipt=None):
    packet = Path(packet)
    if not (packet / "result.json").is_file():
        raise ValueError("Missing completed saved result")
    raw_result = read(packet/"result.json")
    result = load_json(raw_result)
    require(result.get("syntheticOnly") is not True, "Synthetic packet is not native evidence")
    require(result["schema"] == "aqualumen-prepared-node-native-v1", "Native node schema differs")
    for key, expected in (("count", 376), ("frozenCount", 344), ("additionalCount", 32),
                          ("width", 376), ("height", 1), ("targetCount", 8), ("targetInternalFormat", 36208)):
        require(type(result[key]) is int and result[key] == expected, "Exact node shape differs")
    require(result["roles"] == list(ROLES) and result["intervals"] == INTERVALS and
            result["rawByteOrder"] == "little-endian uint32; interval endpoints signed int32 bit patterns",
            "Role/interval/raw byte contract differs")
    require(result["sourceSHA256"] == PINS and result["nativeGLExecuted"] is True and
            "RTX 3080 Ti" in result["renderer"] and "NVIDIA" in result["vendor"] and
            isinstance(result["GL"], str) and result["GL"] and isinstance(result["GLSL"], str) and result["GLSL"],
            "Actual renderer/source provenance differs")
    for flag in ("physicalOracleForAdditional", "waterMainExecuted", "IrisAccepted", "shippingAccepted", "performanceAccepted"):
        require(result[flag] is False, "Unqualified acceptance promoted")
    receipt = receipt_sources(probe_receipt)
    require(receipt["native_output_directory"] == packet.name, "Receipt names a different native output")
    probe_source = receipt["probe_source"].decode()
    modules = {name: read(packet/(name+"-module.glsl"), 65536) for name in ("old", "prepared")}
    require(all(digest(content) == PINS[name] for name, content in modules.items()), "Literal helper source pin differs")
    cases = saved_cases(packet, probe_source)
    ids = validate_programs(packet, result, modules, probe_source)
    validate_storage(result); validate_uploads(result, cases, ids)
    maps = {}; raw_digests = {}
    for role in ROLES:
        maps[role] = []
        for repeat in range(2):
            capture = []
            for slot in range(8):
                name = role+"-"+("repeat-" if repeat else "")+f"slot{slot}.rgba32ui"
                data = read(packet/name, 376*4*4)
                raw_digests[name] = digest(data); capture.append(words(data, 376*4))
            maps[role].append(capture)
    require(result["rawSHA256"] == raw_digests, "Raw map digest ledger differs")
    arithmetic = validate_maps(cases, maps)
    require(len(result["results"]) == 376, "Every native result row required")
    for index, ((_, expected), recorded) in enumerate(zip(cases, result["results"])):
        origin = "frozen344" if index < 344 else "additional-invalid-boundary" if index < 368 else "additional-signed-zero-nonunit"
        require(integers([recorded["index"], recorded["cpuClass"], *recorded["classes"]]) and
                recorded == {"index": index, "origin": origin, "classes": [expected]*3, "cpuClass": expected},
                "Native summary differs from independently validated maps")
    for flag in ("rawInputEchoExact", "classesEqual", "matchesLiteralCPUClass", "allSixIntervalTriplesEqual",
                 "contextValidEqual", "groupChecksumsEqual", "repeatByteIdentical", "additionalMatchesLiteralCPUCases", "accepted"):
        require(result[flag] is True, "Producer summary contradicts raw PASS")
    require(result["status"] == "PASS", "Producer status contradicts raw PASS")
    return {"schema": "aqualumen-prepared-node-independent-v1", "status": "PASS", "accepted": True,
            **arithmetic, "nativeGLExecuted": True, "mapCount": 48, "rawBytesVerified": 48*376*4*4,
            "auditorGLExecuted": False,
            "typedUniformDrawsVerified": 2256, "actualTargetsVerified": 8, "attachedProgramsVerified": 3,
            "resultSHA256": digest(raw_result), "sourceSHA256": PINS,
            "probeSourceSHA256": digest(receipt["probe_source"]), "probeBinarySHA256": digest(receipt["binary"]),
            "probeReceiptSHA256": receipt["receipt_sha256"], "rawSHA256": raw_digests,
            "IrisAccepted": False, "waterMainAccepted": False, "physicalAdditionalAccepted": False,
            "performanceAccepted": False, "shippingAccepted": False,
            "scope": "376 fixed standalone integer classifier/interval/input identities; no rendering, speed, physical, pixel-AA or natural-water adoption."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path)
    parser.add_argument("--probe-receipt", type=Path)
    args = parser.parse_args()
    try:
        result = audit(args.packet, args.probe_receipt)
    except (ValueError, OSError, KeyError, TypeError, UnicodeError) as error:
        result = {"schema": "aqualumen-prepared-node-independent-v1",
                  "status": "INCONCLUSIVE", "accepted": False,
                  "nativeGLExecuted": False, "error": str(error)}
    print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))
    return 0 if result["accepted"] else 2 if result["status"] == "INCONCLUSIVE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
