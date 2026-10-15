# Subsystems

## Overview

Subsystems are the 95+ specialized service objects that power Designer's functionality. Each subsystem manages a specific domain (audio, video input, networking, rendering, etc.). Access them via `SubsystemManager`. Load this file when you need to discover or access subsystems.

> Run `python scripts/d3-ref.py --classes ClassName` for full interface details.

## Userguide

- https://developer.disguise.one/plugins/docs/

## Key Classes

- `SubsystemManager` — access via global `subsystems`
  - `getSystem(type)` → typed subsystem (raises if not found)
  - `maybeGetSystem(type)` → typed subsystem or None
  - `subsystems()` → list of all Subsystem instances

- `Subsystem` — base class
  - `name` [ro] — subsystem name
  - `isEnabled` [ro] — whether active

## Common Tasks

### List all subsystems

```python
result = []
for s in subsystems.subsystems():
    result.append({"name": s.name, "enabled": s.isEnabled})
return result
```

### Get a typed subsystem

```python
audio = subsystems.getSystem(AudioSystem)
print("Audio enabled: %s" % audio.isEnabled)
```

### Safe subsystem access

```python
rs = subsystems.maybeGetSystem(RenderStreamSystem)
if rs:
    print("RenderStream available")
else:
    print("RenderStream not available")
```

## Subsystem Catalog

### Media & Video
| Type | Description |
|------|-------------|
| `MediaManager` | Asset loading, media library |
| `VideoPrefetcher` | Video prefetch/cache pipeline |
| `ProxyMakerSystem` | Proxy generation |
| `MovieWriter` | Video recording/export |
| `RecordingSystem` | Session recording |

### Display & Rendering
| Type | Description |
|------|-------------|
| `DisplayManagerSubsystem` | Display/output management |
| `HoldOutputSystem` | Hold frame output |
| `SoftEdgeUpdateSystem` | Soft edge blending |
| `IndirectionSystem` | Indirection mapping |

### Video Input
| Type | Description |
|------|-------------|
| `LogicalVideoInSystem` | Logical video input management |
| `CameraVideoInSystem` | Camera capture input |
| `IPVideoInSystem` | IP/NDI video input |
| `LumaKeyVideoInSystem` | Luma key video input |
| `VideoInCaptureSystem` | Video capture system |
| `VideoInSystem` | Base video input |
| `PlaceholderVideoInSystem` | Placeholder inputs |
| `SharedVideoInVideoInSystem` | Shared video inputs |
| `RSCompressedVideoInSystem` | RenderStream compressed input |

### Networking
| Type | Description |
|------|-------------|
| `D3NetManagerSystem` | Multi-machine networking |
| `SessionDiscoverySystem` | Session discovery |
| `SessionSystem` | Session management |
| `CommsSystem` | Communications |
| `ShadowResourceHTTPSystem` | Resource sync over HTTP |

### Control Protocols
| Type | Description |
|------|-------------|
| `Dmx` | DMX input/output (use `Dmx`, not `DmxSystem`) |
| `MidiSystem` | MIDI input/output |
| `MtcSystem` | MIDI timecode |
| `ArtNetSystem` | Art-Net protocol |
| `StreamingACNSystem` | sACN (E1.31) |
| `SockPuppetSystem` | Sockpuppet control protocol |
| `HTTPSockpuppetSystem` | HTTP-based sockpuppet |

### Audio
| Type | Description |
|------|-------------|
| `AudioSystem` | Audio playback/routing |

### Calibration
| Type | Description |
|------|-------------|
| `CalibratorSystem` | Projector calibration |
| `CameraCalibrationSystem` | Camera calibration |
| `OpticalCalibratorSystem` | Optical calibration |
| `OptiCalCaptureSystem` | OptiCal capture |

### RenderStream
| Type | Description |
|------|-------------|
| `RenderStreamSystem` | RenderStream integration |

### Hardware-Specific
| Type | Description |
|------|-------------|
| `BlueFishSystem` | Bluefish video I/O |
| `MatroxSystem` | Matrox video I/O |
| `RgbEasySystem` | RGB Easy capture |
| `NewTekNDIRelaySystem` | NDI relay |

### Monitoring
| Type | Description |
|------|-------------|
| `MonitoringManager` | System monitoring/metrics |
| `AlertNotificationSystem` | Alerts and notifications |

### Other
| Type | Description |
|------|-------------|
| `DomainManager` | Domain management |
| `DeltaSystem` | Delta frame handling |
| `NotchLCSubsystem` | Notch LC integration |
| `CITPSubsystem` | CITP protocol |

## Access Patterns

### Via global (most common)

```python
audio = subsystems.getSystem(AudioSystem)
dmx = subsystems.getSystem(Dmx)
d3net = subsystems.getSystem(D3NetManagerSystem)
```

### Via d3NetManager (networking shortcut)

```python
# d3NetManager is pre-imported, no need for subsystems.getSystem
machines = d3NetManager.machines
```

### Via state (project objects)

```python
stage = state.stage    # Stage object
feed = state.feed      # FeedScene object
```

## Gotchas

- The DMX subsystem type is `Dmx`, not `DmxSystem`
- `getSystem()` raises if the subsystem isn't registered — use `maybeGetSystem()` for safe access
- Some subsystems are only available when certain hardware is present
- Subsystem names (`.name`) may differ from their type names
- Not all subsystems expose useful Python properties — many are internal C++ services. Always check with `d3-ref.py --classes` before assuming an interface exists
