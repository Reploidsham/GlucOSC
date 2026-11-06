"""Offline checks for packaging/lock_deps.py (fake PyPI + fake pip). Run: python3 tests/test_lock_deps.py"""
import datetime as dt
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "packaging"))
import lock_deps as L  # noqa: E402

FAILS = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))
    if not ok:
        FAILS.append(name)


NOW = dt.datetime(2026, 11, 5, tzinfo=dt.timezone.utc)


def days_ago(n):
    return (NOW - dt.timedelta(days=n)).isoformat().replace("+00:00", "Z")


# name -> version -> (age in days, deps, platforms or None for all)
WIN = 'winonly; sys_platform == "win32"'
LIN = 'linuxonly; sys_platform == "linux"'
INDEX = {
    "toolkit": {"1.0": (100, ["helper"], None), "1.1": (20, ["helper"], None), "1.2": (3, ["helper"], None),
                "2.0rc1": (30, [], None)},
    "builder": {"6.0": (60, ["helper", WIN, LIN], None), "6.1": (5, ["helper", WIN, LIN], None)},
    "helper": {"0.9": (400, [], None), "1.0": (2, [], None)},  # newest helper is too young
    "winonly": {"3.0": (90, [], {"win32"})},
    "linuxonly": {"1.0": (90, [], None)},
}


def sha_for(name, ver, target):
    return (name + ver + target).encode().hex()[:64].ljust(64, "0")


LATE_FILES = {}  # (name, version, target) -> age in days of a wheel added to the release later


def fake_fetch(url):
    parts = url[len(L.PYPI) + 1:].split("/")
    name = parts[0]
    if len(parts) == 2:  # project json
        return {"info": {"name": name}, "releases": {
            v: [{"upload_time_iso_8601": days_ago(age), "yanked": False}] for v, (age, _d, _p) in INDEX[name].items()}}
    ver = parts[1]
    age = INDEX[name][ver][0]
    files = [{"filename": f"{name}-{ver}-{t}.whl", "digests": {"sha256": sha_for(name, ver, t)},
              "upload_time_iso_8601": days_ago(LATE_FILES.get((name, ver, t), age))} for t in L.TARGETS]
    return {"info": {"name": name, "yanked": False}, "urls": files}


def fake_pip(target, reqs, constraints):
    """Behaves like real pip on a Linux host: markers are judged by the HOST, not the target."""
    from pip._vendor.packaging.requirements import Requirement
    pins = {}
    for r in reqs:
        rq = Requirement(r)
        pins[rq.name] = str(rq.specifier).lstrip("=") if str(rq.specifier).startswith("==") else None
    banned = {tuple(c.split("!=")) for c in constraints}
    chosen = {}

    def pick(name):
        if name in chosen:
            return
        options = [v for v, (_a, _d, plats) in INDEX[name].items()
                   if (name, v) not in banned and not L._is_prerelease(v) and (plats is None or target in plats)]
        if pins.get(name):
            options = [v for v in options if v == pins[name]]
        if not options:
            raise SystemExit(f"fake pip: no {name} for {target}")
        v = max(options, key=L._version_key)
        chosen[name] = v
        for dep in INDEX[name][v][1]:
            rq = Requirement(dep)
            if rq.marker is None or rq.marker.evaluate(L.TARGET_ENV["linux"]):  # host is Linux
                pick(rq.name)

    for name in pins:
        pick(name)
    return [{"metadata": {"name": n, "version": v, "requires_dist": INDEX[n][v][1]},
             "download_info": {"url": f"https://files/{n}-{v}-{target}.whl",
                               "archive_info": {"hashes": {"sha256": sha_for(n, v, target)}}}}
            for n, v in chosen.items()]


# ---- top-level choice
check("newest old-enough final release", L.newest_old_enough(fake_fetch(f"{L.PYPI}/toolkit/json"), NOW, 14) == "1.1")
check("prereleases skipped", L.newest_old_enough(fake_fetch(f"{L.PYPI}/toolkit/json"), NOW, 1) == "1.2")
check("longer cooldown goes further back", L.newest_old_enough(fake_fetch(f"{L.PYPI}/toolkit/json"), NOW, 50) == "1.0")

# ---- full resolution
results, reqs, warnings = L.resolve([("toolkit", None), ("builder", None)], fake_fetch, fake_pip, NOW, 14)
check("top-level picks respect cooldown", reqs == ["toolkit==1.1", "builder==6.0"], reqs)
check("young transitive dependency pushed back", results["linux"]["helper"][1] == "0.9" and results["win32"]["helper"][1] == "0.9",
      results["linux"].get("helper"))
