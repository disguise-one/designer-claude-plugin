---
name: d3-designer
description: >
  Automate disguise d3 / Designer media-server projects with the d3service MCP
  tools and the in-project Python plugin API. Covers project and session
  lifecycle, transports and timeline, notes, tracks, layers and effect modules,
  content and media, stage and projection mapping, devices (DMX, MIDI, serial,
  OSC), multi-machine networking, RenderStream and failover, audio, colour and
  CDL, video input, tracking, feeds and outputs, mixed reality, camera
  calibration (QuickCal, OmniCal), system and network state, and shot recorder.
  Use this skill for ANY disguise d3 automation, scripting, or control task,
  even when the user only says "d3", "Designer", or "media server", or names a
  product area (transport, RenderStream, calibration, and so on). Do not use it
  to build or test the d3 source code, for Jira or CI work, or to start and
  stop d3 processes outside a project task.
---

# d3 Designer

One skill for the full disguise d3 product surface. There are two ways to act on d3:

1. **Explicit MCP tools** of the d3service server (for example `status_list_health`, `transport_play`). Prefer them when the operation has a tool.
2. **Python fallback** with the `python_execute` tool. Use it for anything that has no tool, for changes to many objects, and for queries that are clearer as one Python script than as many tool calls.

Some hosts add a prefix to tool names (for example `mcp__d3service__python_execute`). The names in this skill have no prefix. The names that `tools/list` gives are the final names.

## How to load this skill's files

d3service serves this skill over MCP. A client that has only the MCP connection (no copy of the skill folder on disk) reads every file with `resources/read` and a `skill://` URI:

| What | URI |
|---|---|
| This file | `skill://d3-designer/SKILL.md` |
| A reference | `skill://d3-designer/references/<name>.md` (for example `skill://d3-designer/references/timeline.md`) |
| A script | `skill://d3-designer/scripts/<name>` (for example `skill://d3-designer/scripts/mcp_helpers.py`) |

`skills/list` and `skills/get` (with the skill URI) describe the skill. `resources/directory/read` with `skill://d3-designer/references` lists a folder.

Every path in this skill is relative to the skill root. `references/timeline.md` means `skill://d3-designer/references/timeline.md`. Read the matching reference before you write non-trivial Python.

**The shell scripts are optional.** The `scripts/*.ps1` and `scripts/d3-ref.py` helpers need a local copy of the skill folder and a shell on the same machine. If the host gives you only MCP, ignore them and use the MCP-only steps in each section. Do not try to run a script from a `skill://` URI.

## Core Workflow

1. Translate the user's words into a d3 task domain (project, transport, notes, media, RenderStream, calibration, stage, layers, devices, network, feed, audio, and so on).
2. **Try an explicit MCP tool first.** Check `references/mcp-capabilities.md` for the routing table. Use the dedicated tool when it exists. It is safer, smaller, and checked.
3. **Use `python_execute` when no tool fits**, when the change spans many objects, or when conditional logic across resources needs many tool calls. Read the reference for the domain (Domain Routing Table below) before you write non-trivial Python. `SKILL.md` alone does not give enough API detail.
4. **Identify objects by `uid`** when a tool gives both `name` and `uid`, because names can be the same. When you report, give both name and uid.
5. **Verify after a change** with the matching list, get or status tool. For any stage or spatial change, also do the visual verification (`references/visual-verification.md`).

## Safety

State sensitive actions plainly before you run them. These actions are sensitive: playback, media deletion, project lifecycle (`service_project_*`), failover, reimage, network/IP/DHCP configuration, calibration capture, sockpuppet live changes, OS imaging. Use the least destructive tool that does the job. Keep automation in the active project and session. Do not import os, subprocess or network modules in `python_execute` unless the user asks.

**Dead session or busy session:** if `/api/session/*` returns nginx **502** while `service_system_list_projects` still works, the **session process is gone**. Restart the project. A retry does not help. A common cause is VRAM exhaustion from oversized DirectProjection canvases. See the DP/VRAM audit in `references/stage-projection.md`.

## MCP Routing (high level)

Read `references/mcp-capabilities.md` for the full tool list. Quick map:

