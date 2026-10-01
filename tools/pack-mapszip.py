#!/usr/bin/env python3
"""Pack a mapspack folder into a .mapszip, every entry stored as it is.

    tools/pack-mapszip.py Trip.mapszip Trip.mapspack
"""
import hashlib
import json
import pathlib
import struct
import sys

MAGIC = b"RKZS"
VERSION = 2


def pack(out, entries):
    """`entries` is `(path, bytes)`: a mapspack's files, `map.mapson` and `package.json` first."""
    manifest = {"entries": [{"path": path, "size": len(body), "compressedSize": len(body),
                             "sha256": hashlib.sha256(body).hexdigest(), "stored": True}
                            for path, body in entries]}
    head = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    with open(out, "wb") as f:
        f.write(MAGIC + bytes([VERSION]) + struct.pack(">I", len(head)) + head)
        for _path, body in entries:
            f.write(body)


def mapspack_entries(folder):
    folder = pathlib.Path(folder)
    lead = ["map.mapson", "package.json"]
    rest = sorted(p.relative_to(folder).as_posix() for p in folder.rglob("*")
                  if p.is_file() and not p.name.startswith(".")
                  and p.relative_to(folder).as_posix() not in lead)
    return [(path, (folder / path).read_bytes()) for path in lead + rest]


def main(args):
    if len(args) != 2:
        raise SystemExit(__doc__)
    pack(args[0], mapspack_entries(args[1]))


if __name__ == "__main__":
    main(sys.argv[1:])
