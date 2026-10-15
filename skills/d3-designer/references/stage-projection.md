# Stage & Projection

Contents: Key Classes, Access, Coordinate System, Display Properties, LedScreen, Screen2, Projector, Camera, Object Hierarchy, Projection (Content Mapping), DmxScreen, Venue & Props, Screen Configurations, Helpers, Gotchas, Visual Validation, Lineup Track Validation, Userguide.

## Key Classes
- `Stage` (`Object` > `Resource`) -- Root stage container. Props: `surfaces`, `ledScreens`, `projectors`, `cameras`, `dmxScreens`, `dmxLights`, `venue`, `displays` (ro, all combined). Methods: `display(i)`, `nDisplays()`, `exportStage()`.
- `Display` (`Object` > `Resource`) -- Base for all display surfaces. Props: `resolution`, `scale`, `offset`, `rotation`, `mesh`, `master_fade`, `holdOutput`, `content`, `blendMode`, `colourprofile`, `pixel_mask`, `population_mask`. Methods: `target(iTarget)`, `setContent()`.
- `Screen2` (`Display`) -- Passive projection surface (hit by projectors). Extra: `projectors`, `projectorViewBlending`, `reflectivity`, `screenBackground`.
- `LedScreen` (`SlcAwareDisplay` > `Display`) -- Emissive LED panel. Extra: `luminanceNits`, `viewingAngle`, `reflectivity`, `colourMap`.
- `DmxScreen` (`DmxDisplay` > `Display`) -- DMX-driven LED screen. Extra: `universe`, `iChannel`, `fixture_type`, `array`, `origin`, `universe_step`, `universe_size`. Methods: `assignString()`, `displayChannels()`.
- `Projector` (`SlcAwareDisplay` > `Display`) -- Video projector simulation. Extra: `screens` (List[Screen2]), `configPosition`, `configRotation`, `configThrowRatio`, `configLensShift`, `lumens`, `feather`, `autoSoftEdge`, `barnDoor*`. Methods: `addScreen()`, `removeScreen()`, `nScreens()`, `addStackedProjector()`.
- `Camera` (`SlcAwareDisplay` > `Display`) -- Virtual/physical camera. Extra: `fieldOfViewH`, `fieldOfViewV`, `focalLengthMM`, `sensorSizeMM`, `videoIn`, `k1k2k3`, `overscan`, `lens`. Methods: `saveCurrentView()`. Static: `Camera.localVisualiserCamera()`.
- `Projection` (`Resource`) -- Base class for content mapping. Do not use directly — use a typed subclass below.
- `ScreenConfiguration` (`Resource`) -- Named preset of object positions/rotations/sizes. Props: `objects`, `positions`, `rotations`, `sizes`, `animates`. Methods: `addObject()`, `removeObject()`, `containsObject()`, `updateConfigFromObject()`.
- `Venue` (`Object` > `Resource`) -- Container for props/buildings. Props: `props` (List[Prop]).
- `Prop` (`Object` > `Resource`) -- Physical prop in scene. Props: `mesh`, `scale`, `normalMap`, `luminosity`, `renderSettings`.
- `Object` (`Resource`) -- Base for all stage 3D objects. Props: `offset`, `rotation`, `scale`, `mesh`, `parent`, `children`, `world`, `local`, `renderLayer`, `trackingSource`. Methods: `add()`, `remove()`, `isInActiveStage()`, `centroid()`, `findAllObjectsOfType()`.

## Access
```python
stage = state.stage                          # Stage singleton

# Stage collections
stage.surfaces                               # List[Screen2]
stage.ledScreens                             # List[LedScreen]
stage.projectors                             # List[Projector]
stage.cameras                                # List[Camera]
stage.dmxScreens                             # List[DmxScreen]
stage.dmxLights                              # List[FixtureGroup]
stage.venue                                  # Venue or None
stage.displays                               # List[Display] — read-only combined view

# Resource paths follow the standard pattern: objects/<lowercase_type>/<name>.apx
```

## Coordinate System

position: **+X** = right, **+Y** = up, **+Z** = back (away from audience).
rotation: Euler YXZ order, in degrees, **+X** = pitch forward, **+Y** = yaw right, **+Z** = roll clockwise.

