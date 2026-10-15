# Timeline, Tracks & Transports

A **Track** is a timeline containing layers, cues, and sections. A **Transport** (`TransportManager`) is a playback controller bound to one track at a time — it handles play, stop, and position commands.

Track switching (changing which track a transport drives) requires the REST API, not `TransportCommand`. Use the MCP tool `mcp__d3service__transport_go_to_track` (or `transport_control_go_to_track` for v1 / UID-addressed transports).

## Key Classes
- `Track` (`SuperTrack` > `Resource`) -- Timeline track with layers, cues, sections. Props: `cues`, `layers`, `bpm`, `lengthInBeats`, `lengthInSec`.
- `Layer` (`SuperLayer` > `Resource`) -- Content block on a track. Props: `name`, `tStart`, `tEnd`, `tLength`, `fields`, `moduleType`, `render`.
- `Cue` (`Resource`) -- Marker in `track.cues` TimeSequence. Props: `section`, `note`, `sectionTransition`. Methods: `isSection()`, `getTags()`, `getNote()`, `setNote()`, `hasNote()`.
- `Tag` -- Cue tag value. Props: `text` (str), `type` (int). Constants: `Tag.CUE=1`, `Tag.TC=0`, `Tag.MIDI=2`. Cannot be constructed in Python; read via `cue.getTags()` or `cue.getTag(tagType)`.
- `Note` (`Resource`) -- Annotation resource. Props: `text`, `seen`, `modified`. Methods: `markSeen()`.
- `PlayMode` -- Playhead state. `state` (int): 0=Play, 1=PlaySection, 2=LoopSection, 3=Stop, 4=HoldSection, 5=HoldEnd.
- `TransportManager` (`SuperTransportManager` > `Resource`) -- Playback control hub. Props: `track`, `player`, `setList`, `brightness`, `volume`, `engaged`.
- `TransportCommand` -- Static factory for playback commands. Dispatched via `tm.addCommand()`.
- `TrackPlayer` (`Resource`) -- Playback state. Props: `tCurrent`, `playing`, `stopped`, `holding`, `playMode`, `track`, `activeLayers`.
- `SetList` (`Resource`) -- Ordered track list. Props: `tracks`. Methods: `containsTrack()`.
- `TrackTransitionInfo` -- Crossfade settings. Props: `fadeDurationBeats`, `mode`, `loopUxFade`.
- `TimeSequence` -- Time-indexed container (e.g. `track.cues`). **Not iterable**: use `n()` + `getT(i)` / `getV(i)`.
- `FieldSequence` (`Resource`) -- Animatable layer property. Props: `name`, `disableSequencing`, `sequence`.
- `KeySequence` (`KeyContainer` > `Resource`) -- Keyframe data (runtime subclass: `FloatSequence`). Methods: `nKeys()`, `t(i)`, `key(i)`, `insert()`, `setString()`.

## Access
```python
# Current editor state (guisystem is a runtime global, not in d3.pyi)
track  = guisystem.track                       # current Track
tm     = guisystem.currentTransportManager     # current TransportManager
player = tm.player                             # TrackPlayer

# By resource path
track = resourceManager.load("objects/track/song1.apx", Track)

# Enumerate all
all_tracks   = resourceManager.allResources(Track)
all_setlists = resourceManager.allResources(SetList)
```

## Timing & Conversion
```python
beats = track.lengthInBeats           # total duration in beats
secs  = track.lengthInSec            # total duration in seconds
secs  = track.beatToTime(120.0)      # beat -> seconds
beat  = track.timeToBeat(5.0)        # seconds -> beats
bpm   = track.bpm                    # global BPM (rw)
bpm_local = track.bpmAt(120.0)       # BPM at a specific beat
```

