# Tracking

## Key Classes
- `ObjectTrackingSource` (`Resource`) -- 6DOF input feed. Props: `driver`, `enabledFlags`, `driverSendingFlags`, `pos`, `rot`, `isReceiving`, `smoothReceiveTime`, `rotationDelayOffset`, `frameOfReference`.
- `CameraTrackingSource` (`ObjectTrackingSource`) -- camera pose + lens data. Adds lens read-only props: `focalLength`, `fieldOfViewH/V`, `aperture`, `focusDistance`, `sensorSize`, `centerShift`, `k1k2k3`, `lensDelayOffset`.
- `AxisObjectTrackingSource` (`ObjectTrackingSource`) -- per-axis object source (from PositionReceiver). Props: `xAxis/yAxis/zAxis/xrotAxis/yrotAxis/zrotAxis` (`ScreenPositionAxis`).
- `AxisCameraTrackingSource` (`CameraTrackingSource`) -- per-axis camera source. Adds lens axes: `focalLengthAxis`, `hFovAxis`, `focusDistanceAxis`, `focusEncoderAxis`, `zoomEncoderAxis`, etc.
- `CompositeCameraTrackingSource` (`CameraTrackingSource`) -- splits pose and lens from two sources. Props: `poseSource` (`ObjectTrackingSource`), `lensSource` (`CameraTrackingSource`).
- `GeneratedCameraTrackingSource` (`CameraTrackingSource`) -- auto-created by a driver. No extra props.
- `ScreenPositionReceiver` (`Device`) -- position receiver device. Props: `drivers`, `axes`, `expressions`, `frameOfReference`, `positionSamples`, `timeSamples`, `smoothingFactor`, `movementThreshold`, `prediction`. Methods: `createAxes()`, `clearAxes()`.
- `ScreenPositionAxis` (`Resource`) -- single axis within a receiver. Props: `id`, `object`, `property_`, `min_input/max_input`, `min_output/max_output`, `offset`, `status`, `prediction`, `smoothingFactor`.
- `ScreenPositionDriver` (`Resource`) -- base class for tracking drivers. Method: `generatedTrackingSources()`.
- `TrackingFlags` -- per-channel enable bits. Props: `pos`, `rot`, `focalLength`, `aperture`, `focusDistance`, `focusEncoder`, `zoomEncoder`, `k1k2k3`, `sensorWidth`, `aspectRatio`, `centerShift`.
- `Tracking6DOFState` (`TrackingVectorState`) -- live 6DOF data state. Props: `positionVector`, `velocityVector`, `accelerationVector`, `rotationVector`, `angularVelocityVector`, `angularAccelerationVector` (all `Vec`), `id`, `name`, `receiving`, `tReceived`, `receiveTimeout`.
- `TrackingScalarState` (`TrackingState`) -- live single-axis state. Props: `position`, `velocity`, `acceleration` (float), `id`, `name`, `receiving`.

## Access
```python
# Enumerate all tracking sources (base class catches all subtypes)
sources = resourceManager.allResources(ObjectTrackingSource)
cam_sources = resourceManager.allResources(CameraTrackingSource)

# Load by path (type segment is the lowercase class name)
src = resourceManager.load("objects/objecttrackingsource/my_tracker.apx", ObjectTrackingSource)
cam = resourceManager.load("objects/cameratrackingsource/cam1.apx", CameraTrackingSource)
rcv = resourceManager.load("devices/screenpositionreceiver/mocap.apx", ScreenPositionReceiver)

# Create or get (creates new if not found)
src = resourceManager.loadOrCreate("objects/objecttrackingsource/new_src.apx", ObjectTrackingSource)
```

## Tracking Source Configuration
```python
src = resourceManager.load("objects/objecttrackingsource/cam_body.apx", ObjectTrackingSource)

# Assign driver and control flags
driver = resourceManager.load("devices/screenpositiondriver/vr_tracker.apx", ScreenPositionDriver)
src.driver = driver
markDirty(src)                     # sub-object mutation (TrackingFlags fields)
src.driverSendingFlags.pos = True
src.driverSendingFlags.rot = True
src.enabledFlags.pos = True
src.enabledFlags.rot = True

# Smoothing and timing compensation
src.smoothReceiveTime = True
src.rotationDelayOffset = 0.0      # seconds; compensate rotation lag vs position

# Read live pose (read-only)
print(src.pos)                     # Vec (x, y, z)
print(src.rot)                     # Vec (rx, ry, rz)
print(src.isReceiving)             # bool
```

