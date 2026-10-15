# Feed Outputs

## Key Classes
- `FeedScene` (`Resource`) -- Container for feed rectangles and head configs. Props: `feedRects`, `headConfigs`, `activeRegions`, `excludeMode`, `excludedMaps`. Methods: `add()`, `remove()`, `addHeadConfig()`, `ensureHeadConfig()`, `getUsedHeads()`, `importRectsFromTable()`, `exportRectsAsTable()`.
- `FeedRect` (`Resource`) -- Maps a screen region to a physical output head. Props: `head`, `rect`, `screenRect`, `referenceDisplay`, `resolveDisplay`, `rotationIndex`, `deformStack`, `mask`, `contentMode`, `displayTarget`, `lock_sizes`.
- `FeedHeadConfig` (`Resource`) -- Output head settings. Props: `resolution` (Int2), `name`, `clearColour` (Colour), `clearBackground`, `framesLatency`, `liveDot`, `matrixOutputs`. Static: `FeedHeadConfig.make(resolution)`.
- `ActiveScreenRegion` (`Resource`) -- Screen/rect pair for active region filtering. Props: `Display`, `Rect`.
- `DisplayManagerSubsystem` (`Subsystem`) -- Display adapter management. Methods: `getMachineTargetModesForRefresh()`, `loadDisplayAdapterList()`, `saveDisplayAdapterList()`.

## Access
```python
# All feed scenes
scenes = resourceManager.allResources(FeedScene)

# By path
scene = resourceManager.load("objects/feedscene/Main.apx", FeedScene)

# Create / get
scene = resourceManager.loadOrCreate("objects/feedscene/Touring.apx", FeedScene)

# DisplayManager subsystem (access via type, not string)
dm = subsystems.getSystem(DisplayManagerSubsystem)
```

## Feed Scenes & Head Configs
```python
# Inspect used output heads
heads = scene.getUsedHeads()  # List[int]

# Ensure a head config exists for head 0 at 1920x1080
cfg = scene.ensureHeadConfig(0, Int2(1920, 1080))

# Or create explicitly via static factory
cfg = FeedHeadConfig.make(Int2(3840, 2160))
cfg.name = "LED Wall"
cfg.clearColour = Colour(0, 0, 0, 255)   # RGBA
cfg.framesLatency = 1
cfg.matrixOutputs = "1.1"
scene.addHeadConfig(cfg)

# Remove head config by index
scene.removeHeadConfig(0)
```

## Feed Rectangles
```python
# Create a FeedRect pointing head 0 at a display
rect = resourceManager.loadOrCreate("internal/feedrect/main_rect.apx", FeedRect)
rect.head = 0
rect.rect = Rect(0, 0, 1920, 1080)        # position on output head (pixels)
rect.screenRect = Rect(0, 0, 1, 1)       # source region in UV (0..1)
rect.rotationIndex = 0                   # 0=0deg, 1=90deg, 2=180deg, 3=270deg
rect.contentMode = 0                     # which channels to display
rect.lock_sizes = False

# Set display reference before adding to scene
rect.referenceDisplay = resourceManager.load("objects/display/Screen1.apx", Display)
scene.add(rect)

# Remove
scene.remove(rect)

# Iterate existing rects
for r in scene.feedRects:
    print("%s -> head %d" % (r.resolveDisplay.description, r.head))
```

## Batch Export/Import
```python
# Export rects to table (must have referenceDisplay set on each rect)
# Convert feedRects array to Python list first
rects_list = list(scene.feedRects)
table = FeedScene.exportRectsAsTable(rects_list, "<folder>/rects.csv")

# Import — optionally clear existing rects first
scene.importRectsFromTable(table, False)
```

## Active Regions & Exclusion Filtering
```python
scene.excludeMode = 0   # 0=Exclude listed regions, 1=Include only listed regions

region = resourceManager.loadOrCreate("internal/activescreenregion/r1.apx", ActiveScreenRegion)
region.Display = display_obj
region.Rect = Rect(0, 0, 1920, 1080)
markDirty(scene)                    # in-place list mutation
scene.activeRegions.append(region)
```

## Warp (DeformStack)
```python
# DeformStack lives on FeedRect
ds = rect.deformStack

# DeformStack has insert, remove, item accessors for warp layers
# Layer types (configured via UI): 4point, 9point, Grid, Circular, Lens Deform, Custom, Reference other projector
```

## Display Adapter Info
```python
dm = subsystems.getSystem(DisplayManagerSubsystem)
modes = dm.getMachineTargetModesForRefresh("hostname", 0, Rational(60, 1))
for m in modes:
    print(m)

dm.saveDisplayAdapterList("hostname", "<folder>/adapters.json")
dm.loadDisplayAdapterList("hostname", "<folder>/adapters.json")
```

## Gotchas
- `FeedRect.rect` is in **output pixel coordinates**; `screenRect` is in **UV space (0..1)** — different coordinate systems.
- `FeedRect.referenceDisplay` does not follow forwarding displays; use `resolveDisplay` to get the final target.
- `ensureHeadConfig(i, res)` is the safe way to create/get a head config — avoids duplicates.
- `FeedHeadConfig.make(res)` is a static factory — use it rather than `loadOrCreate` when no persistent path is needed.
- `ActiveScreenRegion` properties are `Display` and `Rect` (capital D/R) — not lowercase `display`/`rect`.
- Feed rectangles **flash blue in Designer GUI every 5 minutes** as an anti-piracy indicator; this does NOT appear on physical output.
- `DisplayManagerSubsystem` is a Subsystem — access via `subsystems.getSystem(DisplayManagerSubsystem)` with the type, not a string.
- `exportRectsAsTable()` requires all rects to have `referenceDisplay` set; convert `scene.feedRects` to a Python list with `list()` before passing.
- `importRectsFromTable()` silently skips rects whose referenced displays don't exist in the destination scene.
- `ScreenConfiguration` stores object positions/rotations/sizes arrays — it's for stage layout snapshots, not feed routing.

## Userguide
- [Feed Outputs Overview](https://help.disguise.one/designer/feed-outputs/feed-outputs-overview) | [Feed Rectangles](https://help.disguise.one/designer/feed-outputs/editing-feed-rectangle) | [Alternate Feed Scenes](https://help.disguise.one/designer/feed-outputs/alternate-feed-scenes) | [Import/Export Scenes](https://help.disguise.one/designer/feed-outputs/import-export-feed-scenes)
- [Blending & Masking](https://help.disguise.one/designer/feed-outputs/blending-masking-outputs) | [Warping](https://help.disguise.one/designer/feed-outputs/warping-outputs) | [VFC Cards](https://help.disguise.one/designer/feed-outputs/configuring-vfc-card-slots) | [Developer Feed API Guide](https://developer.disguise.one/plugins/guides/feed)