| Task | Tool name pattern |
|---|---|
| Project / session / health / notifications | `status_*`, `service_project_*`, `service_system_*` |
| Transport play / stop / jump / speed / volume | `transport_*` (legacy) or `transport_control_*` (v1, UID-addressed) |
| Notes (named annotations) | `notes_list`, `notes_get`, `notes_set` |
| Media metadata / provisioning / tasks / sources | `content_*`, `service_media_*`, `service_content_sources_*` |
| Resources / thumbnails / indirections / sequencing | `resources_*`, `thumbnails_*`, `indirections_*`, `sequencing_*` |
| RenderStream / clusters / failover | `render_stream_*`, `renderstream_*`, `failover_*` |
| Colour / CDL | tools with `colour` and `cdl` in the name (see `references/mcp-capabilities.md`) |
| Sockpuppet (live parameter changes) | `sockpuppet_*` |
| Mixed Reality / camera calibration / QuickCal / OmniCal | `mixed_reality_*`, `camera_calibration_*`, `quickcal_*`, `omnical_*` |
| Shot recorder | `shot_recorder_list_recorders`, `shot_recorder_record_shot` |
| Network adapters / hostname / IP / DHCP | `service_remote_config_*` |
| Diagnostics / GPU outputs / VFCs / OS info | `service_system_*` |
| Python execute / register module | `python_execute`, `python_register_module` |

## Python Execute (fallback)

```python
python_execute(
    moduleName="my_task",
    script="return resourceManager.allResources(Track)"
)
```

Bare names are already imported in the module-less context (no `from d3 import *` needed). For larger or reusable code, register a module first with `python_register_module`. A registered module needs `from d3 import *` at the top.

### Helper module: `mcp_helpers.py`

The file is `scripts/mcp_helpers.py`. Register it once per session. With MCP only, read `skill://d3-designer/scripts/mcp_helpers.py` and pass the text as `contents`:

```
python_register_module(
    moduleName="mcp_helpers",
    contents=<contents of scripts/mcp_helpers.py>)
```

Then call the functions by bare name. `moduleName="mcp_helpers"` runs the script in the namespace of the registered module:

```
python_execute(
    moduleName="mcp_helpers",
    script="return search_resources('sunset')")
```

(From any *other* registered module, use `import user_module_mcp_helpers`. See `references/plugins.md` for the cross-module convention.)

It provides:

