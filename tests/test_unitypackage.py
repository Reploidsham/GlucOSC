"""Checks the .unitypackage / .zip builder (standard library only). Run: python3 tests/test_unitypackage.py"""
import hashlib
import os
import sys
import tarfile
import tempfile
import zipfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import make_unitypackage as mu  # noqa: E402

FAILS = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))
    if not ok:
        FAILS.append(name)


def sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
    mu.main(["--version", "9.9.9", "--out-dir", a])
    mu.main(["--version", "9.9.9", "--out-dir", b])
    pkg_a = os.path.join(a, "GlucOSC-Unity-9.9.9.unitypackage")
    zip_a = os.path.join(a, "GlucOSC-Unity-9.9.9.zip")
    check("unitypackage is reproducible", sha(pkg_a) == sha(os.path.join(b, "GlucOSC-Unity-9.9.9.unitypackage")))
    check("zip is reproducible", sha(zip_a) == sha(os.path.join(b, "GlucOSC-Unity-9.9.9.zip")))

    with tarfile.open(pkg_a, "r:gz") as tar:
        members = tar.getmembers()
        names = [m.name for m in members]
        by_guid = {}
        for m in members:
            g, part = m.name.split("/", 1)
            by_guid.setdefault(g, {})[part] = tar.extractfile(m).read()

    check("every entry is <32 hex guid>/<part>", all(len(n.split("/")[0]) == 32 and n.count("/") == 1 for n in names))
    check("no absolute or parent paths", all(not n.startswith("/") and ".." not in n for n in names))
    check("only regular files in tar", all(m.isfile() for m in members))
    paths = {g: parts["pathname"].decode() for g, parts in by_guid.items()}
    check("every guid has pathname + meta", all("pathname" in p and "asset.meta" in p for p in by_guid.values()))
    check("all paths under Assets/GlucoseDevice", all(p == "Assets/GlucoseDevice" or p.startswith("Assets/GlucoseDevice/") for p in paths.values()))
    check("guid in meta matches folder", all(f"guid: {g}".encode() in parts["asset.meta"] for g, parts in by_guid.items()))
    check("guids are derived from paths (stable)", all(mu.guid_for(p) == g for g, p in paths.items()))

    folders = {p for g, p in paths.items() if b"folderAsset: yes" in by_guid[g]["asset.meta"]}
    files = {p for g, p in paths.items() if "asset" in by_guid[g]}
    check("folders have no asset part", not (folders & files))
    for needed in ["Assets/GlucoseDevice/Editor/GlucoseDeviceBuilder.cs", "Assets/GlucoseDevice/Textures/lcd_words.png",
                   "Assets/GlucoseDevice/Models/GD_Shell.obj", "Assets/GlucoseDevice/PARAMETERS.txt"]:
        check(f"contains {needed}", needed in files)
    for needed in ["Assets/GlucoseDevice", "Assets/GlucoseDevice/Editor", "Assets/GlucoseDevice/Textures",
                   "Assets/GlucoseDevice/Textures/Alternatives"]:
        check(f"folder entry {needed}", needed in folders)
    parents_ok = all(p.rsplit("/", 1)[0] in folders for p in files)
    check("every file's parent folder is in the package", parents_ok)
    src = os.path.join(mu.SOURCE, "Editor", "GlucoseDeviceBuilder.cs")
    g = mu.guid_for("Assets/GlucoseDevice/Editor/GlucoseDeviceBuilder.cs")
    with open(src, "rb") as fh:
        check("file bytes copied unchanged", by_guid[g]["asset"] == fh.read())
    check("no preview images or generated folder", not any("preview_" in p or "/Generated" in p for p in paths.values()))

    with zipfile.ZipFile(zip_a) as zf:
        zn = zf.namelist()
    check("zip holds the GlucoseDevice folder", all(n.startswith("GlucoseDevice/") for n in zn) and len(zn) == len(files), zn[:3])

try:
    mu.main(["--version", "../evil", "--out-dir", tempfile.gettempdir()])
    check("bad version rejected", False)
except SystemExit:
    check("bad version rejected", True)

print()
print("FAILURES:", FAILS if FAILS else "none")
sys.exit(1 if FAILS else 0)