| Stage term | Direction |
|---|---|
| Downstage / audience | −Z |
| Upstage | +Z |
| Stage left | +X |
| Stage right | −X |
| House left | -X |
| House right | +X |

### Mesh Facing (which way a screen points)

A display emits content out of its mesh's **front normal**, so a screen pointing the wrong way renders black from the house. The absolute default direction is **not reliable to assume** — tests give different results. Facing depends on mesh, content, and viewpoint, so **verify empirically rather than trusting a fixed rule**:

1. Place the screen, put content on it, and capture from the audience/house side.
2. If it renders from the wrong side, add `180` to `rotation.y` and re-capture. That single flip is the fix for a back-facing flat screen.
3. **Floor / deck screen** (normal pointing up): `rotation = Vec(-90, 0, 0)` — `Rx(-90)` maps the mesh's local +Z to world +Y (geometry-verified).

Keep the projection's facing consistent with the screen's — see the Parallel *Facing* note below (`projectionObject.rotation` should match whatever `rotation` the screens end up with).

Don't try to fix facing with the `content` property. Its verified mapping is `{0: 'Both Sides', 1: 'Front Only', 2: 'Back Only'}` (from `d3.pyi`; note this is *not* the `Front/Back/Both` order older notes implied). Leave `content` at `0` (Both Sides) unless you specifically need to cull one side; solve facing with rotation + a capture, not `content`.

## Display Properties (shared by all display types)
All displays inherit from `Display` via `Object`:
```python
display.resolution  = Vec2(1920, 1080)       # pixel resolution
display.offset      = Vec(0.0, 2.0, -3.0)   # position in metres (world or parent-relative)
display.rotation    = Vec(0.0, 0.0, 0.0)    # degrees
display.scale       = Vec(3.84, 2.16, 0.1)  # mesh scale
display.master_fade = 1.0                    # output brightness
display.content     = 0                      # 0=Both Sides, 1=Front Only, 2=Back Only (per d3.pyi; see Mesh Facing)
display.blendMode   = 0
display.holdOutput  = False
display.renderLayer = 0
```

### Mesh Sizing
Physical display size = `mesh.extent` multiplied by `scale`. `Mesh.extent` returns `(min_vec, max_vec)`.

- **Builtin meshes** (e.g. "rectangle"): unit-sized (extent −0.5 to 0.5). `scale` controls physical size in metres — e.g. `scale = Vec(3.84, 2.16, 0.1)` = 3.84m wide, 2.16m tall.
- **User-provided meshes**: pre-sized at real-world dimensions. `scale` is typically `(1, 1, 1)`.

Always derive physical extent from `mesh.extent * scale`, not from `scale` alone.

### Built-in meshes & props (check before modelling anything)

The default project ships scenic meshes and scale-reference figures. Reach for these before opening Blender — most stadium/arena rigs are buildable from stock assets. Extents below were read from one project; **confirm against your stock project and always read `mesh.extent`** (half-extents differ per mesh — `rectangle` is ±0.5 but `puffersphere`/`cylinder` are ±1).

| Resource | Notes |
|---|---|
| `objects/mesh/rectangle.apx` | unit rectangle (±0.5) — the default flat-screen mesh |
| `objects/mesh/puffersphere.apx` | unit sphere (±1) — `scale` = radius |
| `objects/mesh/cylinder.obj` | unit cylinder (±1) — LED rings / halos |
| `objects/mesh/dome.obj`, `objects/mesh/concave.apx` | curved surfaces |
| `objects/mesh/arena.obj` | venue shell (~84 m × 20 m × 129 m) |
| `objects/prop/arena.apx` | pre-made arena prop |
| `objects/mesh/singer.obj`, `guitarist.obj`, `drummer.obj`, `man.obj`, `woman.obj` | ~2 m human figures — excellent scale references |

