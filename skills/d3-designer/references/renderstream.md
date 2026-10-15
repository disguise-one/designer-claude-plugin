# RenderStream

## Key Classes
- `RenderStreamModule` (`RenderStreamModuleBase` > `ProjectionAwareModule` > `Module` > `Resource`) — Layer module for remote/local render engine control. Key properties: `mode`, `sceneName`, `fields`, `customEventTriggerMode`, `schemaGeneration`. Methods: `getValue()`, `setValue()`, `getContainerValue()`.
- `RemoteParameterSchema` — Schema entry from `module.fields` (read-only list). Describes an exposed parameter from the engine.

## Access
```python
# RenderStreamModule lives on a layer — access via the layer's module property
layer = resourceManager.allResources(Layer)[0]
rs = layer.module  # RenderStreamModule (or None/different type if not an RS layer)

# Find all RenderStream modules in the project
rs_modules = [l.module for l in resourceManager.allResources(Layer)
              if isinstance(l.module, RenderStreamModule)]
```

## Playback Mode & Scene
```python
# mode: 0=Locked, 1=Free-run, 2=Normal, 3=Paused
rs.mode = 2          # Normal (engine follows Designer transport)
rs.mode = 1          # Free-run (engine runs independently)

# Scene selection (maps to UE levels/maps or Notch block scenes)
rs.sceneName = "Level_Night"

# Trigger mode for custom events: 0=On keyframe, 1=On reset, 2=On change
rs.customEventTriggerMode = 2
```

## Exposed Parameters (Remote Control)
```python
# List schema fields (read-only, populated when workload is running)
for field in rs.fields:
    print(field)  # RemoteParameterSchema objects

# Read/write exposed parameters by key (key = parameter name from engine)
val = rs.getValue("FogDensity")    # ReflectionValue (or None if param not found)
rs.setValue("FogDensity", val)

# Container parameters (grouped, e.g. transform)
val = rs.getContainerValue("CameraTransform")  # ReflectionValue (or None)
```

## Module Properties (inherited)
```python
rs.mapping     # Projection — which screens/mapping receives the stream
rs.brightness  # float — module brightness
rs.blendMode   # int — compositing mode with layers below
rs.tint        # Colour — tint overlay
```

## Schema
The engine plugin (UE, Unity, TouchDesigner, Notch) auto-generates a JSON schema
file describing exposed parameters. Designer reads this to populate `rs.fields`
and present controls in the RenderStream Layer editor. `rs.schemaGeneration`
increments each time the schema is refreshed.

## Failover
Failover uses the Understudy (backup) pattern from the d3net cluster. Configure
via the Cluster Workload widget on the RenderStream Layer. The d3net Network
Session widget monitors primary/understudy stream health. No Python API for
triggering failover directly — managed by Designer's network session.

## Monitoring (Graphs)
RenderStream graphs are read-only diagnostic displays in Designer UI:
- **Renderer** — processing load on render node
- **Stream** — bandwidth/transmission quality
- **Render Skew** — timing jitter in render output
- **Response Skew** — latency in control path
- **Profiling** — detailed CPU/GPU breakdown

No Python API to read graph data; use them for live diagnostics only.

## Engine Project Paths
Assets must be in the RenderStream Projects directory:
- Personal machine: the `RenderStream Projects` folder in the user's Documents folder
- RX/EX hardware: the `RenderStream Projects` folder at the root of the data drive

Default auto-discovered extensions: `.exe` (Unity/custom), `.uproject` (UE),
`.dfxdll` (Notch), `.nvol` (Volinga). For TouchDesigner `.toe` files, create
`permitted_custom_extensions.txt` in the RenderStream Projects root.

## Engine Notes

### Notch
- Place `.dfxdll` blocks in the RenderStream Projects folder.
- Multi-channel: each channel mapping creates a separate Notch block instance (scene rendered multiple times).
- Splitting across nodes requires an exposed camera in the block.

### TouchDesigner
- Requires TD 2022.28040+, Pro/TouchPlayer Pro license, Designer r22+.
- Uses three nodes: `RenderStream In CHOP` (sync + control channels), `RenderStream In TOP` (receive images), `RenderStream Out TOP` (send images).

### Unity
- Plugin location: `PROJECT_ROOT/Assets/DisguiseUnityRenderStream`.
- Uses DX11 (DX12 available from Unity directly).
- Splitting across nodes only works with 3D mappings (Camera Plate/Spatial), not 2D.
- Build as `.exe`; Designer reports engine as "Custom" (no version detection).

### Unreal Engine
- Plugin must be in project `/Plugins/` folder (not engine plugins).
- Scene selector: `None` (merge all), `StreamingLevels` (sublevel isolation), `Maps` (per-map scenes).
- Custom event trigger modes: `On keyframe`, `On reset`, `On change` (prefer over Event Tick for performance).
- Exposed parameters use Level Blueprint variables with `Instance Editable` enabled.
- Remote textures: expose `Texture Render Target 2D` variable → feed video layer into RS layer via arrow-input.
- UE can run as editor or packaged `.exe` (packaged offers better performance).

## Gotchas
- `rs.fields` is empty until a workload is running and the engine has connected.
- `rs.schemaGeneration` increments each time the schema is refreshed (poll or compare for change detection).
- Notch over RenderStream: only a single default channel — multiple channel mappings duplicate the render.
- Unity assets built as executables are reported as engine type "Custom"; no plugin version is surfaced.
- Mixing Disguise hardware product ranges in a cluster (e.g. RX + VX) is unsupported.
- TouchDesigner `.toe` files require `permitted_custom_extensions.txt` — not auto-discovered by default.

## Userguide
- [RenderStream Overview](https://help.disguise.one/workflows/renderstream/renderstream-overview) · [Remote](https://help.disguise.one/workflows/renderstream/renderstream-remote) · [Local](https://help.disguise.one/workflows/renderstream/renderstream-local) · [Failover](https://help.disguise.one/workflows/renderstream/renderstream-failover) · [Graphs](https://help.disguise.one/workflows/renderstream/renderstream-graphs) · [Schema](https://help.disguise.one/workflows/renderstream/renderstream-schema)
- [Notch](https://help.disguise.one/workflows/renderstream/notch/renderstream-notch) · [TouchDesigner](https://help.disguise.one/workflows/renderstream/touchdesigner/renderstream-touchdesigner) · [Unity](https://help.disguise.one/workflows/renderstream/unity/renderstream-unity) · [Unreal Engine](https://help.disguise.one/workflows/renderstream/unreal-engine/renderstream-unreal)
- [UE Project Setup](https://help.disguise.one/workflows/renderstream/unreal-engine/ue-project-setup) · [Exposed Parameters](https://help.disguise.one/workflows/renderstream/unreal-engine/exposed-parameters) · [Scene Levels](https://help.disguise.one/workflows/renderstream/unreal-engine/scene-levels) · [Remote Textures](https://help.disguise.one/workflows/renderstream/unreal-engine/remote-textures)
- [Extending RenderStream (SDK)](https://help.disguise.one/workflows/renderstream/extending-renderstream)
