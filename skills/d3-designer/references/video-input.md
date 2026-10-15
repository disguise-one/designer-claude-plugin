# Video Input

## Key Classes
- `LogicalVideoInDevice` (`LogicalDevice` > `Resource`) -- virtual video device mapping a physical capture input to a named resource. Key props: `localVideoIn`, `resolution`, `pixelFormat`, `interlaced`, `deinterlaceMethod`, `cropRectangle`, `layerStack`, `acesTransform`, `ocioTransform`.
- `VideoIn` -- physical hardware input channel. Props: `hardwareId`, `name`, `videoInFormat`, `isInitialised`. Methods: `getCurrentFrame(deinterlaceMethod)`, `field(iFromMostRecent)`.
- `VideoInFormat` (`Resource`) -- format descriptor. Props: `resolution`, `framerate`, `pixelFormat`, `interlaced`. Static: `VideoInFormat.make(name, resolution, interlaced, fps, pixelFormat)`.
- `VideoInSystem` (Subsystem) -- lists physical channels. Methods: `findVideoIn(hardwareId)`, `makeTeamedVideoInHardwareId(ids)`, `makeMultiviewVideoInHardwareId(src, roi)`.
- `VideoInDeviceMap` (`DeviceMap` > `Resource`) -- maps hardware identifiers to logical devices. Static: `VideoInDeviceMap.getLogicalDevices()`.
- `HardwareVideoInIdentifier` (`HardwareIdentifier` > `Resource`) -- hardware device with `currentFormat` and `formats` list.
- `IPVideoInSystem` (Subsystem) -- ST 2110 / NDI. Props: `group` (`ActiveIPVideoInGroup`). Methods: `downloadSDP(url)`.
- `PersistentIPVideoIn` (`Resource`) -- individual IP stream. Props: `streamName`, `streamType` (0=Unknown, 1=ST2110, 2=NDI), `ndiStreamName`, `width`, `height`. Methods: `apply()`.
- `AcesInputTransformParameters` -- ACES IDT config. Props: `type`, `genericCurve`, `genericSpace`.

## Access
```python
# Logical virtual devices (resource path-based)
dev = resourceManager.load("objects/logicalvideoindevice/cam1.apx", LogicalVideoInDevice)
all_devs = VideoInDeviceMap.getLogicalDevices()           # all logical video devices

# Physical channels via subsystem
vis = subsystems.getSystem(VideoInSystem)
vin = vis.findVideoIn("AJA-KONA-0")                       # VideoIn by hardware ID
for ch in vis.inputChannels:                              # ChannelInfo list
    print(ch.hardwareId, ch.name)

# Hardware identifier from device map
dev_map = resourceManager.allResources(VideoInDeviceMap)[0]
hw = dev_map.getHardwareById("AJA-KONA-0")               # HardwareVideoInIdentifier or None

# IP video subsystem
ip_sys = subsystems.getSystem(IPVideoInSystem)
ip_group = ip_sys.group                                   # ActiveIPVideoInGroup or None
if ip_group:
    for stream in ip_group.activeIPVideoInGroup:          # List[PersistentIPVideoIn]
        print(stream.streamName, stream.streamType)
```

## Logical Device Configuration
```python
dev.setFormat(Vec2(1920, 1080), False, "YUV422")  # resolution, interlaced, pixelFormat
dev.resolution = Vec2(3840, 2160)
dev.pixelFormat = "RGBA"
dev.interlaced = 0                                # 0=progressive, 1=interlaced
dev.deinterlaceMethod = 2                         # see De-interlacing section
dev.cropRectangle = Rect(0, 0, 1.0, 1.0)         # UV space 0-1
dev.cropOffset = Vec2(0, 0)                       # pixel offset
dev.cropSize   = Vec2(1920, 1080)                 # pixel size

# Assign physical input to logical device
vis = subsystems.getSystem(VideoInSystem)
dev.localVideoIn = vis.findVideoIn("AJA-KONA-0")

# Map hardware via device map
dev_map = resourceManager.allResources(VideoInDeviceMap)[0]
hw = dev_map.getHardwareById("AJA-KONA-0")
if hw:
    dev_map.mapDevice(hw, dev)
```

## 4K Quad Link & Multiview
```python
# Quad-link: team 4 SDI inputs into a single 4K virtual input
# Only supported on Pro and Gx machines (not Gx 1), requires r14.3+
vis = subsystems.getSystem(VideoInSystem)
hw_ids = ["AJA-KONA-0", "AJA-KONA-1", "AJA-KONA-2", "AJA-KONA-3"]
try:
    teamed_hw = vis.makeTeamedVideoInHardwareId(hw_ids)   # HardwareVideoInIdentifier

    # Use teamed identifier like any other hardware
    dev_map = resourceManager.allResources(VideoInDeviceMap)[0]
    dev_map.addHardware(teamed_hw)
    dev = resourceManager.load("objects/logicalvideoindevice/cam1.apx", LogicalVideoInDevice)
    dev_map.mapDevice(teamed_hw, dev)
except RuntimeError:
    # Raised if hardware IDs don't exist or not supported on this machine
    pass

# Multiview: crop a region of interest from a source input
src_hw = dev_map.getHardwareById("AJA-KONA-0")
if src_hw:
    roi = Rect(0, 0, 960, 540)
    mv_hw = vis.makeMultiviewVideoInHardwareId(src_hw, roi)
```

