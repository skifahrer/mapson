# schemas

The file formats of Riki Maps and the skifahrer/maptiles pipeline, as JSON Schema 2020-12.
This repository is their only home: the app and the pipeline pull the schemas from here when
they need them and carry no copy.

Three kinds of file, each holding one or more of what it is for:

| Format | What it holds | Schema |
|---|---|---|
| [`.mapson`](#mapson) | one or more maps as JSON: settings, layers, their networks and styles; no downloaded data | [`mapson.schema.json`](schema/v1/mapson.schema.json) |
| [`.servson`](#servson) | one or more servers as JSON, with their subservers, everything they published and, when chosen, their credentials | [`servson.schema.json`](schema/v1/servson.schema.json) |
| [`.mapsack`](#mapsack) | maps with their downloaded data: a mapson plus tiles and feature files, as a folder | [`mapsack.schema.json`](schema/v1/mapsack.schema.json) (its `package.json`) |

A mapsack travels as one file, in either of two archives:

| Archive | What it is | Schema |
|---|---|---|
| [`.mapszip`](#mapszip) | a mapsack in Riki Maps' own container, readable without unpacking | [`mapszip.schema.json`](schema/v1/mapszip.schema.json) (its manifest) |
| [`.mapsaar`](#mapsaar) | a mapsack as an Apple Archive, which any Mac unpacks | none of its own: it is the mapsack's |

And one the pipeline publishes:

| | | |
|---|---|---|
| [`maps.json`](#mapsjson) | the region catalog skifahrer/maptiles publishes | [`maps.schema.json`](schema/v1/maps.schema.json) |

Every schema is published at
`https://raw.githubusercontent.com/skifahrer/schemas/master/schema/v1/<name>.schema.json`.

## mapson

Maps + JSON. One map, or several, as JSON: each map's settings, its layers and how each is
fetched (addresses, request setups, proxies, keys when chosen) and drawn, and its styles. It
holds no downloaded data; a [mapsack](#mapsack) does. Riki Maps reads and writes it as
`.mapson`, and anyone else can too.

| | |
|---|---|
| Schema | [`schema/v1/mapson.schema.json`](schema/v1/mapson.schema.json) (JSON Schema 2020-12) |
| Schema URL | `https://raw.githubusercontent.com/skifahrer/schemas/master/schema/v1/mapson.schema.json` |
| Examples | [`examples/minimal.mapson`](examples/minimal.mapson), [`examples/full.mapson`](examples/full.mapson), [`examples/two-maps.mapson`](examples/two-maps.mapson) |
| Media | UTF-8 JSON, extension `.mapson` (`.rikimap` is the legacy name), UTI `com.rikimaps.mapson` |

### Shape

```jsonc
{
  "$schema": "https://raw.githubusercontent.com/skifahrer/schemas/master/schema/v1/mapson.schema.json",
  "_schemaVersion": 1,
  "id": "0834FFB7-67BA-4327-87F2-E18AEE11B2FC",
  "name": "OpenStreetMap",
  "isBuiltIn": false, "drawsRegions": false, "isOnlineOnly": false,
  "stack": [ /* layers, index 0 drawn first */ ],
  "styles": [ /* may be empty */ ]
}
```

Every object in the schema lists its **required** keys in `required`. Every other key it
names is **optional**. Here are the required ones:

| Object | Required keys |
|---|---|
| map (root, or each of `maps[]`) | `id` `name` `stack` `styles` `isBuiltIn` `drawsRegions` `isOnlineOnly` |
| collection (root with `maps`) | `_schemaVersion` (2) `maps` |
| layer (`stack[]`) | `id` `name` `symbol` `role` `opacity` `source` `isEnabled` |
| layer `source` | exactly one of `region` `url` `files` `apple` |
| `source.url` | `template` `maxZoom` `format` `attribution` |
| style (`styles[]`) | `id` `name` `symbol` `origin` `notes` `adjustments` |
| style `origin` | exactly one of `builtIn` `document` `arrangement` (`{}`) |
| style `adjustments` | `lineWidthScale` `labelSizeScale` |
| credit (`credits[]`) | `holder` |

The schema lists every nested object: Esri services, API readings, renderers,
arrangements and the rest.

### Several maps

A file with `maps` is a collection. Each entry is a whole map, exactly as it would be written
alone, signature and sidecars included:

```jsonc
{
  "$schema": "https://raw.githubusercontent.com/skifahrer/schemas/master/schema/v1/mapson.schema.json",
  "_schemaVersion": 2,
  "maps": [ { /* a map */ }, { /* another */ } ],
  "rikiServiceProxies": { /* for every map; a map's own wins */ },
  "rikiHeaders": { /* the same */ }
}
```

A collection is `_schemaVersion` 2 and has at least one map. A writer with one map writes it
alone, as version 1, so readers that know only one map still open it.

### Value rules

- **Ids** are UUID strings such as `0834FFB7-67BA-4327-87F2-E18AEE11B2FC`. Either case works.
- **Pictures** (`iconPicture`, `imageData`) are standard base64 with padding.
- **Dates** are numbers: seconds since 2001-01-01T00:00:00Z.
- **Integers** (zooms, counts, bytes) must be whole numbers. `18.5` is refused.
- **Enums** (`role`, `format`, `overlay`, …) are closed. A value outside the list makes
  the whole file unreadable.
- **Optional means absent.** Leave a key out instead of writing `null`.
- **Unknown keys are allowed** and readers ignore them. A reader that re-exports a file
  may drop them.

### Signing is optional

`_signature` is optional. Riki Maps signs its own exports with a keyed hash so its import
sheet can say *"Verified · exported by Riki Maps"*. The mark is a UI hint, not security.

- A file without `_signature` is fully valid. It imports normally, just without the
  badge. Other writers should leave the key out.
- Any change to a signed file breaks the mark. The file still imports, only as
  unverified, so an editor should remove `_signature`.
- The signature covers the map, including `$schema`. It excludes `_schemaVersion`,
  `_signature` and the `riki*` sidecars (`rikiSharedFeature`, `rikiServiceProxies`,
  `rikiHeaders`), so those can change without touching it.
- In a collection each map carries its own signature; a collection is verified only when
  every map in it is.

### Versioning

- `_schemaVersion` is the format version. If it is missing, the file is version 0 (written
  before versioning), which reads the same as 1. A collection is 2.
- Adding an optional key does **not** change the version.
- The version goes up only when an older reader would misread a file. That change gets
  a new `schema/vN/` file. A reader must refuse a version newer than it knows instead of
  guessing, and Riki Maps does.
- `$schema` names the schema a file follows. It is optional; writers should set it.

## servson

Servers + JSON. A `.servson` holds one or more saved map servers instead of maps: their
addresses, kinds, request settings, their subservers (Esri folders and the services in them, to
any depth), and everything they published when last read (layers, facts, zooms, bounds), each
with the time of that read. With credentials when the writer chooses. It is a mapson extension: its schema
reuses mapson's `$defs` by relative `$ref`.

| | |
|---|---|
| Schema | [`schema/v1/servson.schema.json`](schema/v1/servson.schema.json) |
| Schema URL | `https://raw.githubusercontent.com/skifahrer/schemas/master/schema/v1/servson.schema.json` |
| Examples | [`examples/minimal.servson`](examples/minimal.servson), [`examples/full.servson`](examples/full.servson) |
| Media | UTF-8 JSON, extension `.servson`, UTI `com.rikimaps.servson` |

```jsonc
{
  "$schema": "https://raw.githubusercontent.com/skifahrer/schemas/master/schema/v1/servson.schema.json",
  "_schemaVersion": 1,
  "exportedAt": 812400000,
  "includesCredentials": false,
  "servers": [ /* in the writer's order */ ],
  "rikiHeaders": { /* host → header → value, only when includesCredentials */ },
  "rikiServiceProxies": { /* host → proxy prefix */ }
}
```

| Object | Required keys |
|---|---|
| root | `exportedAt` `includesCredentials` `servers` |
| server (`servers[]`) | `id` `name` `kind` `url` `headerNames` `symbol` `format` `maxZoom` `attribution` `allowsOffline` `layers` `facts` `addedAt` |
| layer (`layers[]`) | `id` `name` `supportsQuery` |
| service (`publishedServices[]`, `held[]`) | `id` `name` `type` `isFolder` `isDrawn` `layers` `facts` `held` `summary` |
| fact | `name` `value` |

`kind` is one of `arcgis` `tilejson` `tiles` `mapproxy` `api`. The value rules above apply.

**Credentials are the writer's choice.** With `includesCredentials` false, the file has no
`rikiHeaders`. Query keys such as `token`, `key` or `api_key` are also removed from every
address. Header *names* stay, so the reader knows which values it must supply. A reader should
name the hosts whose keys a file carries before importing it. It should also never replace a
value the user already holds.

## mapsack

Maps + sack: maps with the data they downloaded, as a folder. Its `map.mapson` is a mapson, one
map or several; beside it are each layer's tiles and the files its layers read (features,
GPX, GeoJSON, MBTiles…), and `package.json` says which belongs to which layer.

| | |
|---|---|
| Schema | [`schema/v1/mapsack.schema.json`](schema/v1/mapsack.schema.json), for `package.json` |
| Example | [`examples/huts.mapsack/`](examples/huts.mapsack) |
| Media | a folder, extension `.mapsack`, UTI `com.rikimaps.mapsack` (a package: Files shows one item) |

```
map.mapson          the maps, a mapson
package.json        which file belongs to which layer
<layer>.pmtiles     one per tile store, named after the layer that first reads it
files/<name>        files the layers read
```

```jsonc
{
  "$schema": "https://raw.githubusercontent.com/skifahrer/schemas/master/schema/v1/mapsack.schema.json",
  "version": 1,
  "items": [
    { "layerID": "…", "cacheKey": "…", "tiles": "Trails.pmtiles", "files": [] },
    { "layerID": "…", "cacheKey": "…", "files": ["files/huts.geojson"] }
  ]
}
```

- `layerID` is a layer's `id` in any map of `map.mapson`.
- Layers that read the same store, in one map or across maps, name the same `tiles`.
- Every path `package.json` names must be in the mapsack.
- A reader refuses a `version` newer than it knows.

A folder is awkward to send, so a mapsack travels as an archive: a mapszip or a mapsaar. Both
unpack to the same mapsack.

## mapszip

Maps + zip: a mapsack in one file. Despite the name it is not a ZIP archive but a small
container of its own: a reader finds `map.mapson` at the front without unpacking the rest.

| | |
|---|---|
| Schema | [`schema/v1/mapszip.schema.json`](schema/v1/mapszip.schema.json), for the manifest |
| Examples | [`examples/minimal.mapszip`](examples/minimal.mapszip), [`examples/huts.mapszip`](examples/huts.mapszip) |
| Media | binary, extension `.mapszip`, UTI `com.rikimaps.mapszip` |

```
"RKZS"          4 bytes, magic
version         1 byte: 2 (1 is still read: every entry packed, no `stored`)
manifest size   4 bytes, unsigned, big-endian
manifest        UTF-8 JSON, the schema above
payload         each entry's bytes, in manifest order, nothing between or after
```

```jsonc
{ "entries": [
  { "path": "map.mapson", "size": 1520, "compressedSize": 702, "sha256": "…" },
  { "path": "package.json", "size": 310, "compressedSize": 190, "sha256": "…" },
  { "path": "Trails.pmtiles", "size": 9000000, "compressedSize": 9000000,
    "sha256": "…", "stored": true },
  { "path": "files/huts.geojson", "size": 277, "compressedSize": 190, "sha256": "…" }
] }
```

- Each entry is a file of the mapsack, at its path there. `map.mapson` and `package.json` are
  required and come first.
- A reader refuses a path that is absolute or holds `..`.
- An entry is LZFSE-compressed unless `stored` is true. Writers store what is already compressed
  (`.pmtiles`, images, `.zip`, `.gz`). `size` and `sha256` describe the unpacked bytes.
- [`tools/pack-mapszip.py`](tools/pack-mapszip.py) packs a mapsack folder with every entry
  stored, which needs no LZFSE.

## mapsaar

Maps + aar: a mapsack as a compressed [Apple Archive](https://developer.apple.com/documentation/applearchive).
Any Mac unpacks it with `aa extract -i Huts.mapsaar -d Huts.mapsack`, and the layers' tiles come
out as plain `.pmtiles` files that other tools open. It has no schema of its own: what comes out
is a mapsack.

| | |
|---|---|
| Media | Apple Archive (LZFSE), extension `.mapsaar`, UTI `com.rikimaps.mapsaar` |

## maps.json

The region catalog [skifahrer/maptiles](https://github.com/skifahrer/maptiles) publishes and Riki
Maps downloads from: countries, their regions and subregions, and each one's packages with a
download per container format.

| | |
|---|---|
| Schema | [`schema/v1/maps.schema.json`](schema/v1/maps.schema.json) |
| Example | [`examples/maps.json`](examples/maps.json), an excerpt |
| Media | UTF-8 JSON, `maps.json` (`maps-test.json` for the pipeline's quick tests) |

```jsonc
{
  "_updated_at": "2026-10-01T09:35:02Z", "_updated_ts": 1790847302,
  "slovensko": { "name": "Slovensko", "regions": {
    "banskobystricky": { "bbox": [18.46, 48.035, 20.49, 48.965], "maxzoom": 14,
      "maps": { "base": { "download": "…", "size": 167844433, "sha256": "…",
        "formats": { "aar": { "download": "…" }, "zip": { "download": "…" } } } },
      "subregions": { /* cut-outs, the same shape */ } } } }
}
```

- Keys starting with `_` are metadata; every other top-level key is a country.
- A package (`maps.<id>`) and each of its `formats` need `download`; everything else is optional.
- A package's top mirrors one of its formats, the ZIP where there is one, for older readers.
- Dates are ISO 8601 UTC strings, with the same instant as Unix seconds in `*_ts`.
- Unknown keys are allowed. The pipeline validates every catalog it writes against this schema.

## Validating

```sh
pip install jsonschema
tools/validate.py my-map.mapson my-servers.servson my-map.mapszip maps.json
```

Each file is checked against the schema its name says: its extension, `maps.json` or
`*.maps.json` for the catalog, `package.json` or `*.package.json` for a mapsack manifest. A
folder is read as a mapsack. A mapszip is read as a container (magic, version, sizes, every
entry's sha256) and then as the mapsack it holds; packed entries need `pip install pyliblzfse`.
A `.mapsaar` is unpacked with `aa`, so only on a Mac.

Any 2020-12 validator works, for example Ajv: `new Ajv2020().compile(schema)` from
`ajv/dist/2020`. For servson, mapsack and maps.json, `addSchema(mapson)` first: they `$ref` its
`$defs`. The schemas match what Riki Maps' decoders accept, so a file that passes imports there.
`tests/valid/` and `tests/invalid/` hold the edge cases that CI checks.

In an editor, map `*.mapson` and `*.servson` to JSON. VS Code then picks the schema up from the
file's `$schema` key.

### Pulling the schemas

Nothing copies these files. Riki Maps clones this repository into `.build/schemas` for its
tests (`tools/fetch-schemas.sh`); maptiles checks it out in the workflow that writes `maps.json`.
Pin a commit or tag there to hold a version.

## Security

Riki Maps asks on every export whether keys go with the file, for every format. Without them, it leaves out
`rikiHeaders` and the query keys in addresses.

A `.mapson` can carry `rikiHeaders`, which are header values such as API keys for the
map's own layers. It can also carry `rikiServiceProxies`. Readers should use either
only for hosts the map's own layers reach, and should show them to the user before
importing.
