# Devices & Control

## Key Classes
- `Device` (`Resource`) -- Base for all devices. Props: `receiving`, `started` (ro). Methods: `start()`, `stop()`.
- `ControlDevice` (`Device`) -- Text-protocol device (Telnet/UDP base). Props: `failoverCommand`, `recoveryCommand`, `verboseSend`. Methods: `sendFailover(source)`, `sendRecovery(source)`.
- `DmxDevice` (`Device`) -- DMX I/O. Props: `driver` (int, protocol enum), `IP_address`, `start_universe`, `universes`, `directionality`, `machine`, `speed`. Methods: `driverType()`, `driverStatus()`, `lastSent()`, `lastValid()`.
- `DmxCommand` (`Resource`) -- Single DMX value descriptor. Props: `channel` (1-based), `value`, `min_value`, `max_value`, `encoding` (0=8-bit, 1=16-bit BE, 2=16-bit LE, 3=24-bit BE, 4=24-bit LE), `time` (hold duration s).
- `DmxControlModule` (`Module`) -- Timeline DMX control layer (8 command slots). Props: `dmx_command_1..8` (`DmxCommand`), `value_1..8` (float).
- `DmxDriver` (`FixtureDriver`) -- LED fixture colour personality. Props: `mode` (int: 0=RGB, 4=CMY, 5=Mono weighted, 7=Alpha, 8=RrGgBb...), `amber_level`, `white_level`, `horizontal`, `vertical`, `rotation`.
- `OscDevice` (`Device`) -- OSC send/receive. Props: `sendTargets` (List[`OscSendTarget`]: `label`, `address`, `port`, `enabled`), `receivePort`, `ipFromFilter`, `supportsSendingMessageBundles`, `verboseSend`. Methods: `addSendTarget(label, address, port, enabled)`, `removeSendTarget(index)`, `clearSendTargets()`, `send(OscMessage)`. A message goes to every enabled target.
- `MidiSystem` (`Subsystem`) -- MIDI subsystem. Props: `midiIns: List[MidiIn]`, `midiOuts: List[MidiOut]`.
- `MidiIn` -- MIDI input port. Props: `deviceName`, `name`. Methods: `findChangedControllerAddressSince(t)`, `findChangedNoteOnAddressSince(t)`.
- `MidiNoteModule` (`Module`) -- Timeline MIDI note layer. Props: `channel`, `device` (int index into midiOuts), `note` (0-127), `velocity`, `duration`.
- `ScreenPositionReceiver` (`Device`) -- Motion tracking device. Props: `axes: List[ScreenPositionAxis]`, `drivers`, `expressions`, `engaged`, `prediction`, `predictionEnabled`, `smoothingFactor`, `positionSamples`, `timeSamples`. Methods: `createAxes()`, `clearAxes()`, `canCreateAxes()`.
- `ScreenPositionAxis` (`Resource`) -- Single tracking axis binding. Props: `id` (match driver ID string), `object` (Object to drive), `property_`, `status` (0=Disengaged, 1=Engaged), `min_input/max_input`, `min_output/max_output`, `offset`, `prediction`, `smoothingFactor`, `movementThreshold`, `wrapInput`, `graph`.
- `LogicalDevice` (`Resource`) -- Logical device grouping; no device-specific properties beyond Resource base.
- `ControlString` (`Resource`) -- Text command template. Props: `string` (command text).

## Access
```python
# Devices are Resources
dmx  = resourceManager.load("objects/dmxdevice/my dmx.apx", DmxDevice)
osc  = resourceManager.loadOrCreate("objects/oscdevice/console osc.apx", OscDevice)
all_dmx = resourceManager.allResources(DmxDevice)

# MIDI via subsystem (not a Resource)
midi = subsystems.getSystem(MidiSystem)
ins  = midi.midiIns                  # List[MidiIn]
outs = midi.midiOuts                 # List[MidiOut]
```

## DMX
```python
dmx = resourceManager.loadOrCreate("objects/dmxdevice/artnet1.apx", DmxDevice)
dmx.driver         = 0              # 0=Art-Net (others: sACN, Enttec, Soundlight, EZDMX, KiNET)
dmx.IP_address     = "192.168.1.100"
dmx.start_universe = 1
dmx.universes      = 4
dmx.directionality = 1              # 0=Input+Output, 1=Output, 2=Input
dmx.speed          = 1              # send frequency multiplier (1=per frame)

# DmxCommand -- describes a channel/value pair used by DmxControlModule
cmd = resourceManager.loadOrCreate("objects/dmxcommand/ch1_full.apx", DmxCommand)
cmd.channel   = 1                   # 1-based
cmd.value     = 255
cmd.min_value = 0
cmd.max_value = 255
cmd.encoding  = 0                   # 0=8-bit

# DmxDriver -- LED fixture personality (for fixture-addressed output)
driver = resourceManager.load("objects/dmxdriver/my fixture.apx", DmxDriver)
driver.mode        = 0              # 0=RGB, 4=CMY, 5=Mono(weighted), 7=Alpha
driver.amber_level = 0.5

# Status / lifecycle
dtype = dmx.driverType()            # returns driver name (e.g. "artnet")
dstat = dmx.driverStatus()          # e.g. "Inactive"
dmx.start()
dmx.stop()
```

