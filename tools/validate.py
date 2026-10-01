#!/usr/bin/env python3
"""Validate mapson, servson, mapspack, mapszip, mapsaar and maps.json files against their schemas.

    pip install jsonschema
    tools/validate.py my-maps.mapson my-servers.servson Trip.mapspack Trip.mapszip maps.json
    tools/validate.py --expect-invalid tests/invalid/*

Each file is checked against the schema its name says: by extension, or `maps.json` /
`*.maps.json` for the catalog and `package.json` / `*.package.json` for a mapspack manifest.
A folder is read as a mapspack; a .mapszip or .mapsaar is unpacked into one first.
Exits 1 when any file does not come out as expected.
"""
import argparse
import hashlib
import json
import pathlib
import shutil
import struct
import subprocess
import sys
import tempfile

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCHEMAS = ROOT / "schema" / "v1"
NAMES = ("mapson", "servson", "mapszip", "mapspack", "maps")
SUFFIXES = {".mapson": "mapson", ".rikimap": "mapson", ".servson": "servson",
            ".mapszip": "mapszip-file", ".mapsaar": "mapsaar-file"}
MAGIC = b"RKZS"
CONTAINER_VERSIONS = (1, 2)

try:
    import liblzfse
except ImportError:
    liblzfse = None


def load(name):
    return json.loads((SCHEMAS / f"{name}.schema.json").read_text(encoding="utf-8"))


def validators(override=None):
    schemas = {name: load(name) for name in NAMES}
    # servson, mapspack and maps $ref mapson's $defs; registered under their real ids
    registry = Registry().with_resources(
        (schema["$id"], Resource.from_contents(schema)) for schema in schemas.values())
    if override:
        schema = json.loads(pathlib.Path(override).read_text(encoding="utf-8"))
        schemas = {name: schema for name in schemas}
    made = {}
    for name, schema in schemas.items():
        Draft202012Validator.check_schema(schema)
        made[name] = Draft202012Validator(schema, registry=registry)
    return made


def kind_of(path):
    name = path.name.lower()
    if path.is_dir():
        return "mapspack-dir"
    if name in ("maps.json", "maps-test.json") or name.endswith(".maps.json"):
        return "maps"
    if name == "package.json" or name.endswith(".package.json"):
        return "mapspack"
    return SUFFIXES.get(path.suffix.lower(), "mapson")


def schema_issues(validator, document, where=""):
    found = sorted(validator.iter_errors(document), key=lambda e: list(e.absolute_path))
    return [f"{where}{e.json_path}: {e.message}" for e in found]


def json_issues(validator, data, where=""):
    try:
        document = json.loads(data)
    except ValueError as error:
        return [f"{where}not readable JSON: {error}"]
    return schema_issues(validator, document, where)


def mapszip_issues(checking, data):
    """The container: magic, version, manifest and each entry; then the mapspack it holds."""
    if len(data) < 9 or data[:4] != MAGIC:
        return ["not a mapszip: no RKZS magic"]
    if data[4] not in CONTAINER_VERSIONS:
        return [f"container version {data[4]} is not one of {CONTAINER_VERSIONS}"]
    (length,) = struct.unpack(">I", data[5:9])
    if 9 + length > len(data):
        return ["manifest runs past the end of the file"]
    try:
        manifest = json.loads(data[9:9 + length])
    except ValueError as error:
        return [f"manifest is not JSON: {error}"]
    found = schema_issues(checking["mapszip"], manifest, "manifest ")
    if found:
        return found
    offset = 9 + length
    bodies = {}
    for entry in manifest["entries"]:
        raw = data[offset:offset + entry["compressedSize"]]
        offset += entry["compressedSize"]
        if len(raw) < entry["compressedSize"]:
            return found + [f"{entry['path']}: payload ends early"]
        body = unpacked(entry, raw)
        if body is None:
            continue
        if len(body) != entry["size"] or hashlib.sha256(body).hexdigest() != entry["sha256"]:
            found.append(f"{entry['path']}: size or sha256 differs from the manifest")
        else:
            bodies[entry["path"]] = body
    if offset != len(data):
        found.append(f"{len(data) - offset} bytes after the last entry")
    if found or len(bodies) < len(manifest["entries"]):
        return found
    with tempfile.TemporaryDirectory() as folder:
        for path, body in bodies.items():
            target = pathlib.Path(folder, path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
        return mapspack_issues(checking, pathlib.Path(folder))


def unpacked(entry, raw):
    if entry.get("stored"):
        return raw
    if liblzfse is None:
        print(f"     note: {entry['path']} is LZFSE-packed; pip install pyliblzfse to check the mapspack")
        return None
    return liblzfse.decompress(raw)


def mapspack_issues(checking, folder):
    """A mapspack: map.mapson, package.json, and every file the manifest names."""
    found = []
    for name in ("map.mapson", "package.json"):
        if not (folder / name).is_file():
            found.append(f"no {name}")
    if found:
        return found
    mapson_data = (folder / "map.mapson").read_bytes()
    found += json_issues(checking["mapson"], mapson_data, "map.mapson ")
    manifest_data = (folder / "package.json").read_bytes()
    found += json_issues(checking["mapspack"], manifest_data, "package.json ")
    if found:
        return found
    mapson = json.loads(mapson_data)
    maps = mapson["maps"] if "maps" in mapson else [mapson]
    layer_ids = {str(layer.get("id", "")).upper() for one in maps for layer in one.get("stack", [])}
    for item in json.loads(manifest_data)["items"]:
        if item["layerID"].upper() not in layer_ids:
            found.append(f"package.json: layer {item['layerID']} is in no map of map.mapson")
        for path in ([item["tiles"]] if "tiles" in item else []) + item["files"]:
            if not (folder / path).is_file():
                found.append(f"package.json names {path}, which is not in the mapspack")
    return found


def mapsaar_issues(checking, path):
    """Unpacked with Apple's `aa`, which only macOS has."""
    tool = shutil.which("aa")
    if not tool:
        return ["a .mapsaar is an Apple Archive: unpack it with `aa extract` and pass the folder"]
    with tempfile.TemporaryDirectory() as folder:
        done = subprocess.run([tool, "extract", "-i", str(path), "-d", folder],
                              capture_output=True, text=True)
        if done.returncode:
            return [f"not an Apple Archive: {done.stderr.strip()}"]
        return mapspack_issues(checking, pathlib.Path(folder))


def issues(checking, path):
    kind = kind_of(path)
    if kind == "mapspack-dir":
        return mapspack_issues(checking, path)
    if kind == "mapsaar-file":
        return mapsaar_issues(checking, path)
    try:
        data = path.read_bytes()
    except OSError as error:
        return [f"not readable: {error}"]
    if kind == "mapszip-file":
        return mapszip_issues(checking, data)
    return json_issues(checking[kind], data)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("files", nargs="+")
    parser.add_argument("--expect-invalid", action="store_true",
                        help="every file must FAIL validation")
    parser.add_argument("--schema", help="check every JSON file against this schema instead")
    args = parser.parse_args()

    checking = validators(args.schema)

    failed = False
    for name in args.files:
        found = issues(checking, pathlib.Path(name))
        if args.expect_invalid:
            ok = bool(found)
            print(f"{'ok  ' if ok else 'FAIL'} {name}: "
                  f"{found[0] if found else 'validated, but should not have'}")
        else:
            ok = not found
            print(f"{'ok  ' if ok else 'FAIL'} {name}")
            for line in found:
                print(f"     {line}")
        failed |= not ok
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
