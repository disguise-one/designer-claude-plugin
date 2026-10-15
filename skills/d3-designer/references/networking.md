# Networking

## Key Classes
- `D3NetManager` (`Resource`) -- Session manager: director/actor/understudy roles, failover, machine list. Global: `d3NetManager`.
- `Machine` (`Resource`) -- A networked server in the session. Props: `hostname`, `IP_address`, `role`, `active`, `failed`, `networkConnected`, `networkStatus`, `machineType`, `feed`, `audio`, `targets`.
- `IPAddress` -- IP address value. Props: `addr4` (int, read-only).

## Access
```python
# d3NetManager is a pre-imported global (like resourceManager)
mgr = d3NetManager

# Get all machines in the project (includes local machine)
all_machines = resourceManager.allResources(Machine)

# Get the local machine running this d3 instance
local_machine = d3NetManager.localMachine

# Load a specific machine by path
m = resourceManager.load("objects/machine/r24-00.apx", Machine)

# Find a machine by hostname
m = d3NetManager.findMachineByHostname("r24-00")
```

## Session Roles & Status
```python
# Session mode booleans (read-only)
d3NetManager.soloMode              # True when running without a session
d3NetManager.directorMode          # True when this machine is director
d3NetManager.actorMode             # True when this machine is an actor
d3NetManager.understudy            # True when this machine is an understudy
d3NetManager.dedicatedDirectorMode
d3NetManager.mobileEditorMode

# Session members
director     = d3NetManager.director        # Machine [rw]
actors       = d3NetManager.actors          # List[Machine] [rw]
understudies = d3NetManager.understudies    # List[Machine] [rw]
session_machines = d3NetManager.machines    # List[Machine] [ro] — machines in current session
```

## Change Director
```python
# Modify the director machine
d3NetManager.director = resourceManager.load("objects/machine/r24-00.apx", Machine)
```

## Failover Configuration
```python
d3NetManager.timeout       # float [rw] — 0 disables automatic failover
d3NetManager.normal_preset # str [rw] — preset name to restore on failover
```

## Machine Configuration
```python
m = d3NetManager.localMachine

# Identity & connection
m.hostname          # str [rw]
m.IP_address        # str [ro]
m.name              # str [ro]
m.active            # bool [ro] — currently in session
m.failed            # bool [ro]
m.networkConnected  # bool [ro]
m.networkStatus     # int [ro]
m.machineType       # int [rw] — 0=Designer, 8=gx1, 10=solo, 11=vx4, etc.

# Audio/feed assignment
m.feed              # FeedScene [rw]
m.alternate_feed    # FeedScene [rw]
m.audio             # int [rw] — 0=Off, 1=Timeline Only, 2=Videofiles Only, 3=On

# Understudy targets
m.targets           # List[Machine] [rw] — machines this understudy covers

# Network port
m.httpPort          # int [rw]

# Machine role (read-only enum value → string)
role_str = Machine.machineRoleToString(m.role)
```

## Commands & Dispatch
```python
# Send a RemoteCommand to all session machines or one specific machine
d3NetManager.dispatchCommandAll(cmd, sessionOnly=True)
d3NetManager.dispatchCommandDirect("r24-00", cmd, sessionOnly=True)  # returns bool

# Check understudy availability and configuration
d3NetManager.understudyAvailableFor(machine)          # bool
d3NetManager.getDirectorUnderstudy()                  # Machine
d3NetManager.getUnderstudyConfigStatus(understudy)    # int
d3NetManager.isUnderstudy(machine)                    # bool

# Validate before adding a machine to session
ok = d3NetManager.machineCanBeAddedToSessionAs(machine, role_int)

# Machine status by node ID
status = d3NetManager.machineStatus(node_id)  # MachineStatus
node_id = m.nodeId                            # optional[int] [ro]
```

## VFC / IP Networking (per-machine)
```python
# IP-VFC ST 2110 (NMOS)
ip = m.vfcIPNetConfigAddress(iSlot, eth, nvm)  # -> IPAddress; addr4 is int
m.vfcPTPLockState(iSlot)      # int — PTP lock status
m.vfcPTPProfile(iSlot)        # int
m.vfcStatus(iSlot)            # int
m.vfcFirmwareVersion(iSlot)   # VFCFpgaVersion
m.streamEnabled(iSlot, iPort) # bool

# Genlock / house sync
m.allRequiredOutputsGenlocked()   # bool
m.assertHouseSync()
m.hasIncomingHouseSyncSignal()    # bool
m.incomingHouseSyncSignal()       # float
```

## Gotchas
- `d3NetManager` is a pre-imported global — do NOT use `resourceManager.load()` to get it.
- `d3NetManager.machines` is the current session machine list (empty in solo mode); use `resourceManager.allResources(Machine)` to get all project machines.
- `Machine.name` exists (unlike most resources where only `description` works), but `description` is also available.
- `Machine.IP_address` is read-only; set network config via VFC methods or d3Manager UI.
- `NetworkInterface` class does not exist in d3.pyi — network adapter selection is done via d3Manager UI before starting a project, not via the Python API.
- Failover `timeout=0` disables automatic failover; `normal_preset` must match an existing preset name exactly.
- Editors connect to the Director over the network; the Director must be running and `editorsAllowed` must be enabled before an Editor can join a session.

## Userguide
- [d3Net Overview](https://help.disguise.one/designer/networking/d3net-overview) · [d3Net Setup](https://help.disguise.one/designer/networking/setup-d3net) · [Setup Editors](https://help.disguise.one/designer/networking/setup-editors) · [Network Interface Selection](https://help.disguise.one/designer/networking/network-interface-selection)
- [Python d3Net Guide](https://developer.disguise.one/plugins/guides/d3net) · [NMOS](https://help.disguise.one/designer/networking/nmos) · [Network Status Widget](https://help.disguise.one/designer/networking/network-status-widget)
- [Security Overview](https://help.disguise.one/designer/networking/security-overview) · [Network Ports](https://help.disguise.one/designer/networking/network-ports-and-activity) · [Teaming](https://help.disguise.one/designer/networking/teaming) · [VLAN](https://help.disguise.one/designer/networking/virtual-local-area-network)
