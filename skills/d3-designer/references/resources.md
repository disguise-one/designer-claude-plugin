# Resources

Resources are the persistent objects in a d3 project — video clips, screens, tracks, devices, and 240+ other types. `ResourceManager` is the central gateway.

## Key Classes

- `ResourceManager` — singleton via global `resourceManager` or `ResourceManager.get()`.
- `Resource` — base class. Props: `description` [ro], `path` [rw], `uid` [ro], `isDirty` [ro], `isBad` [ro], `isInError` [ro], `locked` [ro], `tags` [ro].

## Path Conventions

All resource paths: `<prefix>/<typename>/<name>.apx` — always **lowercase**, always `.apx`.

| Prefix | Visibility |
|--------|-----------|
| `objects/` | User-visible in UI |
| `internal/` | Hidden from users |

The type segment is the lowercase class name: `type(obj).__name__.lower()`.
User-facing type name: `type(obj).__username__` (e.g. `Screen2.__username__` = `"Surface"`).

When representing disk files, original extensions are preserved: `objects/videoclip/intro.mov.apx`.

## On-disk layout (loose files vs packaged)

Know which parts of a project you can touch with external tools and which you can't:

- **Loose on disk, writable by external tools** (Blender, image tools):
  - `<project>/objects/Mesh/*.obj`
  - `<project>/objects/DxTexture/*.png`
  - Note the **capitalised** directory names *on disk* (`Mesh`, `DxTexture`) vs the **lowercase** resource paths used in the API (`objects/mesh/…`, `objects/dxtexture/…`). Write the file there, then `resourceManager.load("objects/mesh/x.obj", Mesh)` / `load("objects/dxtexture/x.png", DxTexture)` — **the resource path *is* the file path.**
- **Inside the `.d3` package, NOT on disk:** all `.apx` resources. You **cannot** hand-edit a `DirectProjection` (or any `.apx`) to recover from a bad state — fix it through the API. (Don't waste time walking `objects/directprojection/` for files; there aren't any.)
- **Picking up a file rewritten underneath d3:** `reloadExternal()` on the `Mesh` / `DxTexture`. For a mesh, `useFileNormals = False` + `updateMesh()` forces a normal recompute.
- **Safety net:** `<project>/history/*.d3` autosaves exist — a real recovery option alongside the destructive-operation warnings.

## Access Patterns

```python
# Current UI state
track = guisystem.track                          # active track
layer = guisystem.selectedLayers[0]              # selected layer

# By path (plain strings, always lowercase, always .apx)
track = resourceManager.load("objects/track/song1.apx", Track)

# Create new or get existing — description is derived from path (read-only)
screen = resourceManager.loadOrCreate("objects/ledscreen/my screen.apx", LedScreen)

# Most recently used
track = resourceManager.getMostRecentUserVisibleResourceOfType(Track)

# Search by path prefix (not substring — must match from start)
paths = resourceManager.search("objects/ledscreen")

# Enumerate all of a type
all_screens = resourceManager.allResources(LedScreen)

# Existence check
resourceManager.exists("objects/track/song1.apx")
```

## Modifying Resources

```python
# Direct property assignment — auto-dirties the resource
resource.some_property = new_value

# In-place mutation of non-Resource, non-scalar values — markDirty on the owner
markDirty(container)
container.children.append(child)                 # list mutation
del container.children[:]                        # list mutation
container.offset.x = 5.0                         # Vec component mutation

# Unnamed sub-resources (path == "") — save via named parent
fseq.sequence.setFloat(0.0, val)
named_parent.saveOnDelete()
```

## Resource Operations

```python
resource = resourceManager.load("objects/track/song1.apx", Track)

# Identity
resource.description     # human-readable name (read-only, from path)
resource.uid             # unique int identifier
str(resource.path)       # full resource path
resource.path.filename   # just the filename

# State
resource.isDirty         # unsaved changes
resource.isBad           # missing or failed
resource.isInError       # bad, incomplete, or not found locally
resource.locked          # currently locked

# Copy / move / delete
new_obj = resource.duplicate(resource.path.replaceFilename("song1_copy"))
resource.rename("objects/track/new_name.apx")
resource.moveToTrash()

# References — find what points to this resource
clips = resource.findResourcesPointingToThis(VideoClip)

# Tags
resource.tags                   # Array<ResourceTag> — read-only
resource.addTag(tag_obj)        # tag_obj must be a ResourceTag
resource.removeTag(tag_obj)
resource.hasTag(tag_obj)
```

## Gotchas

- **`description` is read-only** — derived from path. Use `rename()` to change it.
- **Paths are always lowercase** — mismatched case causes lookup failures.
- **`search()` is prefix match** — `search("video")` returns nothing; use `search("objects/videoclip")`.
- **`saveOnDelete()` is preferred over `save()`** — it defers to the next batch and handles grouped modifications.
- **`markDirty()` only before in-place mutation** of non-Resource, non-scalar values (list append/remove/del, Vec component assignment). Direct property assignment auto-dirties.
- **Deletion is blocked while something still strongly references the resource.** `moveToTrash()` + `emptyTrash([r])` silently fails if, e.g., the stage still holds the display — `emptyTrash` logs `delete blocked by strong reference objects/stage/stage 1.apx` / `Cannot empty trash; still in use` and the resource lingers in `stage.displays` under a `trash/...` path. Drop and persist the reference first: `markDirty(stage)` → remove from the type-specific list (`stage.projectors`/`surfaces`/`ledScreens`) → `stage.saveOnDelete()` → then `moveToTrash()` + `emptyTrash()`. Linked sub-resources travel with the parent — a `Projector` drags its `ProjectorConfig`, a `Display` its auto-created `DirectProjection` — so add them to the `emptyTrash()` list too.

Code for a full delete (clear the stage reference, then trash, then empty):

```python
markDirty(stage)
stage.projectors = [p for p in stage.projectors if p is not doomed]   # or stage.surfaces / .ledScreens;
                                                                      # del stage.projectors[:] to clear all
stage.saveOnDelete()                                   # REQUIRED - commits the dropped reference
doomed.moveToTrash()
resourceManager.emptyTrash([doomed])                   # accepts a list; add the sub-resources too
```

`resourceManager.remove(path)` only logs "not found" and leaves the resource. Do not use it to delete.
- **Unnamed resources** (where `path == ""`) delegate lifecycle to a parent — save the named parent.
- **`allResources()` returns a snapshot** — won't reflect adds/removes after the call.

## Common Resource Types

`VideoClip`, `VideoAsset`, `AudioFile`, `Screen`, `Screen2`, `LedScreen`, `Projection`, `Machine`, `Layer`, `Module`, `DeviceManager`, `SuperTrack`, `Track`, `SetList`, `Note`, `Tag`

## Userguide

- [Python: Resources](https://developer.disguise.one/plugins/guides/resources/)
