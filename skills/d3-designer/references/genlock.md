# Genlock

Genlock locks display outputs to an external sync source (house sync or PTP). Configuration is per-machine via `Machine` methods and per-VFC slot via `DisplayOutputVFC`.

## Key Classes
- `Machine` (`Resource`) — Per-machine genlock configuration and status.
- `DisplayAdapterList` — Live snapshot of GPU adapters. Access via `Machine.findDisplayAdapterList()`.
- `DisplayOutputVFC` — One VFC hardware slot. Properties: `slot`, `model`, `generation`, `splitMode`.
- `PTPInfo` — PTP configuration. Properties: `ptpDomainNbr`, `ptpPortNbr`, `ptpClkId`, `profile`, `state`.
- `PTPLockState` — PTP lock status. Properties: `state` (int), `distance` (int).

## Access
```python
machines = resourceManager.allResources(Machine)
m = machines[0]                             # local machine typically first

adapters = m.findDisplayAdapterList()       # DisplayAdapterList (live snapshot)
vfcs = adapters.allVfcs()                   # List[DisplayOutputVFC]
```

## House Sync
```python
# Check incoming house sync signal
has_sync = m.hasIncomingHouseSyncSignal()   # bool
freq     = m.incomingHouseSyncSignal()      # float (Hz) -- 0 if no signal

# Check if all required outputs are genlocked
all_locked = m.allRequiredOutputsGenlocked()  # bool

# Assert/clear house sync
m.assertHouseSync()
m.clearHouseSync()
```

## VFC Sync Status
```python
# Per-slot sync status
for vfc in vfcs:
    slot      = vfc.slot
    sync_mode = m.vfcSysSyncMode(slot)      # int: sync source mode
    sync_rate = m.vfcSysSyncFrate(slot)     # float: incoming sync frame rate

# Slot mismatches
mismatches = m.vfcSysSyncModeMismatch()     # List[int] — slot indices
if mismatches:
    for slot in mismatches:
        print("Sync mode mismatch on slot %d" % slot)

# Alert conditions
for vfc in vfcs:
    slot = vfc.slot
    if m.vfcSysAlertStatusSynError(slot):
        print("Sync error on slot %d" % slot)
    if m.vfcSysAlertStatusPTPStepped(slot):
        print("PTP stepped on slot %d" % slot)
    if m.vfcSysAlertStatusBoardTempExceeded(slot):
        print("Temp exceeded on slot %d" % slot)
```

## PTP
```python
# PTP domain mismatch across VFC slots
ptp_mismatch = m.vfcSysPtpDomainMismatch() # int: 0 = no mismatch

# Which slot syncs PTP (optional<int>)
slot_ptp = m.getSlotToSyncPTP()
if slot_ptp.has_value():
    print("PTP sync via slot %d" % slot_ptp.value())
```

## Apply Configuration
```python
# After changing display/genlock settings, apply to hardware
m.applyPortConfigs(True)    # blocking=True waits for completion

if m.needsDisplaySettingsApplied():
    m.applyDisplaySettings()
```

## Diagnostic Snapshot
```python
for m in resourceManager.allResources(Machine):
    print("%s: genlocked=%s house_sync=%s freq=%.2fHz" % (
        m.name,
        m.allRequiredOutputsGenlocked(),
        m.hasIncomingHouseSyncSignal(),
        m.incomingHouseSyncSignal()
    ))
    for slot in m.vfcSysSyncModeMismatch():
        print("  WARNING: sync mode mismatch on slot %d" % slot)
```

## Gotchas
- `incomingHouseSyncSignal()` returns `0.0` (not an error) when no signal; check `hasIncomingHouseSyncSignal()` first.
- `vfcSysSyncModeMismatch()` returns slot **indices** as integers — cross-reference with `vfc.slot`.
- `getSlotToSyncPTP()` returns `optional<int>` — use `.has_value()` to check, `.value()` to extract the slot number.
- `applyPortConfigs(False)` returns immediately; use `True` if subsequent code depends on the new config.
- `assertHouseSync()` / `clearHouseSync()` control output lock state, not sync source or frame rate config.

## Reference
- [Genlock Configuration](https://help.disguise.one/designer/configuration/genlock-configuration)
