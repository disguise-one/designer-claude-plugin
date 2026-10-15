# Virtual Production, xR & AR Workflows

## Key Classes

- `Camera` (`SlcAwareDisplay`) -- Physical or virtual camera. Props: `videoIn`, `spatialCalibration`, `setExtensionAlpha`, `setExtensionFeather`, `renderTimeToVideoReceiveTimeSec`, `videoReceiveTimeToTrackerReceiveTimeSec`, `fieldOfViewH`, `fieldOfViewV`, `focalLengthMM`, `k1k2k3`, `overscan`, `videoInCompositeFade`.
- `VirtualCamera` (`Camera`) -- xR/set-extension camera reprojected from a parent. Props: `parentCamera`, `relativePosition`, `relativeRotation`, `zoomScale`, `lensSource`, `outputType`, `activeMixedRealitySets` (read-only).
- `MixedRealitySet` (`CameraTallyDisplay`) -- MR Set compositing virtual and real content. Props: `indirectionController`, `calibrationLuts`, `onStageObjects`, `setExtensionMesh`, `activeCamera`, `cameraOverride`.
- `SpatialCalibrationConfig` (`Resource`) -- Spatial calibration data for a camera. Props: `observations`, `lensPoses`, `registration`, `calibrationSettings`. Methods: `calibrationReadSources()`, `loadLensCalibration(path)`, `saveLensCalibration(path, resolution)`, `resetTracking()`, `projectedPointsAtObservation(obs, apply_distortion)`.
- `CameraCalibration` (`Resource`) -- Mobile/lens calibration session. Props: `chessboardSizeDefault`, `chessSquaresSizeDefault`, `intrMatchTolerance`. Methods: `runCalibration()`, `saveCalibrationConfig()`.
- `CameraBookmark` (`Resource`) -- Saved camera view. Props: `pos`, `rotation`, `fieldOfView`, `name`. Methods: `setPerspective(pos, rot, fov)`, `setOrthographic()`, `setFeedView()`.
- `CameraCutControl` (`IndirectionControl` > `Module`) -- Timeline module for scripted camera switching. Props: `mrSet`, `indirectionController`, `selectedResource`.
- `CalibrationLutMapping` (`Resource`) -- LUT-to-MR-Set colour calibration mapping.

## Access

```python
# Cameras
cams = resourceManager.allResources(Camera)
vcam = resourceManager.loadOrCreate("objects/virtualcamera/main.apx", VirtualCamera)
cam  = resourceManager.loadOrCreate("objects/camera/a-cam.apx", Camera)

# MR Sets
mrs = resourceManager.allResources(MixedRealitySet)
mr  = resourceManager.loadOrCreate("objects/mixedrealityset/stage.apx", MixedRealitySet)

# Spatial calibration (linked via camera)
sc = cam.spatialCalibration

# Bookmarks
bks = resourceManager.allResources(CameraBookmark)
```

## Camera Configuration

```python
cam.videoIn            = resourceManager.loadOrCreate("objects/logicalvideoindevice/input1.apx", LogicalVideoInDevice)
cam.fieldOfViewH       = 60.0
cam.focalLengthMM      = 35.0
cam.overscan           = Vec2(1.1, 1.1)

vcam.parentCamera      = cam
vcam.relativePosition  = Vec(0, 0, 0)
vcam.relativeRotation  = Vec(0, 0, 0)
vcam.zoomScale         = 1.0
vcam.lensSource        = 0                # 0=FromParent, 1=Manual
vcam.outputType        = 0                # 0=Regular, 1=Spherical
```

## MR Set Configuration

```python
mr.onStageObjects      = [resourceManager.loadOrCreate("objects/ledscreen/wall.apx", LedScreen)]
mr.setExtensionMesh    = resourceManager.loadOrCreate("objects/mesh/extension.apx", Mesh)
mr.cameraOverride      = None             # None uses indirection controller

# Access active indirection controller
ctrl = mr.indirectionController           # e.g. SequencedIndirectionController / DMXIndirectionController
```

## Set Extension

```python
cam.setExtensionAlpha   = 1.0             # 1=enabled, 0=disabled
cam.setExtensionFeather = 32              # feather size in pixels
cam.videoInCompositeFade = 1.0            # 1=video in transmission
```

## Colour Calibration

```python
lut_map = resourceManager.loadOrCreate("objects/calibrationlutmapping/cal.apx", CalibrationLutMapping)
mr.calibrationLuts = [lut_map]
```

## Timing & Delay Calibration

```python
cam.renderTimeToVideoReceiveTimeSec       = 0.05    # seconds: render to camera capture
cam.videoReceiveTimeToTrackerReceiveTimeSec = 0.002 # seconds: video to tracker sync
```

## Spatial Calibration

```python
sc = cam.spatialCalibration
sc.calibrationReadSources()               # list available sources
sc.resetTracking()                        # clear registration

# Load / save lens calibration
sc.loadLensCalibration("intrinsics/my_lens")
sc.saveLensCalibration("intrinsics/my_lens", Vec2(1920, 1080))

# Inspect observations
for obs in sc.observations:
    pts = sc.projectedPointsAtObservation(obs, True)
```

## Camera Bookmarks

```python
bk = resourceManager.loadOrCreate("objects/camerabookmark/shot_a.apx", CameraBookmark)
bk.setPerspective(Vec(0, 1.5, -5), Vec(0, 0, 0), 60.0)
bk.name = "Shot A"
```

## Camera Switching on Timeline

```python
cut = resourceManager.loadOrCreate("objects/cameracutcontrol/cut1.apx", CameraCutControl)
cut.mrSet = mr
# CameraCutControl drives the MR Set's indirection controller
```

## Gotchas

- `activeMixedRealitySets` on `VirtualCamera` is read-only — assign cameras to the MR Set instead.
- `SpatialCalibrationConfig` is accessed via `camera.spatialCalibration`, not `allResources`.
- `renderLayer` uses integer enum values (e.g., 1 for "On Stage").
- Delay properties are in **seconds**, not milliseconds.
- `MixedRealitySet` camera switching is driven by `indirectionController.value`; the controller type (DMX, OSC, Sequenced, etc.) determines assignment patterns.
- `CameraCalibration` (mobile lens calibration) is separate from `SpatialCalibrationConfig` (spatial tracking).

## Userguide

- [Virtual Production overview](https://help.disguise.one/workflows/vp/virtual-production) | [xR overview](https://help.disguise.one/workflows/xr/xr-overview) | [AR overview](https://help.disguise.one/workflows/ar/ar-overview)
- [Spatial Calibration](https://help.disguise.one/workflows/xr/spatial-calibration) | [Colour Calibration](https://help.disguise.one/workflows/xr/colour-calibration) | [Camera Switching](https://help.disguise.one/workflows/xr/camera-switching)
- [Set Extension](https://help.disguise.one/workflows/xr/set-extension) | [Depth of Field](https://help.disguise.one/workflows/xr/depth-of-field) | [Shot Recorder](https://help.disguise.one/workflows/vp/shot-recorder-setup)
- [API xR Calibration](https://help.disguise.one/designer/apis/api-xr-calibration) | [Frustum Workflows](https://help.disguise.one/workflows/xr/frustum-workflows) | [Green Screen](https://help.disguise.one/workflows/vp/green-screen-workflow)
