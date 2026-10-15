# General Workflows (OSC, Sockpuppet, Motion Capture, EVO, ISAAC, NeRFs)

## Key Classes
- `OscDevice` (`Device` > `Resource`) -- OSC network endpoint. Props: `sendTargets` (List[`OscSendTarget`]), `receivePort`, `ipFromFilter`, `supportsSendingMessageBundles`. Methods: `addSendTarget(label, address, port, enabled)`, `removeSendTarget(index)`, `clearSendTargets()`, `send()`, `start()`, `stop()`.
- `OscCommand` (`Resource`) -- OSC address + arguments definition. Props: `address` (str), `arguments` (List[OscArgument]).
- `OscControlModule` (`Module` > `Resource`) -- Layer module that fires OSC commands on keyframes. Props: `osc_device`, `command`, `variable_1..4`, `auto_resend`.
- `SockPuppetSystem` (`Subsystem`) -- Sockpuppet subsystem. Static: `repatchAllLayers(className, personality)`, `deletePatch(patch)`. Props: `registry`.
- `HTTPSockpuppetSystem` (`Subsystem`) -- HTTP Sockpuppet subsystem (enables inbound HTTP layer control).
- `SockpuppetPersonality` (`Resource`) -- Named mapping of layer fields to DMX/OSC/HTTP control slots. Props: `className`, `nProperties`, `properties`. Methods: `addProperty(fieldName, displayName, group)`, `findProperty(fieldName)`, `reset()`.
- `SockpuppetProperty` (`Resource`) -- One controllable field inside a personality. Props: `fieldName`, `displayName`, `address`, `type` (0=8-bit,1=bank/slot,2=16-bit,3=RGB,4=string), `min`, `max`, `default`, `enabled`, `dmxChannelOffset`.
- `ControlPatch` (`Resource`) -- Live patch linking a layer to a personality. Methods: `controlsField(name)`, `inputValues()`.
- `SockPuppetVideoModule` (`Module`) -- Video layer type with Sockpuppet-aware properties. `getPersonality()` returns `ControlPatch` for patched modules.
- `HttpControlModule` (`Module`) -- Layer module that fires outbound HTTP requests. Props: `request` (HttpControlRequest), `trigger` (0=Always, 1=WhenPlaying).
- `HttpControlRequest` (`Resource`) -- HTTP call definition. Props: `url`, `method` (0=Get..4=Delete), `body`, `headers`.

## Access
```python
# OSC devices
dev = resourceManager.loadOrCreate("objects/oscdevice/my osc.apx", OscDevice)

# Sockpuppet subsystem + personalities
sp  = subsystems.getSystem(SockPuppetSystem)
reg = sp.registry                                    # SockpuppetPersonalityRegistry
all_p = resourceManager.allResources(SockpuppetPersonality)
pers  = resourceManager.load("objects/sockpuppetpersonality/myrig.apx", SockpuppetPersonality)

# Access module from a layer
track = guisystem.track
if track.layers:
    layer = track.layers[0]
    module = layer.module                          # OscControlModule, HttpControlModule, etc.
    patch  = module.getPersonality()               # runtime: ControlPatch or None
```

## OSC Device Configuration
```python
dev = resourceManager.loadOrCreate("objects/oscdevice/my osc.apx", OscDevice)
dev.clearSendTargets()
dev.addSendTarget("console", "192.168.1.100", 8000, True)   # every enabled target gets every message
dev.receivePort   = 9000
dev.ipFromFilter  = "192.168.1.50"   # blank = accept any sender
dev.supportsSendingMessageBundles = False

dev.start()       # activate listener/sender
dev.receiving     # bool -- currently receiving
```

## OSC Control Module (Send on Cue)
```python
# Create device and command separately
dev = resourceManager.loadOrCreate("objects/oscdevice/my osc.apx", OscDevice)
cmd = resourceManager.loadOrCreate("objects/osccommand/show go.apx", OscCommand)
cmd.address = "/show/go"

# Assign to module (requires existing layer with OscControlModule)
track = guisystem.track
layer = track.layers[0]  # or find/create a layer with OscControlModule
module = layer.module

module.osc_device  = dev
module.command     = cmd
module.variable_1  = 1.0
module.auto_resend = 0   # 0=On command keyframe, 1=Whenever variable changes
```