## Playback Control
```python
pos   = player.tCurrent              # current beat position
is_on = player.playing               # bool
mode  = player.playMode.state        # int: 0=Play..5=HoldEnd

# Transport commands -- static factories, dispatched via tm.addCommand()
# source MUST be state (other sources are internal only)
tm.addCommand(TransportCommand.makePlayMode(state, tm, PlayMode(0)))   # Play
tm.addCommand(TransportCommand.makePlayMode(state, tm, PlayMode(3)))   # Stop
tm.addCommand(TransportCommand.makePlayMode(state, tm, PlayMode(2)))   # LoopSection

# Jump to position
tm.addCommand(TransportCommand.makeJumpToBeat(state, tm, 240.0))
tm.addCommand(TransportCommand.makeJumpToTime(state, tm, 10.5))       # seconds
tm.addCommand(TransportCommand.makeJumpToFrame(state, tm, 300))
tm.addCommand(TransportCommand.makeJumpToCue(state, tm, 3, 0, 0, 0))  # cue xx.yy.zz + CueMode(int)

# Nudge relative
tm.addCommand(TransportCommand.makeNudgeBeat(state, tm, 4.0))         # +4 beats
tm.addCommand(TransportCommand.makeNudgeSection(state, tm, 1))        # next section
tm.addCommand(TransportCommand.makeNudgeTrack(state, tm, 1))          # next track

# Speed
tm.addCommand(TransportCommand.makeSetSpeed(state, tm, 2.0))
```

## Sections, Cues & Notes
```python
# Sections are Cue entries where cue.isSection() is True
n = track.nSections()
beat   = track.sectionToBeat(0)              # beat of section 0
length = track.sectionLengthBeats(0)
idx    = track.beatToSection(120.0)          # section index containing beat

# Split / merge
track.splitSectionAtBeat(120.0)              # default transition
info = TrackTransitionInfo()
info.fadeDurationBeats = 4.0
track.splitSectionAtBeat(240.0, info)        # with crossfade
track.mergeSectionAtBeat(120.0)              # remove boundary

# Iterate cues (TimeSequence -- NOT iterable, use n()/getT()/getV())
cues = track.cues
for i in range(cues.n()):
    beat = cues.getT(i)
    cue  = cues.getV(i)                     # Cue object
    if cue.isSection():
        print("Section at beat %s" % beat)
    for tag in cue.getTags():               # List[Tag] -- read-only
        print("  tag type=%d text=%s" % (tag.type, tag.text))

# Read tag by type (returns Tag or None)
cue = track.cueAtBeat(0.0)
tag = cue.getTag(Tag.CUE)                   # Tag.CUE=1, Tag.TC=0, Tag.MIDI=2

# Notes on cues
cue.setNote("Intro starts here")
text = cue.getNote()                         # str
cue.hasNote()                                # bool

# Notes at beat positions (convenience methods on Track)
track.setNoteAtBeat(0.0, "Show start")
text = track.noteAtBeat(0.0)
track.removeNoteAtBeat(0.0)

# Navigate to adjacent markers
cue_beats = track.cueBeats()                 # List[float]
track.findBeatOfNextTag(50.0)
track.findBeatOfLastSection(50.0)
track.findBeatOfNextNote(50.0)
```

## Layers
```python
layers = track.layers                        # List[SuperLayer]
layer  = track.findLayerByName("MyVideo")    # returns Layer or None

# Add / remove (first arg is a module type)
layer = track.addNewLayer(VariableVideoModule, 0.0, 120.0, "Intro Video")  # (type, tStart, length, name)
# Other types: ColourModule, BitmapModule, BlurModule, AudioModule, ComposeModule, etc.
track.removeLayer(layer)

# Properties
layer.name = "Renamed"
layer.tStart                                 # start beat (rw)
layer.tLength                                # duration (rw)
layer.render = False                         # disable rendering
layer.setExtents(0.0, 240.0)                # move + resize

# Reorder, split, group
track.moveLayerToIndex(layer, 0)
track.splitLayersAtBeat([layer], 60.0)
track.groupLayers([layer1, layer2], "MyGroup", False)
# findLayerByName does not find GroupLayers; iterate track.layers instead
group = [l for l in track.layers if isinstance(l, GroupLayer)][0]
track.ungroupLayer(group)
track.makeArrow(src_layer, dst_layer)
```

## Layer Field Sequences (Keyframes)
```python
fseq = layer.findSequence("brightness")
fseq.disableSequencing = False               # enable keyframing
val = fseq.eval(60.0, 0)                    # evaluate at beat -> float

ks = fseq.sequence                           # KeySequence (runtime: FloatSequence)
for i in range(ks.nKeys()):
    print("beat=%s" % ks.t(i))
ks.insert(0, 30.0, 0)                       # (index, beat, key_type)
ks.setString(0, "1.0")                      # set value as string
ks.stripToFirstKey()                         # remove all but first
```

