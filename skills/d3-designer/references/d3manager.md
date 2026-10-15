# d3Manager, Sessions & Project Paths

## Overview

d3Manager is a standalone launcher/UI application for creating, opening, and managing Designer
projects, networked machines, checkpoints, snapshots, and diagnostics. Most d3Manager operations
(create project, open project, join session, create checkpoint/snapshot) are **UI-driven** -- there
is no Python API to drive the launcher itself. The Python plugin runs *inside* an already-running
Designer session, so the relevant Python surface is: querying session/machine state, reading
project paths, and understanding the running environment.

## Key Classes

- `D3NetManager` (`Resource`) -- Network topology resource. Props: `machines`, `director`,
  `actors`, `understudies`, `localMachine`, `thisMachine`, `soloMode`, `directorMode`,
  `actorMode`, `understudy`, `hasValidDirector`, `timeout`. Methods: `findMachineByHostname()`,
  `machineStatus()`, `dispatchCommandAll()`, `dispatchCommandDirect()`, `isUnderstudy()`.
- `D3NetManagerSystem` (`Subsystem`) -- Subsystem accessor. Props: `d3NetManager`.
- `Machine` (`Resource`) -- A machine in the network. Props: `name`, `hostname`, `IP_address`,
  `machineType`, `role`, `active`, `failed`, `networkConnected`, `networkStatus`, `nodeId`,
  `nodeName`, `d3ProjectsFolder`, `hasDedicatedGui`, `isGuiVisible`, `runningAs`.
  Methods: `status()`. Static: `localApiEndpoint()`.
- `MachineStatus` -- Snapshot of machine state. Props: `states` (List[State]), `guiVisible`,
  `tUpdated`.
- `SessionSystem` (`Subsystem`) -- Props: `sessionName`. Methods: `getIsNodeInSession(nodeId)`.
- `SessionDiscovery` / `SessionDiscoverySystem` (`Subsystem`) -- Methods:
  `getSessionAPIEndpoint(sessionName)`.
- `PathsManager` -- Global `paths` object. Key paths: `consolePath`, `currentConsoleArchivePath`,
  `archivedConsolesDirectory`, `appProjectDirectory`, `isRunningFromCheckpoint`,
  `checkpointName`, `telemetryLogsPath`, `schemaPath`, `d3Exe`, `pythonDir`, `isDeveloperEnvironment`.
  Static: `projectExtension()`, `projectExtensionSnapshot()`, `isFullProject(path)`,
  `isStarterProject(path)`.

## Access

```python
# D3NetManager and session info (globals: d3NetManager, subsystems, paths)
nm      = d3NetManager                             # D3NetManager resource directly
nm_sys  = subsystems.getSystem(D3NetManagerSystem) # or via subsystem
nm      = nm_sys.d3NetManager

sess    = subsystems.getSystem(SessionSystem)
print(sess.sessionName)                            # session name or "" if solo

disc    = subsystems.getSystem(SessionDiscoverySystem)
ep      = disc.getSessionAPIEndpoint("MySession")  # REST API endpoint URL

# Path info
print(paths.consolePath)                           # path to current console log
print(paths.isRunningFromCheckpoint)               # bool
print(paths.checkpointName)                        # checkpoint label
print(paths.appProjectDirectory)                   # projects root folder
print(paths.isDeveloperEnvironment)                # bool

# Static helpers
ext      = paths.projectExtension()                # ".d3"
snap_ext = paths.projectExtensionSnapshot()        # ".d3ss"
```

## Network / Machine Inspection

```python
nm = d3NetManager

# Local machine
local = nm.localMachine
print("hostname: %s" % local.hostname)
print("IP: %s" % local.IP_address)
print("name: %s" % local.name)
print("solo: %s" % nm.soloMode)

# All machines in the project
for m in nm.machines:
    st = nm.machineStatus(m.nodeId)                # MachineStatus
    print("%s active=%s failed=%s" % (m.hostname, m.active, m.failed))

# Find a specific machine
m = nm.findMachineByHostname("render-01")

# Director / actor topology
print(nm.directorMode)                             # True if local is director
print(nm.actorMode)                                # True if local is actor
director = nm.director                             # Machine
for actor in nm.actors:
    print(actor.hostname)
for u in nm.understudies:
    print(u.hostname)

# Check session membership (nodeId is optional<uint>; check has_value() first)
sess = subsystems.getSystem(SessionSystem)
if local.nodeId.has_value():
    in_sess = sess.getIsNodeInSession(local.nodeId.value())
```

## Session State

```python
sess = subsystems.getSystem(SessionSystem)
name = sess.sessionName    # empty string when running solo (no session)

# Machine role flags (on D3NetManager)
nm = d3NetManager
nm.soloMode                 # True: no session, running standalone
nm.directorMode             # True: this machine is the director
nm.actorMode                # True: this machine is an actor
nm.understudy               # True: this machine is an understudy
nm.dedicatedDirectorMode    # True: dedicated (GUI-only) director
nm.mobileEditorMode         # True: mobile editor connected
nm.nonDedicatedDirectorMode # True: director is also playing back
```