## Sockpuppet Personality (Define Controllable Fields)
```python
pers = resourceManager.loadOrCreate("objects/sockpuppetpersonality/rig.apx", SockpuppetPersonality)
prop = pers.addProperty("brightness", "Brightness", "Base")
prop.type    = 0        # 8-bit DMX
prop.min     = 0.0
prop.max     = 1.0
prop.default = 1.0
prop.address = "brightness"   # OSC sub-address
prop.enabled = True

# Inspect
for p in pers.properties:
    print("%s -> address=%s  type=%d  dmxOffset=%d" % (p.fieldName, p.address, p.type, p.dmxChannelOffset))

# Re-patch all layers of a class to this personality
SockPuppetSystem.repatchAllLayers("SockPuppetVideoModule", pers)

# Remove a patch
patches = resourceManager.allResources(ControlPatch)
for p in patches:
    if p.controlsField("brightness"):
        SockPuppetSystem.deletePatch(p)
```

## Motion Capture
Skeleton rigging and tracking-source binding are UI operations. From Python you can enumerate resources:

```python
skeletons = resourceManager.search("objects/skeleton")
sources   = resourceManager.search("objects/skeletalpointtrackingsource")
```

Vicon emulator requires a license; set up via Designer UI or Vicon Tracker software.

## EVO Visualisers (MA3D, Capture, Depence)
EVO connects external visualisers via NDI video and DMX/OSC camera position data:

- **NDI stream**: set up in the Designer UI. `d3.pyi` has no NDI output class. For NDI input, see `NewTekNDIRelaySystem` and `NewTekNDIRelayVideoIn`.
- **Camera position via DMX**: write to DMX universe channels
- **Camera position via OSC**: use `OscDevice` directly or `OscControlModule` on a layer
- **Capture**: uses 16-bit values; range -32,768 to 32,768 (full scale = 65,536)

## ISAAC Bridge & NeRFs
**ISAAC Bridge** (Smart Monkeys) integrates as a Designer panel plugin; no Python API in d3.pyi.

**Volinga NeRFs / Gaussian Splatting** render as a RenderStream workload — manage via
`RenderStreamChannel` and `RsAsset` resources (see `references/renderstream.md`).

## Gotchas
- OSC **bundles are not supported** — Designer processes individual OSC messages only.
- `OscDevice.send()` accepts an `OscMessage` object not exposed in d3.pyi — use `OscControlModule` on a timeline layer instead.
- `SockPuppetSystem.repatchAllLayers` takes the class name as a **string** (e.g. `"SockPuppetVideoModule"`), not a type object.
- `OscControlModule.command` is initially None — create an `OscCommand` resource and assign it.
- `Module.getPersonality()` returns `ControlPatch` for sockpuppet-patched modules, `None` for unpatchemd.
- `SockpuppetProperty.type` int values (0..4) have no named constants — use raw ints.
- HTTP **inbound** (remote HTTP control of layers) via `HTTPSockpuppetSystem` is separate from outbound `HttpControlModule`; requires a license.

## Userguide
- [OSC Overview](https://help.disguise.one/workflows/osc/osc-workflows-overview) | [OSC Sockpuppet](https://help.disguise.one/workflows/osc/sockpuppet) | [Sockpuppet Overview](https://help.disguise.one/workflows/sockpuppet/sockpuppet-overview) | [Patch Assignments](https://help.disguise.one/workflows/sockpuppet/patch-assignments) | [Bank Editor](https://help.disguise.one/workflows/sockpuppet/bank-editor) | [Personality Editor](https://help.disguise.one/workflows/sockpuppet/sockpuppet-personality-editor) | [HTTP Sockpuppet](https://help.disguise.one/workflows/sockpuppet/http/httpsockpuppet)
- [Motion Capture](https://help.disguise.one/workflows/motion-capture/motion-capture-overview) | [Skeleton](https://help.disguise.one/workflows/motion-capture/skinned-mesh-skeleton/skeleton) | [Skeletal Point Tracking](https://help.disguise.one/workflows/motion-capture/skinned-mesh-skeleton/skeletal-point-tracking-source)
- [EVO](https://help.disguise.one/workflows/evo/evo) | [MA3D](https://help.disguise.one/workflows/evo/ma3d) | [Capture](https://help.disguise.one/workflows/evo/capture) | [Depence](https://help.disguise.one/workflows/evo/depence) | [ISAAC Bridge](https://help.disguise.one/workflows/isaac-bridge/isaac-bridge) | [Volinga NeRFs](https://help.disguise.one/workflows/nerfs/volinga)