## Camera Tracking Source
```python
cam = resourceManager.load("objects/cameratrackingsource/main_cam.apx", CameraTrackingSource)

# Timing compensation for lens data lag
cam.lensDelayOffset = 0.005        # seconds

# Read live lens intrinsics (all read-only)
print(cam.focalLength)             # mm
print(cam.fieldOfViewH)            # degrees
print(cam.aperture)                # f-stop
print(cam.focusDistance)           # metres
print(cam.sensorSize)              # Vec2 (mm)
print(cam.centerShift)             # Vec2 (mm)
print(cam.k1k2k3)                  # Vec (lens distortion)

# Lock zoom/focus encoders
cam.lockZoomEncoderValue(True)
cam.lockedZoomValue = 0.5
cam.lockFocusEncoderValue(False)
```

## Composite Camera Tracking
```python
# Combine pose from one source, lens from another
comp = resourceManager.loadOrCreate("objects/compositecameratrackingsource/comp.apx",
                                     CompositeCameraTrackingSource)

pose_src = resourceManager.load("objects/objecttrackingsource/body.apx", ObjectTrackingSource)
lens_src = resourceManager.load("objects/cameratrackingsource/lens.apx", CameraTrackingSource)

comp.poseSource = pose_src         # ObjectTrackingSource for XYZ and rotation
comp.lensSource = lens_src         # CameraTrackingSource for lens data
```

## Position Receiver Device
```python
rcv = resourceManager.load("devices/screenpositionreceiver/stage_mocap.apx", ScreenPositionReceiver)
rcv.start()

rcv.positionSamples = 5            # 0 = disabled
rcv.timeSamples = 3
rcv.smoothingFactor = 0.5          # 0.0-1.0; higher = smoother but more latency
rcv.movementThreshold = 0.001      # metres; 0 = no threshold
rcv.prediction = 0.02              # seconds lookahead; 0 = disabled

# Auto-create axes from connected driver (if driver is configured)
if rcv.canCreateAxes():
    rcv.createAxes()               # populates rcv.axes

for axis in rcv.axes:
    print("%s -> object=%s prop=%s" % (axis.id, axis.object, axis.property_))
```

## Axis Configuration
```python
# Configure individual axis (from rcv.axes, or create standalone)
axis = resourceManager.loadOrCreate("objects/screenpositionaxis/axis_tx.apx", ScreenPositionAxis)

# Map driver output ID to d3 object property
axis.id = "Tx"                     # must match driver's output ID
axis.object = some_stage_object    # Object to drive
axis.property_ = "tx"              # property name (trailing _ avoids Python keyword)

# Value remapping: driver units -> d3 stage units (metres)
axis.min_input  = -2000.0
axis.max_input  =  2000.0
axis.min_output = -2.0
axis.max_output =  2.0
axis.offset     = 0.0

# Status and timing
axis.status = 1                    # 0=Disengaged, 1=Engaged
axis.prediction = 0.02
axis.smoothingFactor = 0.3

# Read current value (live)
print(axis.output)                 # float
```

## Driver's Generated Sources
```python
driver = resourceManager.load("devices/screenpositiondriver/freed.apx", ScreenPositionDriver)
for ts in driver.generatedTrackingSources():
    print(ts.description, ts.pos, ts.isReceiving)
```

## Gotchas
- `Tracking6DOFDriver` and `TrackingObject` do **not** exist in d3.pyi -- use `ObjectTrackingSource` and `ScreenPositionDriver` instead.
- `ScreenPositionReceiver` is a `Device` (path `devices/screenpositionreceiver/`); tracking sources are `Resource` (path `objects/<classname>/`).
- `TrackingFlags` is not an enum -- it's a struct with bool fields; set `src.enabledFlags.pos = True` directly.
- `pos` and `rot` on `ObjectTrackingSource` are **live read-only** values; to drive a stage object, assign it via `ScreenPositionAxis.object`.
- `property_` (trailing underscore) is the Python name for `property` on `ScreenPositionAxis` -- avoids Python keyword conflict.
- `createAxes()` overwrites existing axes -- call `canCreateAxes()` first and only call when intentionally re-generating.
- Lens intrinsics on `CameraTrackingSource` (`focalLength`, `sensorSize`, etc.) are **all read-only** live values; configure axis-mapped inputs via `AxisCameraTrackingSource`.
- `lensDelayOffset` compensates for lens data arriving after pose data; `rotationDelayOffset` does the same for rotation vs position within a single source.

## Userguide
- [Camera Tracking](https://help.disguise.one/designer/devices/camera-tracking) | [Object Tracking Source](https://help.disguise.one/designer/stage-setup/objects/object-tracking-source) | [Position Receiver](https://help.disguise.one/designer/devices/position-receiver)
- [Motion Capture Overview](https://help.disguise.one/workflows/motion-capture/motion-capture-overview) | [Skeleton](https://help.disguise.one/workflows/motion-capture/skinned-mesh-skeleton/skeleton) | [Skeletal Point Tracking Source](https://help.disguise.one/workflows/motion-capture/skinned-mesh-skeleton/skeletal-point-tracking-source) | [Vicon Emulator](https://help.disguise.one/workflows/motion-capture/vicon-emulator)
