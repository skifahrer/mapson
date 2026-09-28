# mapson

Map exchange format: one map, as JSON. It holds the map's layers, its styles and how
each layer is drawn. It does not hold tiles. Riki Maps reads and writes it as `.mapson`,
and anyone else can too.

| | |
|---|---|
| Schema | [`schema/v1/mapson.schema.json`](schema/v1/mapson.schema.json) (JSON Schema 2020-12) |
| Schema URL | `https://raw.githubusercontent.com/skifahrer/mapson/master/schema/v1/mapson.schema.json` |
| Examples | [`examples/minimal.mapson`](examples/minimal.mapson), [`examples/full.mapson`](examples/full.mapson) |
| Media | UTF-8 JSON, extension `.mapson` (`.rikimap` is the legacy name), UTI `com.rikimaps.mapson` |

## Shape

```jsonc
{
  "$schema": "https://raw.githubusercontent.com/skifahrer/mapson/master/schema/v1/mapson.schema.json",
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
| map (root) | `id` `name` `stack` `styles` `isBuiltIn` `drawsRegions` `isOnlineOnly` |
| layer (`stack[]`) | `id` `name` `symbol` `role` `opacity` `source` `isEnabled` |
| layer `source` | exactly one of `region` `url` `files` `apple` |
| `source.url` | `template` `maxZoom` `format` `attribution` |
| style (`styles[]`) | `id` `name` `symbol` `origin` `notes` `adjustments` |
| style `origin` | exactly one of `builtIn` `document` `arrangement` (`{}`) |
| style `adjustments` | `lineWidthScale` `labelSizeScale` |
| credit (`credits[]`) | `holder` |

The schema lists every nested object: Esri services, API readings, renderers,
arrangements and the rest.

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

## Signing is optional

`_signature` is optional. Riki Maps signs its own exports with a keyed hash so its import
sheet can say *"Verified · exported by Riki Maps"*. The mark is a UI hint, not security.

- A file without `_signature` is fully valid. It imports normally, just without the
  badge. Other writers should leave the key out.
- Any change to a signed file breaks the mark. The file still imports, only as
  unverified, so an editor should remove `_signature`.
- The signature covers the map, including `$schema`. It excludes `_schemaVersion`,
  `_signature` and the `riki*` sidecars (`rikiSharedFeature`, `rikiServiceProxies`,
  `rikiHeaders`), so those can change without touching it.

## Versioning

- `_schemaVersion` is the format version. If it is missing, the file is version 0 (written
  before versioning), which reads the same as 1.
- Adding an optional key does **not** change the version.
- The version goes up only when an older reader would misread a file. That change gets
  a new `schema/vN/` file. A reader must refuse a version newer than it knows instead of
  guessing, and Riki Maps does.
- `$schema` names the schema a file follows. It is optional; writers should set it.

## serverson

A `.serverson` holds saved map servers instead of a map: their addresses, kinds, request
settings, and everything they published when last read (layers, Esri services and folders,
facts, zooms, bounds), each with the time of that read. It is a mapson extension: its schema
reuses mapson's `$defs` by relative `$ref`.

| | |
|---|---|
| Schema | [`schema/v1/serverson.schema.json`](schema/v1/serverson.schema.json) |
| Schema URL | `https://raw.githubusercontent.com/skifahrer/mapson/master/schema/v1/serverson.schema.json` |
| Examples | [`examples/minimal.serverson`](examples/minimal.serverson), [`examples/full.serverson`](examples/full.serverson) |
| Media | UTF-8 JSON, extension `.serverson`, UTI `com.rikimaps.serverson` |

```jsonc
{
  "$schema": "https://raw.githubusercontent.com/skifahrer/mapson/master/schema/v1/serverson.schema.json",
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

## Validating

```sh
pip install jsonschema
tools/validate.py my-map.mapson my-servers.serverson
```

Each file is checked against the schema its extension names.

Any 2020-12 validator works, for example Ajv:
`new Ajv2020().compile(schema)` from `ajv/dist/2020`. For serverson, `addSchema(mapson)` first. The schema matches what Riki Maps' decoder
accepts, so a file that passes it imports there. `tests/valid/` and `tests/invalid/` hold the edge cases that CI
checks.

In an editor, map `*.mapson` to JSON. VS Code then picks the schema up from the file's
`$schema` key.

## Security

Riki Maps asks on every export whether keys go with the file. Without them, it leaves out
`rikiHeaders` and the query keys in addresses.

A `.mapson` can carry `rikiHeaders`, which are header values such as API keys for the
map's own layers. It can also carry `rikiServiceProxies`. Readers should use either
only for hosts the map's own layers reach, and should show them to the user before
importing.