## LedScreen
```python
# loadOrCreate + rename auto-adds to stage.ledScreens — do NOT also append or you get duplicates
# ORDER MATTERS (see the DP mode warning below): assign the mesh BEFORE resolution.
scr = resourceManager.loadOrCreate("objects/ledscreen/my screen.apx", LedScreen)
scr.rename(scr.path)                         # triggers init: auto-creates DirectProjection
scr.mesh = resourceManager.load("objects/mesh/my region.obj", Mesh)   # if using an imported mesh
scr.resolution    = Vec2(1920, 1080)         # true pixel pitch of the physical screen
scr.luminanceNits = 800.0
scr.viewingAngle  = 140.0
scr.reflectivity  = 0.04
stage.saveOnDelete()                         # rename() auto-adds to stage list (in-place mutation)

# REQUIRED: pin the auto-created DirectProjection. Path: "objects/directprojection/<screenname> (direct).apx".
dp = resourceManager.load("objects/directprojection/%s (direct).apx" % scr.path.filename, DirectProjection)
dp.mode = 1                                   # 1 = manual. THIS is mandatory (see warning below).
dp.resolution = Vec2(dx, dy)                  # your chosen canvas size (aspect = screen)
dp.save()
```

### ⚠️ DirectProjection `mode` / VRAM — read before any bulk screen work

The DP has an undocumented **`mode`** property. **Default `0` = auto-derive the canvas resolution from the screen; `1` = manual.** In `mode == 0`:

- d3 recomputes `dp.resolution` to **very large** values (more than 8000 pixels on each side) **every time the owning screen's `mesh` is assigned or the mesh resource is reloaded**.
- Setting `dp.resolution` while `mode == 0` **appears to succeed** — an immediate read-back returns your value — then **silently reverts** on the next mesh assignment/reload. This is the trap; verifying twice and moving on does not save you.
- Across many screens the canvases add up to over a gigapixel. The session stops responding (`/api/session/*` returns HTTP 502 while `/api/service/*` stays healthy), and the oversized values **persist into the `.apx` files**, so the project fails again on load.

So: **always set `dp.mode = 1` before `dp.resolution`, and assign the screen's `mesh` before touching resolution** (a later mesh assign in mode 0 wipes it).