check("no warnings", warnings == [], warnings)
rows = L.merge(results)
names = {r[0]: r for r in rows}
check("windows-only dependency found even though host is Linux", "winonly" in results["win32"] and "winonly" not in results["linux"])
check("linux-only dependency dropped from the Windows set", "linuxonly" in results["linux"] and "linuxonly" not in results["win32"])
check("windows-only dependency gets a marker", names["winonly"][2] == 'sys_platform == "win32"', names["winonly"])
check("linux-only dependency gets a marker", names["linuxonly"][2] == 'sys_platform == "linux"', names["linuxonly"])
check("shared dependency has no marker", names["helper"][2] is None)
check("one hash per platform file", len(names["toolkit"][3]) == 2, names["toolkit"][3])

text = L.render(rows, "2026-11-05", 14, warnings)
check("header mark present", text.startswith(L.HEADER_MARK))
check("hash continuation lines well formed", "toolkit==1.1 \\\n    --hash=sha256:" in text and text.rstrip().endswith(names["winonly"][3][-1]))
check("marker line format", 'winonly==3.0 ; sys_platform == "win32" \\' in text)

# ---- pinned young top-level only warns
results, reqs, warnings = L.resolve([("toolkit", "1.2"), ("builder", None)], fake_fetch, fake_pip, NOW, 14)
check("pinned young version kept with warning", reqs[0] == "toolkit==1.2" and any("toolkit==1.2" in w for w in warnings), (reqs, warnings))

# ---- hash mismatch is fatal
def bad_fetch(url):
    d = fake_fetch(url)
    for f in d.get("urls", []):
        f["digests"]["sha256"] = "0" * 64
    return d


try:
    L.resolve([("toolkit", None)], bad_fetch, fake_pip, NOW, 14)
    check("hash mismatch rejected", False)
except SystemExit as e:
    check("hash mismatch rejected", "Hash mismatch" in str(e), e)

# ---- a new wheel added to an OLD release must not slip past the cooldown
LATE_FILES[("helper", "0.9", "win32")] = 1
try:
    L.resolve([("toolkit", None)], fake_fetch, fake_pip, NOW, 14)
    check("late-added wheel in old release rejected", False)
except SystemExit as e:
    # Either way (no older version left, or pip finds nothing) the young file is never locked.
    check("late-added wheel in old release rejected", "Could not find versions" in str(e) or "no helper" in str(e), e)
LATE_FILES.clear()

# ---- file pip picked is unknown to PyPI -> stop
def missing_fetch(url):
    d = fake_fetch(url)
    d["urls"] = [f for f in d.get("urls", []) if "win32" not in f["filename"]] if "urls" in d else d.get("urls")
    if d.get("urls") is None:
        d.pop("urls", None)
    return d


try:
    L.resolve([("toolkit", None)], missing_fetch, fake_pip, NOW, 14)
    check("unknown file name rejected", False)
except SystemExit as e:
    check("unknown file name rejected", "does not list" in str(e), e)

# ---- extras are followed
items = [
    {"metadata": {"name": "parent", "version": "1", "requires_dist": ["child[fast]>=1"]}},
    {"metadata": {"name": "child", "version": "1", "requires_dist": ['speedup; extra == "fast"', 'never; extra == "slow"']}},
]
keep, missing = L.target_closure(items, ["parent"], "linux")
check("extra dependency reported missing", missing == ["speedup"], (keep, missing))
items.append({"metadata": {"name": "speedup", "version": "1", "requires_dist": []}})
keep, missing = L.target_closure(items, ["parent"], "linux")
check("extra dependency kept, unrequested extra ignored", keep == {"parent", "child", "speedup"} and missing == [], (keep, missing))
keep, missing = L.target_closure(
    [{"metadata": {"name": "a", "version": "1", "requires_dist": ['b[x]; sys_platform == "win32"']}}], ["a"], "win32")
check("missing requirement keeps its extras", missing == ["b[x]"], missing)

# ---- .in parsing
with tempfile.NamedTemporaryFile("w", suffix=".in", delete=False) as fh:
    fh.write("# comment\nPySide6-Essentials\npyinstaller==6.0.0  # held\n\n")
check("in-file parsing", L.read_in_file(fh.name) == [("PySide6-Essentials", None), ("pyinstaller", "6.0.0")])
with open(fh.name, "w") as f2:
    f2.write("pyinstaller>=6\n")
try:
    L.read_in_file(fh.name)
    check("ranges rejected in .in", False)
except SystemExit:
    check("ranges rejected in .in", True)
os.unlink(fh.name)

# ---- real report shape (pip 23+ style 'hashes' and older 'hash')
rep = L.parse_report([
    {"metadata": {"name": "A_b", "version": "1"}, "download_info": {"url": "u/a.whl", "archive_info": {"hash": "sha256=" + "a" * 64}}},
    {"metadata": {"name": "c", "version": "2"}, "download_info": {"url": "u/c.whl", "archive_info": {"hashes": {"sha256": "c" * 64}}}},
])
check("report parsing, both hash styles, names normalized", rep["a-b"][2] == "a" * 64 and rep["c"][2] == "c" * 64, rep)

print()
print("FAILURES:", FAILS if FAILS else "none")
sys.exit(1 if FAILS else 0)
