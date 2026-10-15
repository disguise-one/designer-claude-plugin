# APIs

Designer exposes several API layers. The Python plugin covers transport events and xR/projector
calibration. The REST APIs (Developer Portal, SMC) are separate HTTP services, not Python classes.

## API Landscape

| API | Access | Purpose |
|-----|--------|---------|
| Python Plugin API | `mcp__d3service__python_execute` (or in-process `d3.*` globals) | All-domain Designer automation |
| Developer Portal REST | `mcp__d3service__*` tools (see `mcp-capabilities.md`) | Session/machine/transport/notes/media/calibration etc. |
| SMC REST API | direct HTTP via Developer Portal | Hardware monitoring: power, VFC, BMC, network |
| xR Calibration API | Python plugin classes below + MCP `mixed_reality_*` / `camera_calibration_*` / `quickcal_*` / `omnical_*` | Camera & projector calibration automation |
| RenderStream SDK | Native/C++ SDK | Frame sync for 3rd-party render engines |

The Developer Portal API is wrapped by the `mcp__d3service__*` tools — prefer those over raw HTTP. The SMC API and RenderStream SDK are external and not part of the Designer Python plugin.

## Key Classes

Entry points of the Python API for the APIs that have Python classes:

- `APIEventTransport` -- the transport that external API events drive.
- `CameraCalibrationSystem` -- the subsystem for xR camera calibration solves.
- `OpticalCalibrator` -- the OmniCal projector-camera calibration.

## API Event Transport

```python
# Bind transport to a TransportManager
tm    = guisystem.currentTransportManager
api_t = resourceManager.loadOrCreate("objects/apieventtransport/ext.apx", APIEventTransport)
api_t.transportManager = tm
api_t.cueMode = 0          # 0 = Global (All Tracks), 1 = Local (Current Track)

# fieldActivity lists currently active fields driven by the external API (read-only)
print(api_t.fieldActivity)
```

## xR Camera Calibration

```python
sys = CameraCalibrationSystem.get()
cal = resourceManager.load("objects/cameracalibration/studio.apx", CameraCalibration)
sc  = resourceManager.load("objects/spatialcalibrationconfig/main.apx", SpatialCalibrationConfig)

# Tune tolerances
cal.intrMatchTolerance = 0.8    # 0-1: how strictly intrinsics are matched
cal.intrMaxError       = 2.0    # max reprojection error (pixels) accepted

# Run calibration for all enabled observations
sys.runCalibrateAll(sc)
print("Overall error: %s" % sys.overallError)

# Per-observation inspection
for obs in resourceManager.allResources(CameraCalibrationObservation):
    if obs.enabledForCalibration:
        sys.runCalibrateForObservation(obs)
        print("  pos=%s error=%s" % (obs.solvedPos, obs.solvedError))

# Capture new observation from live camera
cam = resourceManager.load("objects/camera/main.apx", Camera)
sys.captureNewObservation(cam)

# Remove an observation
sys.deleteObservation(obs)
```

## OmniCal Projector Calibration

```python
oc = resourceManager.load("objects/opticalcalibrator/main.apx", OpticalCalibrator)

# Status
print("busy=%s capturing=%s" % (oc.isBusy(), oc.isCapturing()))

# Run plan, push warps, save camera positions to stage
task = oc.executePlan()        # returns OptiCalTask; poll oc.isBusy() for completion
oc.sendWarps()
oc.saveCalibratedCameras()

# Read configuration (properties are read-only via Python)
print("bandwidth=%s Gbit/s" % oc.cameraBandwidthGbit)
print("frame delay=%d frames" % oc.renderFrameDelay)
```

## Gotchas

- **Developer Portal / SMC API are not Python plugin classes** -- they are external REST services.
  Calling them from a plugin requires `urllib2`/`httplib`, not d3 objects.
- `CameraCalibrationSystem.get()` is a static method -- unlike most subsystems which are accessed
  via `subsystems.<Name>`.
- `OpticalCalibrator` properties are readable from Python but not writable (read via Python, modify in GUI).
- `OpticalCalibrator.executePlan()` returns `OptiCalTask` -- no `.wait()`; poll `oc.isBusy()`.
- `APIEventTransport.fieldActivity` is read-only; the external API pushes field values in.
- `CameraCalibration.cameraNames` is read-only; cameras associate through observations.

## Userguide
- [APIs Overview](https://help.disguise.one/designer/apis/api-overview) | [Developer Portal APIs](https://help.disguise.one/designer/apis/developer-portal-apis) | [SMC API](https://help.disguise.one/designer/apis/smc-api) | [xR Calibration API](https://help.disguise.one/designer/apis/api-xr-calibration)
- [Developer Portal](https://developer.disguise.one)