**Capping DP canvases is legitimate engineering, not a workaround.** Keep `LedScreen.resolution` at true pixel pitch (that's the physical rig). Size the DP canvas to a sensible content resolution at the screen's exact aspect (e.g. long edge ≤ 2048). The pixel-space-layer caveat (below, in Gotchas) only bites *pixel-positioned* modules (`TextModule` `fontSize`/`xPosition`); canvas-relative generative modules (`TestPatternModule`, `RadarModule`, gradients) are unaffected by an aspect-preserving downscale. Worked budget: a 150 m × 45 m stage, 20 regions at 6 mm pitch = **57 Mpx of LED** but only **44 Mpx of canvas** at a 2048 cap.

**Mandatory audit after any bulk screen work** — fail loudly before rendering:
```python
dps = [d for d in resourceManager.allResources(DirectProjection)]
tot = sum(int(d.resolution.x) * int(d.resolution.y) for d in dps)
big = [(str(d.path.filename), int(d.resolution.x), int(d.resolution.y))
       for d in dps if int(d.resolution.x) * int(d.resolution.y) > 5e6]
# Abort/repair if tot/1e6 > ~150 (Mpx) or big is non-empty.
```

**Recovery (the naive fix re-allocates before it frees — free FIRST):**
```python
# Pass 1: drop every DP to tiny to release VRAM.
for dp in resourceManager.allResources(DirectProjection):
    if str(dp.path.directory) == "objects/directprojection/":
        dp.mode = 1
        dp.resolution = Vec2(64, 64)
# Pass 2: set real targets, then save.
```

## Screen2 (Projection Surface)
```python
surf.resolution       = Vec2(3840, 2160)
surf.reflectivity     = 0.9
surf.screenBackground = 0                    # 0=Black, 1=Transparent
stage.surfaces.append(surf)
```

## Projector
A projector casts light onto `Screen2` surfaces. `screens` limits which surfaces it renders; empty = all surfaces.
```python
proj.configThrowRatio = 1.7
proj.configLensShift  = Vec2(0.0, -0.1)
proj.lumens           = 20000.0
proj.resolution       = Vec2(1920, 1200)
stage.projectors.append(proj)

proj.addScreen(surf)                         # restrict to specific surfaces
proj.removeScreen(surf)

# Barn doors (0.0–1.0 fractions)
proj.barnDoorLeft = proj.barnDoorRight = proj.barnDoorTop = proj.barnDoorBottom = 0.05
proj.autoSoftEdge = 1                        # 0=Off, 1=On

# Brightness stacking
proj.addStackedProjector(proj2)

# Quick-calibration — call editingConfig(False) to apply
proj.configPosition = Vec(0.0, 5.0, 8.0)
proj.configRotation = Vec(-20.0, 0.0, 0.0)
proj.editingConfig(False)
```

## Camera
```python
cam.fieldOfViewH  = 60.0                     # degrees
cam.focalLengthMM = 35.0
cam.sensorSizeMM  = Vec2(36.0, 24.0)
cam.resolution    = Vec2(1920, 1080)
cam.zNear         = 0.1
cam.zFar          = 100.0
cam.k1k2k3        = Vec(0.0, 0.0, 0.0)      # radial distortion
cam.overscan      = Vec2(1.0, 1.0)
stage.cameras.append(cam)

local_cam = Camera.localVisualiserCamera()   # the editor viewport camera —
                                             # do NOT drive this for captures
                                             # (snaps the user's view); use a
                                             # dedicated Camera resource instead.
                                             # See mcp_helpers.get_visualiser_camera().
```

## Object Hierarchy
Any `Object` can be parented. Child `offset`/`rotation`/`scale` become parent-relative.
```python
parent.add(child)                            # child.parent == parent
parent.remove(child)
parent.children                              # List[Object]
```

## Projection (Content Mapping)

A projection routes layer content to displays. Assign to a layer via the `"mapping"` FieldSequence.

**Do not use the base `Projection` class directly.** Use a typed subclass.

Most projection types have a `projectionObject` (`ProjectionObject`, an `Object` subclass) that positions them in 3D space. Set `projection.projectionObject.offset` and `.rotation` to place the projection over its target screens. Only `DirectProjection` and `FeedProjection` are screen-relative (no spatial positioning needed).

| Content on...                   | Use                    |
|---------------------------------|------------------------|
| One screen (UV-mapped)          | `DirectProjection`     |
| Multiple flat/angled screens    | `Parallel`             |
| From a viewpoint                | `PerspectiveProjection`|
| Cylindrical wrap                | `Cylindrical`          |
| xR / virtual production         | `MeshProjection`       |
| Per-screen crop/scale/assign    | `FeedProjection`       |

All subclasses inherit: `screens`, `resolution`, `filtering`, `mask`. Each subclass adds properties for its mode — look them up via `d3-ref.py --classes`. For `FeedProjection` feed controls, see `references/feeds-outputs.md`.

### Parallel Geometric Model

Parallel projects onto a physical area defined by `size` (Vec2, metres). `resolution` sets pixel density within that area.

`lock` couples size and resolution: Aspect (default, `1`) forces resolution to match the aspect ratio of `size` — setting resolution alone will be auto-corrected. Off (`0`) decouples them.

For multi-screen setups, `size` must span the full physical bounding box of the screen array. For non-coplanar screens, use `compute_screen_bbox()` from `mcp_helpers` — it computes the world-space axis-aligned bounding box from mesh extents, scale, rotation, and offset. Set `size` from the returned extents and `projectionObject.offset` from the returned centre.

**Facing must match the screens (observed in testing).** A `Parallel` casts along its `projectionObject`'s forward axis, so the projection has to point the same way the screens face or content lands behind them / not at all. The rule that worked: **set `projectionObject.rotation` equal to whatever `rotation` the screens ended up with** (see Mesh Facing — resolve the screens' facing first, then copy it here). Observed pairings: walls at `yaw 180` → `projectionObject.rotation = Vec(0, 180, 0)`; a floor array at `Vec(-90, 0, 0)` → `Vec(-90, 0, 0)`. (The exact projection-axis convention isn't documented; this equal-to-screen-facing rule is inferred — verify for other orientations.)

### Examples

```python
# Direct projection — one screen, UV-mapped content
dp = resourceManager.loadOrCreate("objects/directprojection/main.apx", DirectProjection)
dp.screens = [led_main]
dp.resolution = Vec2(1920, 1080)

# Parallel projection — multiple flat/angled screens sharing one canvas
pp = resourceManager.loadOrCreate("objects/parallel/all screens.apx", Parallel)
pp.screens = [led_left, led_centre, led_right]
# For non-coplanar screens, use compute_screen_bbox([led_left, led_centre, led_right])
pp.lock = 0                                          # decouple size and resolution
pp.size = Vec2(total_width, total_height)
pp.resolution = Vec2(pixels_wide, pixels_tall)
# Position AND orient the projection object to cover the screen array
po = pp.projectionObject
po.offset = Vec(centre_x, centre_y, centre_z)       # centre of the bounding box
po.rotation = screens[0].rotation                   # match the screens' facing (see note above)
```

Layers need both a mapping (projection) and content — see `references/content-media.md` for assigning video clips via `findSequence("video")`.

## DmxScreen
```python
dmx.resolution    = Vec2(20, 1)
dmx.fixture_type  = 0                        # pixel type (0=RGB etc.)
dmx.array         = 0                        # addressing order (0=Horizontal)
dmx.origin        = 0                        # start corner
dmx.universe      = 1                        # 1-based
dmx.iChannel      = 1                        # 1-based start channel
dmx.universe_step = 0
dmx.universe_size = 512
stage.dmxScreens.append(dmx)
```

## Venue & Props
`stage.venue` is **`None` in a blank project** — create/load a `Venue` before adding props.
```python
stage.venue                                  # Venue or None — create one if absent
venue.props                                  # List[Prop]
venue.props.append(prop)

prop.offset = Vec(0.0, 0.0, 0.0)
prop.scale  = Vec(1.0, 1.0, 1.0)
prop.mesh   = resourceManager.load("objects/mesh/scenic.obj", Mesh)
prop.renderSettings.displayMode = 1          # 1 = flat. SEE WARNING BELOW.
prop.renderSettings.diffuseMap  = resourceManager.load("objects/dxtexture/scenic.png", DxTexture)
```

`Prop` members: `mesh`, `normalMap`, `normalMapScalar`, `densityMap`, `densityScale`, `luminosity`, `renderSettings` (`PropRenderer`), `meshChangedAction`.
`PropRenderer` (`prop.renderSettings`) members: `displayMode`, `diffuseMap`, `blendMode`, `reflectance`, `flatCol`, `wireCol`, `wireframeCleanup`, `isShadowCaster`, `dseExpandCM`.

> **⚠️ `displayMode = 3` = flat + wireframe overlay.** On a high-poly mesh the wireframe saturates and the object reads as a **dark, speckled blob**. **A dense mesh rendering near-black with a dotted/speckled surface is almost always `displayMode = 3`, not a shading or texture fault — check it FIRST**, before UVs, normals, z-fighting, or `useFileNormals`. `displayMode = 1` = flat. (observed r257961)

## Screen Configurations
Named presets that snapshot object transforms for show-switching.
```python
cfg.addObject(scr)
cfg.updateConfigFromObject(scr, 0)           # snapshot current transform at index 0
cfg.containsObject(scr)                      # bool
cfg.objects                                  # parallel lists: objects, positions, rotations, sizes
```

## Helpers (mcp_helpers)

Stage-specific helpers from `scripts/mcp_helpers.py`. Register the module once per session.

- `capture_stage(output_dir, width, height, fov, eye, target)` — position the visualiser camera and capture a frame. Auto-positions above/front of all displays when no eye/target given. Returns `{"status": "capture_deferred", ...}`.
- `create_lineup_track()` — create a per-screen test pattern track with colour-coded layers per display. Returns `{"track": "mcp_lineup", "screens": [...], "checkout_beat": 30.0}`.
- `checkout_mapping(projection_path, colour=None)` — isolate a mapping on the lineup track's section 1 and jump to beat 30. Returns `{"status": "ready", ...}`.
- `cleanup_checkout()` — remove checkout layers from the lineup track. Returns `{"removed": int}`.
- `get_visualiser_camera()` — return or create the `mcp_visualiser` camera.
- `compute_screen_bbox(screens)` — world-space axis-aligned bounding box of a list of Displays. Uses `mesh.extent * scale` for physical size, applies Y rotation and offset. Returns `{"min", "max", "size", "centre"}`.

## Gotchas
- `stage.displays` is read-only — add objects via type-specific lists (`stage.ledScreens`, `stage.surfaces`, etc.).
- `Screen2` is the API name for what the UI calls a "screen surface" (passive, hit by projectors). `LedScreen` is the emissive LED panel.
- `Projection` (content mapping) is not the same as `Projector` (light emitter). Projectors cast onto `Screen2` surfaces; projections route timeline content to any display.
- Do not use base `Projection` directly — use a typed subclass (`DirectProjection`, `Parallel`, etc.).
- A projection with empty `screens` renders nothing — always assign target displays.
- `stage.venue` can be `None` in a new project.
- `Object.offset`/`rotation`/`scale` are world-space when no parent, relative to parent otherwise.
- `Projector.screens` limits which surfaces the projector renders; empty = all surfaces.
- `configPosition`/`configRotation` etc. on `Projector` are quick-calibration; call `editingConfig(False)` to apply.
- There is no `Screen` class — use `Screen2`.
- **`rename(path)` on a new Display auto-adds it to the stage and auto-creates a DirectProjection.** Do NOT also `stage.ledScreens.append(scr)` — that creates a duplicate entry. **Always overwrite the auto-created DP's resolution** (`dp.resolution = scr.resolution`) — its default is NOT consistent (observed: 256×256, 16384×1393, others), and a mismatch silently breaks pixel-space layer math (TextModule fontSize/xPosition/yPosition, BitmapModule scale, etc.) even though the wall itself still renders. Load the DP by its predictable path `objects/directprojection/<screenname> (direct).apx` rather than scanning `allResources(DirectProjection)` after `rename()` — the scan can race the auto-creation.
- `loadOrCreate` returns the existing object if the path matches — only call `rename` on genuinely new displays. For multi-screen setups, create a `Parallel` projection explicitly — the auto-created DPs handle individual screens only.
- **Adding/removing objects from stage lists is in-place list mutation.** Call `markDirty(state.stage)` before appending/removing from stage lists (e.g. `stage.ledScreens.append(scr)`).
- **`stage.displays` is a `Boundindexer` (read-only, computed view)** — `del stage.displays[:]`, `stage.displays.remove(d)` and `stage.displays = [...]` all fail. Mutate the type-specific lists instead (`stage.surfaces`, `stage.ledScreens`, `stage.projectors`, `stage.cameras`, `stage.dmxScreens`).
- **The slice-delete pattern (`del list[:]`) only works on `track.layers`.** Stage lists are `Boundindexer` — to clear or filter, reassign: `stage.surfaces = [s for s in stage.surfaces if keep(s)]` (after `markDirty(stage)`).
- A blank project includes a default Projector (`"projector 1"`) and Screen2 (`"surface 1"`). To delete them: filter them out of `stage.surfaces` / `stage.projectors`, then `obj.moveToTrash()` + `resourceManager.emptyTrash([...])`. **Do NOT use `resourceManager.remove(path)`** — it logs but doesn't delete (see SKILL.md Resource Patterns).

## Visual Validation (SaveFrameSystem)

`SaveFrameSystem` captures a rendered frame from any Display (screen, projector, or camera) to disk. Access via `subsystems.getSystem(SaveFrameSystem)`.

```python
sfs = subsystems.getSystem(SaveFrameSystem)
sfs.deferSaveScreenFrame(display, 0, "<capture folder>")   # a folder that the d3 host can write
# Saves screen_<target_name>_00000.png next frame
```

Parameters: `display` (any Display), `iTarget` (target index, usually `0`), `directory` (absolute path).

**Verifying the stage.** For a quick check, use the `internal_gui_capture` MCP tool — it returns the current GUI view inline as an image, no file round-trip. It captures whatever the editor is currently framing, so it can't set an arbitrary angle.

**Stage overview via visualiser Camera (controlled pose)**: when you need a specific overview angle without snapping the user's editor view, the `mcp_helpers` module registration creates a `mcp_visualiser` Camera on the stage. `capture_stage()` (or `d3-capture-frame.ps1`) positions this camera above and in front of the stage at ~25 degrees down — this elevated angle reveals Z-depth positioning errors that a flat front view hides. Use the MCP client's image-reading tool on the resulting PNG to verify: screen positions and angles, content on each screen, projection coverage. If screens look misaligned in depth, check their Z coordinates.

**Editor display labels.** `Camera.localVisualiserCamera()` overlays each display's name ("center", "left", "projector 1", etc.) on the screen surface — those labels are editor-view only and not in the rendered output. The dedicated `mcp_visualiser` camera used by `capture_stage()` does NOT include this overlay, so the labels won't appear in your PNGs. The note exists in case you ever capture from `localVisualiserCamera` directly: don't mistake those labels for actual content, and don't assume "blank screen with only the label" means a broken layer until you've checked content brightness.

## Lineup Track Validation

A scratch "Lineup" track (`mcp_lineup`) for isolating and verifying individual mappings. Two sections:

| Section | Beats | Purpose |
|---------|-------|---------|
| 0: Screen Check | 0–29 | Permanent TestPatternModule layer per display, each tinted a different colour via palette xCol/yCol. Read this capture to check the stage geometry looks correct for the design. Fix issues before checking mappings. |
| 1: Mapping Checkout | 30–59 | Empty by default. `checkout_mapping()` creates a temporary layer here, captures a frame, then `cleanup_checkout()` removes it. |

### Functions (mcp_helpers module)

```python
# Create the lineup track (once, after stage build)
create_lineup_track()
# -> {"track": "mcp_lineup", "screens": [{"name": ..., "colour": [x, y]}], "checkout_beat": 30.0}

# Verify a single mapping — creates temp layer, navigates to section 1, captures
checkout_mapping("objects/directprojection/centre.apx")
checkout_mapping("objects/parallel/all screens.apx", colour=(0.5, 0.8))
# -> {"status": "capture_scheduled", "projection": ..., "output_dir": ..., "beat": 30.0}

# Remove checkout layers when done
cleanup_checkout()
# -> {"removed": int}
```

### Track switching

`TransportCommand.trackAndBeat` does not switch tracks — it only affects beat position. Use the REST API `gototrack` endpoint to change tracks. The orchestration script handles this automatically.

### Orchestration script

`d3-capture-lineup.ps1` runs the full lineup in one tool call — creates track, captures screen check, checks out each mapping, captures each, cleans up:

```bash
pwsh -File scripts/d3-capture-lineup.ps1 \
  -Mappings '{"mappings": [{"name": "Centre", "path": "objects/directprojection/centre.apx"}]}' \
  -OutputDir "<capture folder>"
```

`-OutputDir` is optional. The default is a `d3-captures` folder in the temp folder. A different folder must be writable by the d3 host and readable by the script.

Output: JSON array of `{section, image, ...}` entries. Read each PNG to verify mapping coverage.

## Userguide
- [Stage setup](https://help.disguise.one/designer/stage-setup/stage-setup-overview) · [Screens](https://help.disguise.one/designer/stage-setup/screens/screens-overview) · [Projectors](https://help.disguise.one/designer/stage-setup/projector-simulation/projector-simulation-overview) · [Cameras](https://help.disguise.one/designer/stage-setup/cameras)
- [Venues & Props](https://help.disguise.one/designer/stage-setup/venues-and-props/venues-props-overview) · [DMX screens & lights](https://help.disguise.one/designer/stage-setup/dmx-screens-lights/dmx-screens-lights-overview) · [Mapping](https://help.disguise.one/designer/mapping/content-mapping-overview)
- [Calibration overview](https://help.disguise.one/workflows/calibration-projection/projector-calibration-overview) · [Python stage guide](https://developer.disguise.one/plugins/guides/stage) · [Python calibration guide](https://developer.disguise.one/plugins/guides/calibration)