## Project Paths

```python
# Common path queries via the global `paths` (PathsManager)
paths.appProjectDirectory           # root projects directory
paths.consolePath                   # current session console log file path
paths.currentConsoleArchivePath     # archived console for this session
paths.archivedConsolesDirectory     # folder containing all archived consoles
paths.telemetryLogsPath             # telemetry output folder
paths.schemaPath                    # schema.json describing all reflected objects
paths.d3Exe                         # path to d3.exe
paths.pythonDir                     # Python installation folder
paths.rsyncExe                      # rsync binary path

# Check runtime context
paths.isRunningFromCheckpoint       # bool: launched from a checkpoint
paths.isDeveloperEnvironment        # bool: developer build

# Path classification
paths.isFullProject("<projects folder>/myshow/myshow.d3")   # bool
paths.isStarterProject("<projects folder>/starter.d3")      # bool
paths.projectExtension()            # ".d3"
paths.projectExtensionSnapshot()    # ".d3ss"
```

## What d3Manager Does (UI Only -- No Python API)

The following are d3Manager UI operations with no Python equivalent:

- **Create / open / close project** -- file browser in the Projects tab
- **Start / relaunch project** -- double-click `.d3` or click the Disguise icon to relaunch last
- **Add / remove project folders** -- managed in the Projects tab
- **Templates** -- designate any project as a template for new projects
- **Join session** -- Network tab; multi-user editing over the network
- **Assistance mode** -- join a session with remote-support access enabled
- **Advanced machine settings** -- application mode, option switches; set per machine
- **Create checkpoint** -- named copy of the project file; also accessible via Designer File menu
- **Create snapshot** -- save/restore full project state; managed in the Snapshots panel
- **Upgrade / downgrade project** -- version migration UI
- **Generate diagnostics** -- System or Project Diagnostic zip for support
- **Generate console files** -- open latest console or console folder
- **Remote profiling** -- Network tab; generates a Chrome-trace JSON for perf analysis
- **Remote install** -- push Designer installation to networked machines

## Gotchas

- There is no `manager` global. d3Manager is a separate launcher process; Python runs inside
  Designer, not inside d3Manager.
- `d3NetManager` is the global for the `D3NetManager` resource directly (not a subsystem).
  `D3NetManagerSystem` subsystem is an alternative path via `subsystems.getSystem(D3NetManagerSystem).d3NetManager`.
- `SessionSystem.sessionName` returns `""` (empty string) when solo -- use `nm.soloMode` for
  a clear boolean test.
- `Machine.name` exists on `Machine` (unlike most `Resource` subclasses where only `description`
  is available).
- `Machine.nodeId` is `optional<uint>` -- check `.has_value()` before accessing with `.value()`.
- `PathsManager.checkpointName` is typed `int` in the stub; use `isRunningFromCheckpoint` as
  the reliable bool guard before reading it.
- Checkpoints and snapshots cannot be created from Python at runtime; they require the d3Manager
  UI or the Designer File menu.
- Remote profiling output is a Chrome-trace JSON; open in `chrome://tracing` or Perfetto UI.
- Subsystem access uses `subsystems.getSystem(SystemClass)` (not `find()`).

## Userguide

- [d3Manager Overview](https://help.disguise.one/designer/d3manager/d3manager-overview)
- [Creating Projects](https://help.disguise.one/designer/d3manager/creating-projects) | [Opening Projects](https://help.disguise.one/designer/d3manager/opening-projects) | [Starting Existing Projects](https://help.disguise.one/designer/d3manager/starting-existing-projects)
- [Managing Project Folders](https://help.disguise.one/designer/d3manager/managing-project-folders) | [Working with Templates](https://help.disguise.one/designer/d3manager/working-with-templates)
- [Networked Machines](https://help.disguise.one/designer/d3manager/manager-networked-machines) | [Joining a Session](https://help.disguise.one/designer/d3manager/joining-a-session) | [Assistance Mode](https://help.disguise.one/designer/d3manager/enabling-assistance-mode)
- [Advanced Machine Settings](https://help.disguise.one/designer/d3manager/advanced-machine-settings)
- [Creating Checkpoints](https://help.disguise.one/designer/d3manager/creating-checkpoints) | [Creating Snapshots](https://help.disguise.one/designer/d3manager/creating-snapshots)
- [Upgrading/Downgrading Projects](https://help.disguise.one/designer/d3manager/upgrading-downgrading-projects)
- [Generating Console Files](https://help.disguise.one/designer/d3manager/generating-console-files) | [Generating Diagnostics](https://help.disguise.one/designer/d3manager/generating-diagnostics) | [Remote Profiling](https://help.disguise.one/designer/d3manager/remote-profiling)