## Crossfade / Transitions
```python
info = track.defaultTransitionInfo           # TrackTransitionInfo
info.fadeDurationBeats                       # crossfade length in beats
info.mode                                    # transition mode (int)

# Per-section transition
info = track.transitionInfoAtSection(1)
info = track.transitionInfoAtBeat(120.0)

# Set crossfade on a section cue
cue = track.cueAtBeat(120.0)
cue.sectionTransition.fadeDurationBeats = 8.0
```

## Set Lists
```python
sl = tm.setList                              # current set list (rw)
for t in sl.tracks:
    print(t.description)
sl.containsTrack(track)                     # bool
```

## Transport Manager Settings
```python
tm.engaged = True                            # accept external commands
tm.on_clock_lost                             # action when TC lost (int)
tm.on_clock_regained                         # action when TC regained (int)
tm.play_mode                                 # chase play mode (int, rw)
tm.timecode_can_change_track                 # int (rw)
track.tc_adjust                              # TC offset in seconds (on Track, not TM)
tm.statusString                              # current TC status string
```

## Gotchas
- `TimeSequence` is **not iterable** -- use `for i in range(seq.n()): seq.getT(i), seq.getV(i)`.
- `PlayMode` / `CueMode` have no named Python constants -- construct as `PlayMode(int_value)`. `CueMode` is not in d3.pyi; pass int (typically 0).
- `makeJumpToTime` takes **seconds**, `makeJumpToBeat` takes **beats** -- the timeline is beat-native.
- Keyframe `t` values are **track-global beats**, not layer-local offsets.
- `track.layers` returns `List[SuperLayer]` -- use `findLayerByName()` to get a `Layer` with `fields`/`findSequence`.
- `Section` is not a standalone class -- sections are `Cue` entries where `cue.isSection()` returns True.
- **"Section" and "cue" are often interchangeable** in user language -- both are markers within a track. SetList is completely separate (ordered list of tracks).
- Layer z-order: index 0 = top (renders on top). `addNewLayer` inserts at 0. Use `moveLayerToIndex(layer, track.nLayers()-1)` for background layers.
- `track.description` is the human-readable name; there is no `track.name`.
- `tc_adjust` lives on `Track`, not on `TransportManager`.
- `Tag` values cannot be constructed in Python -- read them via `cue.getTags()` or `cue.getTag(tagType)`.
- `addNewLayer(moduleType, tStart, length, name)` — the third argument is **duration** (not end beat). Use `VariableVideoModule` for video (not `VideoModule`, which is deprecated).
- `findLayerByName` does not find `GroupLayer` instances -- iterate `track.layers` and check `isinstance(l, GroupLayer)`.
- **TransportCommand source must be `state`** -- other sources (Track, etc.) cause "unrecognised source" errors.
- **`TransportCommand.trackAndBeat` does not switch tracks** -- setting `cmd.trackAndBeat.track` only affects beat position, not the active track. To switch tracks, use the MCP tool `mcp__d3service__transport_go_to_track`.
- `track.moveLayersUp([layer])` / `track.moveLayersDown([layer])` — nudge layer z-order by one position.
- `track.findLayerIndex(layer)` — returns current z-order position.
- `TransportManager.goTo()` does not exist — use `tm.addCommand(TransportCommand.makeJumpToBeat(state, tm, beat))`.
- `guisystem.transportManager` does not exist — use `guisystem.currentTransportManager`.
- `PlayMode.Play` does not exist — use `PlayMode(0)` (0=Play, 1=PlaySection, 2=LoopSection, 3=Stop, 4=HoldSection, 5=HoldEnd).

## Userguide
- [Track & Sequencing API](https://developer.disguise.one/plugins/guides/track-and-sequencing) | [Transports API](https://developer.disguise.one/plugins/guides/transports)
- [Timeline](https://help.disguise.one/designer/timeline-tracks-transports/timeline) | [Tracks](https://help.disguise.one/designer/timeline-tracks-transports/tracks-overview) | [Transports](https://help.disguise.one/designer/timeline-tracks-transports/transports-overview) | [Sections](https://help.disguise.one/designer/timeline-tracks-transports/adding-removing-sections) | [Set List](https://help.disguise.one/designer/timeline-tracks-transports/set-list) | [Crossfade](https://help.disguise.one/designer/timeline-tracks-transports/universal-crossfade) | [Notes](https://help.disguise.one/designer/timeline-tracks-transports/notes) | [Tags](https://help.disguise.one/designer/timeline-tracks-transports/tags)