- `search_resources(keyword, types=[VideoClip, AudioTrack, DxTexture])` - fuzzy resource finder.
- `compute_screen_bbox(screens)` - world-space AABB of Displays (handles rotation and scale).
- `set_layer_values(layer, beat, **kwargs)` - keyframe layer fields (Float / Resource).
- `get_visualiser_camera()` - return or create the dedicated `mcp_visualiser` Camera on the stage.
- `capture_stage(output_dir, ..., auto_position=True)` - **fallback** for a controlled overview pose. Prefer the `internal_gui_capture` tool for inline captures. It renders with the dedicated `mcp_visualiser` camera, NOT `Camera.localVisualiserCamera()` (the editor preview camera, which would move the user's view). See `references/visual-verification.md`.
- `create_lineup_track()` / `checkout_mapping(path)` / `cleanup_checkout()` - per-screen test-pattern lineup track.

Rule: objects that the helpers make start with `mcp_` (the `mcp_lineup` track, the `mcp_visualiser` camera, the `mcp_lineup_*` mappings). When the task is done, remove them: call `cleanup_checkout()`, and remove the camera if the task made it. No helper removes the user's displays. Remove displays only when the user asks for it.

### References and API lookup (optional local tool)

If you have a local copy of the skill folder and a shell, one tool reads the references and looks up the API:

```bash
python scripts/d3-ref.py stage-projection,layers-modules --classes LedScreen,Parallel --search radar
python scripts/d3-ref.py --classes Track --doc Track.addNewLayer
python scripts/d3-ref.py --classes Track --inherited
python scripts/d3-ref.py --list
python scripts/d3-ref.py --help
```

`d3-ref.py` prints the domain markdown files **and** runs `d3-pyi-lookup.py` in one call. The lookup tool reads a `d3.pyi` type stub. By default it downloads the public stub from `https://developer.disguise.one/assets/d3.pyi` and keeps it in the `d3-designer-skill` folder of the local application data folder (it refreshes the file when it is older than one day). **The public stub can be older than your build.** If you have a stub from your own build, use `--stub PATH` or the `D3_PYI_PATH` environment variable. To refresh the cache at once, run `python scripts/fetch_d3_pyi.py`.

Without a local copy or a shell, do the same with MCP only: read the reference with `resources/read`, and introspect the live API with `python_execute` and `dir()`. Use a **name whitelist** (see Python Rules). A blanket `getattr` over `dir()` raises an error.

## Python Rules

- **Python 2.7** runtime. Main thread only. `threading` and `sys` are blocked.
- **Properties have no `()`**: `layer.description`, not `layer.description()`.
- **`return`** gives JSON in `returnValue`. `print()` goes to `pythonLog`.
- **Traceback line numbers:** the engine wraps your script in a function. Your line 1 is reported as line 10, so subtract 9 from a reported line number. (This follows from the wrapper code. Check it with one deliberate error if the exact number matters.)
- **`Action`/`Widget` attributes raise `TypeError`.** Avoid them. `LayerView` noise in d3Log is harmless.
- **`guisystem.track`** is the current track. Do not hard-code resource paths.
- **After `loadOrCreate` on a Display**, call `obj.rename(obj.path)` to start its initialisation.
- **Module-less execute:** bare names are already imported. Do not use `from d3 import *`. Registered modules start with `from d3 import *` and are imported as `user_module_<name>`.
- **No comments** in generated scripts. Keep them small and idempotent. Start with read-only code when the API shape is not clear.
- **No parallel changes.** One project at a time. Python calls that change data run one after the other.
- **Some engine errors escape `try/except`.** `getattr` on `Action` or `ParamAction<uint>` attributes raises `TypeError: Access to object of type 'Action' is not allowed`. `FieldSequence.eval()` on a `ResourceSequence` raises `RuntimeError: Cannot convert ResourceSequence...`. **Both bypass a surrounding `except Exception`.** A "dump every attribute" loop therefore always fails on real objects. **Introspect with a name whitelist. Never use a blanket `getattr` over `dir()`.**
- **Do not read bulk mesh data.** `mesh.triangles` and `mesh.verts` are so large that JSON serialisation can time out.
- **A timeout is not always a failure.** A long single script (for example `mesh.reloadExternal()` and `updateMesh()` on a very large OBJ) can return HTTP 500 `TimeOutError` and still finish the work. **Make one change per call for large payloads. Query again instead of a retry.**
- **`d3.gpuLoad` is not reliable** (the units and values are not consistent). Use `status_list_health` -> `status.averageFPS` instead.

## Dirtying and Saving Resources

- Assigning a property on a `Resource` marks it dirty by itself (`screen.resolution = Vec2(1920, 1080)`).
- Call `markDirty(owner)` **before** you change a non-Resource, non-scalar value in place (`stage.ledScreens.append(screen)`, `del stage.ledScreens[:]`, `resource.offset.x = 5.0`). The owner's property setter does not run for these changes.
- Call `saveOnDelete()` only for **unnamed sub-resources** (`resource.path == ""`), on the named parent.
- A new resource (from `loadOrCreate` or `addNewLayer`) needs none of these.

Details and examples: `references/resources.md`.

## Globals (inside `python_execute`)

| Object | Type | Key members |
|---|---|---|
| `d3` | `D3` | `projectName`, `projectFolder`, `majorVersion`, `gpuLoad`, `space` |
| `state` | `D3State` | `state.stage`, `state.feed` |
| `subsystems` | `SubsystemManager` | `subsystems.getSystem(TypeName)` |
| `resourceManager` | `ResourceManager` | `load`, `loadOrCreate`, `allResources`, `search`, `remove` |
| `guisystem` | `GuiSystem` | `track`, `selectedLayers`, `player`, `currentTransportManager` |
| `d3NetManager` | `D3NetManager` | `machines` |

## Resource Patterns

Paths are lowercase with the `.apx` extension: `objects/<typename>/<name>.apx` (visible) or `internal/...` (hidden). The type segment is `type(obj).__name__.lower()`.

```python
resourceManager.load("objects/track/song1.apx", Track)
resourceManager.loadOrCreate("objects/ledscreen/my screen.apx", LedScreen)
resourceManager.allResources(LedScreen)
resourceManager.search("objects/ledscreen")            # prefix match
resource.duplicate(resource.path.replaceFilename("copy_name"))
```

To delete a resource, first remove the stage's references to it, then use `moveToTrash()` and `emptyTrash([...])`. Do not use `resourceManager.remove(path)`. The full steps are in `references/resources.md`.

## Visual Verification (mandatory for any stage or spatial change)

After a change to stage layout, projection mapping, or display geometry, capture the result and look at it before you say the task is complete. Use the `internal_gui_capture` tool (it returns the image inline). If it times out, or you need a set camera pose, use the fallbacks. All the steps, the fallbacks and the post-build checklist are in `references/visual-verification.md`. Do not present a flawed result as complete.

## Project Lifecycle

Prefer the MCP tools: `service_project_start_local`, `service_project_quit_local`, `service_project_restart_local`, `service_project_force_quit_local`.

The MCP has no tool to make a new blank project. A local copy of the skill folder has a script for it. It unpacks the `blank.zip` that is in the install (in the `build\msvc` folder), renames the `.d3` file, and then starts d3:

```bash
pwsh -File scripts/d3-designer.ps1 -Action create-blank -Target release -ProjectName "my project"
```

`-Target` is the name of a d3 installation. `release` is the install in Program Files. To use another install, set the `D3_INSTALL_ROOT` environment variable (the target is then `env`), or make a `d3-config.json` next to the scripts (see `scripts/config.example.json`). Add `-DryRun` to see what the script would do before it stops or starts anything. The `start` and `create-blank` actions stop a running d3 first, so state this to the user before you run them.

## Domain Routing Table (Python references)

Read the relevant file before you write non-trivial Python. All files are in `references/`. The class names are the main classes of each domain. Look up the exact members in `d3.pyi`.

| Domain | Reference | Key classes |
|---|---|---|
| Timeline / playback | `timeline.md` | `SuperTrack`, `Track`, `TransportManager`, `Cue`, `TransportCommand` |
| Layers & effects | `layers-modules.md` | `Layer`, `Module` and its subclasses |
| Video content | `content-media.md` | `VideoAsset`, `VideoClip` |
| Stage / projection | `stage-projection.md` | `LedScreen`, `DirectProjection` (`mode`/VRAM warning), `Parallel`, `Prop` (`displayMode`) |
| Lighting & rendering (previz) | `lighting-rendering.md` | `StageRenderSettings`, `Light`, `Stage` ambient/area lighting |
| Meshes from Blender / OBJ | `blender-meshes.md` | axis mapping, UV authoring, diffuse bake |
| DMX / MIDI / serial / OSC | `devices-control.md` | `DmxDevice`, `DmxDriver`, `MidiSystem`, `SerialDevice`, `OscDevice` |
| Multi-machine networking | `networking.md` | `Machine`, `D3NetManager` |
| RenderStream | `renderstream.md` | `RenderStreamModule`, `RenderStreamCluster` |
| Audio | `audio.md` | `AudioSystem`, `AudioTrack` |
| Colour management | `colour.md` | `ColourProfile`, `CDL` |
| Video input | `video-input.md` | `LogicalVideoInDevice` |
| Tracking | `tracking.md` | `ObjectTrackingSource`, `ScreenPositionDriver` |
| Feed / output | `feeds-outputs.md` | `FeedScene`, `ScreenConfiguration`, `FeedHeadConfig` |
| Genlock | `genlock.md` | `Machine`, `DisplayAdapterList`, `DisplayOutputVFC` |
| Expressions | `expressions.md` | Expression syntax & system variables |
| Resources | `resources.md` | `ResourceManager`, `Resource` |
| Subsystems | `subsystems.md` | `SubsystemManager` |
| GUI / editor | `gui-editor.md` | `GuiSystem`, `Widget`, `selectedLayers` |
| Plugins | `plugins.md` | Plugin system |
| Calibration / xR APIs | `apis.md` | `APIEventTransport`, `CameraCalibrationSystem`, `OpticalCalibrator` |
| d3 Manager | `d3manager.md` | `D3NetManager`, `Machine`, `PathsManager` |
| Getting started | `getting-started.md` | Basic show recipe (clear, screens, mapping, layers, capture); licensing |
| VP / xR workflows | `workflows-vp.md` | Multi-system patterns |
| OSC / SockPuppet | `workflows-general.md` | `SockPuppetSystem`, `OscControlModule`, `OscDevice` |
| Visual verification | `visual-verification.md` | Capture tools, fallbacks, post-build checklist |
| MCP tool catalog | `mcp-capabilities.md` | All d3service tools (a hint; `tools/list` is final) |

## Response Checklist

1. Pick the MCP tool from `references/mcp-capabilities.md` and call it directly when one exists.
2. Otherwise read the domain reference (with `resources/read`, or with `d3-ref.py` if you have a local copy), then run a small Python script with `python_execute`.
3. Check `returnValue` and errors. For a Python error, subtract 9 from the reported line number.
4. Verify with the matching list, get or status tool.
5. **Visual verification (mandatory for stage and spatial changes).** Capture with `internal_gui_capture` (the image comes back inline) and judge it critically. Use `d3-capture-frame.ps1` only when you need a set overview pose. Do not present a flawed result as complete.
