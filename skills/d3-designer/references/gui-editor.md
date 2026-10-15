# GUI, Editor & Stage Navigation

## Key Classes
- `GuiSystem` (`Subsystem`) -- Runtime UI hub. Props: `currentTransportManager`, `player`, `track`, `selectedLayers`, `gui`, `space`. **Not in d3.pyi by name** — accessed via `guisystem` global.
- `D3State` (`Resource`) -- Project-wide state. Props: `stage`, `projectName`, `feed`, `devices`. Accessed via `state` global.
- `Stage` (`Object` > `Resource`) -- Root 3D scene. Props: `venue`, `ledScreens`, `projectors`, `cameras`, `surfaces`, `dmxLights`, `dmxScreens`, `lights`, `floor_size`, `floor_pos`, `floor_plan`, `ambientLight`, `ambientColour`.
- `Venue` (`Object` > `Resource`) -- Stage design variant. Prop: `props` (Array[Prop]).
- `Prop` (`Object` > `Resource`) -- Mesh object in scene. Props: `mesh`, `offset`, `rotation`, `scale`, `normalMap`, `luminosity`, `renderSettings`.
- `Object` (`Resource`) -- Base for all 3D stage objects. Props: `offset`, `rotation`, `scale`, `children`, `parent`, `local` (Mat), `world` (Mat), `mesh`, `renderLayer`. Methods: `add()`, `remove()`, `isInActiveStage()`, `findAllObjectsOfType()`, `centroid()`.
- `Space` (`Resource`) -- Stage scene container. Methods: `stage()`, `setAmbientOcclusionMode(int)`.
- `LocalGuiDisplay` (`Display` > `Object`) -- The local output display. Static: `LocalGuiDisplay.localGui()`.

## Access
```python
# Active stage (primary access path)
stage = state.stage                        # Stage — current project stage

# Venues and props
venue  = stage.venue                       # active Venue (rw)
props  = venue.props if venue else []      # Array[Prop]
prop   = resourceManager.loadOrCreate("objects/prop/my_prop.apx", Prop)

# All venues (multiple venue designs)
venues = resourceManager.allResources(Venue)

# Current editor state
track  = guisystem.track                   # current Track
layers = guisystem.selectedLayers          # Array[ReflectionValue] — selected layers in UI
```

## Stage Scene Configuration
```python
stage = state.stage

# Floor
stage.floor_size = Vec2(20.0, 20.0)        # width x depth, in meters
stage.floor_pos  = Vec(0, 0, 0)            # floor origin

# Ambient lighting
stage.ambientLight  = 1000.0               # lux
stage.ambientColour = Colour(1, 1, 1, 1)   # RGBA

# Rendering quality
stage.footprintsQuality = 1.0              # shadow buffer res multiplier; 0 = disabled
stage.autoSoftEdge = 1                     # toggle dynamic blend

# Screen/display lists (read access)
for s in stage.ledScreens:   print(s.description)
for p in stage.projectors:   print(p.description)
for c in stage.cameras:      print(c.description)
```

## Venues & Props
```python
# Create or switch venue
new_venue = resourceManager.loadOrCreate("objects/venue/ShowA.apx", Venue)
state.stage.venue = new_venue

# Add a prop to the active venue
prop = resourceManager.loadOrCreate("objects/prop/truss.apx", Prop)
markDirty(venue)
venue.props.append(prop)

# Position / orient a prop
prop.offset   = Vec(2.0, 0.0, 1.5)        # x, y, z in meters
prop.rotation = Vec(0.0, 45.0, 0.0)       # degrees around x, y, z
prop.scale    = Vec(1.0, 1.0, 1.0)
prop.luminosity = 0.8
```

## Object Hierarchy
```python
# Traverse children
for child in stage.children:
    print("%s (%s)" % (child.description, type(child).__name__))

# Find by type within sub-tree
screens = stage.findAllObjectsOfType(LedScreen)  # List[Object]

# Reparent
prop.parent.remove(prop)          # detach from current parent
other_object.add(prop)            # reattach under new parent

# World vs local transform
world_mat  = prop.world            # Mat — absolute transform
local_mat  = prop.local            # Mat — relative to parent

# Check if in the active stage
prop.isInActiveStage()             # bool
```

## Project & Version Info
```python
print(state.projectName)           # str — project name (read-only)
print(d3.majorVersion)             # str — Designer version string
print(d3.minorVersion)             # str — Designer minor version
```

## Gotchas
- `state.stage` is the **active** stage. A project may contain multiple `Stage` resources; use `resourceManager.allResources(Stage)` to enumerate all.
- `stage.venue` is a **single** `Venue` (the active design), not a list. Switch designs by assigning `state.stage.venue`. All designs are accessible via `resourceManager.allResources(Venue)`.
- `Object.offset` / `rotation` / `scale` are **relative to parent**, not world-space. Use `obj.world` for the absolute transform matrix.
- `GuiSystem` is not discoverable by name in d3.pyi (categories: GUI/Internal/System); use only via the `guisystem` global.
- `venue.props` is an Array type, not a Python list. Use `.append()` to add items, not `+` operator.
- `LocalGuiDisplay.localGui()` returns the local render-output display — not a scene prop; useful for display settings (resolution, colour profile, etc.).

## Userguide
- [Designer UI](https://help.disguise.one/designer/ui/designer-user-interface) | [Stage Navigation](https://help.disguise.one/designer/ui/navigating-the-stage) | [Editing the Stage](https://help.disguise.one/designer/ui/editing-the-stage)
- [Venues & Props](https://help.disguise.one/designer/ui/adding-venues-props) | [Designer Elements](https://help.disguise.one/designer/getting-started/designer-elements) | [Keyboard Shortcuts](https://help.disguise.one/designer/getting-started/designer-keyboard-shortcuts)