## OSC
```python
osc = resourceManager.loadOrCreate("objects/oscdevice/console.apx", OscDevice)
osc.clearSendTargets()
osc.addSendTarget("console", "192.168.1.50", 8000, True)
osc.receivePort   = 9000
osc.ipFromFilter  = ""              # blank = accept any source IP
osc.supportsSendingMessageBundles = True

# Send a message programmatically
msg = OscMessage()
msg.addString("/d3/transport/play")  # path as first argument
osc.send(msg)

osc.start()
print(osc.receiving)                # True when actively receiving
```

## MIDI
```python
midi = subsystems.getSystem(MidiSystem)
for port in midi.midiIns:
    print("%s: %s" % (port.name, port.deviceName))

# Detect recent MIDI activity (returns changed address since time t, or -1)
t    = guisystem.player.tCurrent
addr = midi.midiIns[0].findChangedNoteOnAddressSince(t)
ctrl = midi.midiIns[0].findChangedControllerAddressSince(t)

# MidiNoteModule properties (accessed via layer module — see layers-modules reference)
# mod.channel = 1..16, mod.note = 0..127, mod.velocity = 0..127
# mod.device = index into midi.midiOuts list, mod.duration = float beats
```

## Motion Tracking (ScreenPositionReceiver)
```python
spr = resourceManager.loadOrCreate("objects/screenpositionreceiver/camera1.apx", ScreenPositionReceiver)
spr.engaged           = True
spr.smoothingFactor   = 20.0        # % smoothing (higher = more lag)
spr.positionSamples   = 5           # filter samples (0 = off)
spr.prediction        = 0.05        # seconds of prediction lookahead
spr.predictionEnabled = 1

# Auto-create axes from active driver
if spr.canCreateAxes():
    spr.createAxes()

# Configure individual axes
for axis in spr.axes:
    axis.id         = "camera1_x"   # must match ID published by tracking driver
    axis.object     = resourceManager.load("objects/camera/cam1.apx", Camera)
    axis.property_  = "position.x"
    axis.min_input  = -5000.0       # driver world units
    axis.max_input  =  5000.0
    axis.min_output = -5.0          # d3 stage units
    axis.max_output =  5.0
    axis.status     = 1             # 1 = Engaged

# Supported driver types (ScreenPositionDriver subclasses in spr.drivers):
# NatNet, nCam, Stype, MoSys F4, Kinesys, Movecat, PRG, D3SSI, HMC,
# Navigator, OSC, PosiStageNet, RTTrPM, Simotion, STS, CPS, Unican, VisualAct
```

## ControlDevice (Telnet / UDP)
```python
dev = resourceManager.load("objects/telnetdevice/projector.apx", TelnetDevice)

# Create ControlString resources for commands
failover = resourceManager.loadOrCreate("objects/controlstring/standby.apx", ControlString)
failover.string = "STANDBY\r\n"

recovery = resourceManager.loadOrCreate("objects/controlstring/wake.apx", ControlString)
recovery.string = "WAKE\r\n"

# Assign to device
dev.failoverCommand = failover
dev.recoveryCommand = recovery
dev.verboseSend     = True

# Trigger commands
dev.sendFailover("manual")          # trigger failover command immediately
dev.sendRecovery("manual")          # trigger recovery command immediately
```

## Matrix Switches
```python
# Matrix types: LightwareMatrix, BarcoMatrixPro, BlackMagicVideoHub, etc.
# Switched via MatrixControl layer in timeline (UI-driven).
# Access by resource path for configuration:
mx = resourceManager.load("objects/lightwarematrix/main.apx", LightwareMatrix)
# Matrix switch types have no Python-reflected properties; configure in UI.
```

## Gotchas
- `Device.description` is read-only (derived from resource path) -- use `resource.rename(new_path)` to rename.
- `DmxCommand.channel` is **1-based**; channel 0 is invalid.
- `MidiNoteModule.device` is an **integer index** into `MidiSystem.midiOuts`, not a device name.
- `ScreenPositionAxis.id` must **exactly** match the ID string the tracking driver publishes -- mismatch silently leaves the axis Disengaged.
- `ScreenPositionAxis.status` is an `int` (0/1), not a bool.
- `MidiSystem` is accessed via `subsystems.getSystem(MidiSystem)`, not `resourceManager`.
- `OscDevice.send()` takes an `OscMessage` object. Use `msg.addString()` etc. to populate the message (no `setAddress()` method exists).
- `ControlString` is a Resource created via `loadOrCreate()`, then set `.string` property. Not a constructor.

## Userguide
- [Devices index](https://help.disguise.one/designer/devices/devices-index) | [Creating devices](https://help.disguise.one/designer/devices/creating-devices) | [DMX](https://help.disguise.one/designer/devices/dmx-device) | [MIDI](https://help.disguise.one/designer/devices/midi-device) | [OSC](https://help.disguise.one/designer/devices/osc-device) | [Telnet](https://help.disguise.one/designer/devices/telnet-device) | [UDP](https://help.disguise.one/designer/devices/udp-device)
- [Motion control](https://help.disguise.one/designer/devices/automation/motion-control-systems) | [Axes](https://help.disguise.one/designer/devices/automation/axes) | [Tracking source](https://help.disguise.one/designer/devices/automation/tracking-source) | [Automation drivers](https://help.disguise.one/designer/devices/automation/automation-driver-index/automation-driver-index)
- [Matrix switches](https://help.disguise.one/designer/devices/matrices/matrix-switches-overview) | [Python plugin guide: devices](https://developer.disguise.one/plugins/guides/devices)
