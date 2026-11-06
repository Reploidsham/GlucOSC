#!/usr/bin/env python3
"""Pack unity/GlucoseDevice into a .unitypackage and a plain .zip (standard library only).

Run from the repository root:
    python3 tools/make_unitypackage.py --out-dir dist

Writes:
    dist/GlucOSC-Unity.unitypackage   (double-click / Assets > Import Package > Custom Package)
    dist/GlucOSC-Unity.zip            (same files, for copying into Assets by hand)
With --version 1.2.3 the names become GlucOSC-Unity-1.2.3.*

Both files are reproducible: the same input gives the same output (fixed timestamps, sorted
entries, no user names), so anyone can rebuild them and compare checksums. Compression can differ
between Python builds (zlib versions), so compare using the same Python version as the release.

GUIDs are derived from each file's path, so they stay the same from release to release and
Unity treats a newer package as an update of the same assets.
"""
from __future__ import annotations

import argparse
import gzip
import io
import os
import sys
import tarfile
import uuid
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, ".."))
SOURCE = os.path.join(REPO, "unity", "GlucoseDevice")
UNITY_ROOT = "Assets/GlucoseDevice"

# Fixed namespace so GUIDs never change between machines or releases. Do not edit.
GUID_NAMESPACE = uuid.UUID("6b0c3a52-7d1e-4f0a-9a57-2c1e9f4d8b31")
FIXED_TIME = 1704067200  # 2024-01-01 00:00:00 UTC, used for every timestamp
SKIP_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}
SKIP_SUFFIXES = (".meta", ".pyc")


def guid_for(unity_path: str) -> str:
    return uuid.uuid5(GUID_NAMESPACE, "GlucOSC:" + unity_path).hex


def file_meta(guid: str) -> str:
    # Minimal meta: Unity fills in default importer settings on import.
    # The builder window fixes texture and model import settings itself.
    return f"fileFormatVersion: 2\nguid: {guid}\n"


def folder_meta(guid: str) -> str:
    return (f"fileFormatVersion: 2\nguid: {guid}\nfolderAsset: yes\n"
            "DefaultImporter:\n  externalObjects: {}\n  userData: \n  assetBundleName: \n  assetBundleVariant: \n")


def collect(source: str = SOURCE):
    """Return (folders, files) as sorted lists of (unity_path, disk_path)."""
    if not os.path.isdir(source):
        raise SystemExit(f"Unity folder not found: {source}")
    folders = [(UNITY_ROOT, source)]
    files = []
    for dirpath, dirnames, filenames in os.walk(source):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith(".") and d != "__pycache__")
        rel_dir = os.path.relpath(dirpath, source).replace(os.sep, "/")
        unity_dir = UNITY_ROOT if rel_dir == "." else f"{UNITY_ROOT}/{rel_dir}"
        for d in dirnames:
            folders.append((f"{unity_dir}/{d}", os.path.join(dirpath, d)))
        for name in sorted(filenames):
            if name in SKIP_NAMES or name.endswith(SKIP_SUFFIXES) or name.startswith("."):
                continue
            files.append((f"{unity_dir}/{name}", os.path.join(dirpath, name)))
    return sorted(folders), sorted(files)


def _add_bytes(tar: tarfile.TarFile, name: str, data: bytes) -> None:
    info = tarfile.TarInfo(name)
    info.size = len(data)
    info.mtime = FIXED_TIME
    info.mode = 0o644
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    tar.addfile(info, io.BytesIO(data))


def build_unitypackage(out_path: str, source: str = SOURCE) -> int:
    folders, files = collect(source)
    entries = []
    for unity_path, _disk in folders:
        g = guid_for(unity_path)
        entries.append((g, unity_path, None, folder_meta(g)))
    for unity_path, disk in files:
        g = guid_for(unity_path)
        with open(disk, "rb") as fh:
            entries.append((g, unity_path, fh.read(), file_meta(g)))
    guids = [e[0] for e in entries]
    if len(set(guids)) != len(guids):
        raise SystemExit("GUID collision; this should never happen")

    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.USTAR_FORMAT) as tar:
        for g, unity_path, data, meta in sorted(entries):
            if data is not None:
                _add_bytes(tar, f"{g}/asset", data)
            _add_bytes(tar, f"{g}/asset.meta", meta.encode("utf-8"))
            _add_bytes(tar, f"{g}/pathname", unity_path.encode("utf-8"))
    with open(out_path, "wb") as out:
        # mtime=0 and no file name inside the gzip header keep the output byte-identical.
        with gzip.GzipFile(filename="", mode="wb", fileobj=out, mtime=0, compresslevel=9) as gz:
            gz.write(raw.getvalue())
    return len(entries)


def build_zip(out_path: str, source: str = SOURCE) -> int:
    _folders, files = collect(source)
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for unity_path, disk in files:
            arc = unity_path[len("Assets/"):]  # zip holds the GlucoseDevice folder itself
            info = zipfile.ZipInfo(arc, date_time=(2024, 1, 1, 0, 0, 0))
            info.external_attr = 0o644 << 16
            info.create_system = 3  # same value on every OS, so the bytes match
            info.compress_type = zipfile.ZIP_DEFLATED
            with open(disk, "rb") as fh:
                zf.writestr(info, fh.read())
    return len(files)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--version", default="", help="optional version text added to the file names")
    p.add_argument("--out-dir", default=os.path.join(REPO, "dist"))
    p.add_argument("--source", default=SOURCE, help=argparse.SUPPRESS)
    a = p.parse_args(argv)
    if not all(c.isalnum() or c in ".-_+" for c in a.version):
        raise SystemExit("version may only contain letters, digits and . - _ +")
    os.makedirs(a.out_dir, exist_ok=True)
    stem = "GlucOSC-Unity" + (f"-{a.version}" if a.version else "")
    pkg = os.path.join(a.out_dir, stem + ".unitypackage")
    zp = os.path.join(a.out_dir, stem + ".zip")
    n = build_unitypackage(pkg, a.source)
    m = build_zip(zp, a.source)
    print(f"wrote {pkg} ({n} entries)")
    print(f"wrote {zp} ({m} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