## IP Video (ST 2110 / NDI)
```python
# ST 2110 is PRERELEASE. Requires:
#   - enableIPVideo option switch set to 1
#   - Mellanox NIC (VX and GX range only — EX range NOT supported)
ip_sys = subsystems.getSystem(IPVideoInSystem)
group = ip_sys.group

if group:
    streams = group.activeIPVideoInGroup                  # List[PersistentIPVideoIn]

    # Configure an ST 2110 stream (key fields from PersistentIPVideoIn / st2110Details):
    if streams:
        streams[0].streamType = 1                         # 1=ST2110
        streams[0].streamName = "Camera1"
        streams[0].width  = 1920
        streams[0].height = 1080
        # st2110Details holds: port, framerateNumerator, framerateDenominator (1 or 1001),
        #                      bitDepth (8/10/12), subSample (4:2:2/4:4:4/RGB), dst, src
        streams[0].apply()                                # activate changes

    # NDI stream
    if len(streams) > 1:
        streams[1].streamType = 2                         # 2=NDI
        streams[1].ndiStreamName = "STUDIO-PC (Camera)"
        streams[1].apply()
```

## De-interlacing
```python
# deinterlaceMethod is an int. Query available methods at runtime:
name = LogicalVideoInDevice.deinterlaceMethodName(2)      # method name for index 2
help_text = LogicalVideoInDevice.getDeinterlaceHelpText() # all methods with descriptions

dev = resourceManager.load("objects/logicalvideoindevice/cam1.apx", LogicalVideoInDevice)
dev.interlaced = 1
dev.deinterlaceMethod = 3
```

## ACES & Colour
```python
# ACES IDT on logical device
params = AcesInputTransformParameters()
params.type = 1                    # IDT type (0=Off, others are camera-specific)
params.genericCurve = 0
params.genericSpace = 0

dev = resourceManager.load("objects/logicalvideoindevice/cam1.apx", LogicalVideoInDevice)
dev.acesTransform = params
dev.ocioTransform = OcioColourSpace()   # set OCIO colour space if not using ACES
```

## VideoClip Integration
```python
# When a VideoClip uses live input, clip.isVideoIn == True
for clip in resourceManager.allResources(VideoClip):
    if clip.isVideoIn:
        ldev = clip.logicalVideoIn                        # LogicalVideoInDevice (read-only)
        print("%s (video input clip)" % clip.description)

# Reassign which logical device a clip uses
target = resourceManager.load("objects/logicalvideoindevice/cam2.apx", LogicalVideoInDevice)
clip = resourceManager.allResources(VideoClip)[0]
clip.Video_Input = target
```

## Gotchas
- **Subsystem access**: Use `subsystems.getSystem(VideoInSystem)`, not `subsystems.get()`.
- `VideoInSystem` and `IPVideoInSystem` are **subsystems** — access via `subsystems.getSystem(Type)`, not `resourceManager`.
- `VideoInDeviceMap.getLogicalDevices()` is a **static method** — call on the class, not an instance.
- `cropRectangle` is in **UV space (0–1)**, not pixels; `cropOffset`/`cropSize` are in pixels.
- 4K quad-link is only available on **Pro/Gx machines** (not Gx 1), requires **r14.3+**.
- ST 2110 IP video is **prerelease** and requires the `enableIPVideo` option switch set to `1`, plus a Mellanox NIC — **EX range machines are not supported**.
- ST 2110 framerate denominator must be `1` or `1001`; interlaced/pSF sources are **not supported**.
- Default input latency is **one frame** (hardware-enforced for smooth playback). Sync to PTP for minimum latency.
- HDMI 2.0 capture (EX 2C / EX 3+) requires **r32.2.4+** and a specific OS image. EX 2C supports 2 concurrent 4K inputs; EX 3+ supports 3. Limits are **enforced at runtime**.
- `VideoIn.hardwareIds` may return multiple sub-IDs for grouped (quad-link) inputs.
- De-interlacing is not recommended by Disguise — prefer 720p progressive sources.

## Userguide
- [Setup Video Input](https://help.disguise.one/designer/devices/video-input/setup-video-input) | [4K Quad Link](https://help.disguise.one/designer/devices/video-input/4k-quad-link-capture) | [De-interlacing](https://help.disguise.one/designer/devices/video-input/video-deinterlacing-methods)
- [HDMI Capture](https://help.disguise.one/designer/devices/video-input/hdmi-video-capture) | [IP Video (ST 2110)](https://help.disguise.one/designer/devices/video-input/ip-video-capture) | [Python Plugin Guide](https://developer.disguise.one/plugins/guides/video-input)
