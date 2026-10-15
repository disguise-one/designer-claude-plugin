# Audio

## Key Classes
- `AudioSystem` (`Subsystem`) -- audio subsystem. Props: `isEnabled`, `name`. Methods: `maxNumberOfPatches()`.
- `AudioModule` (`Module` > `Resource`) -- audio layer module on the timeline. Props: `track` (AudioTrack), `output` (LogicalAudioOutDevice), `volume`, `balance`, `mode` (0=Normal/1=Locked), `at_end_point` (0=Loop/1=Pause), `transition_time`. Methods: `prevPlayerAudibility()`.
- `AudioTrack` (`Resource`) -- audio file container. Props: `audioFile` (AudioFile), `filename`, `header` (AudioInfo, ro), `iPivotBeat`, `nBeatsPerLoop`, `stereoOption` (0=Both/1=Left/2=Right), `markers`.
- `AudioFile` (`Resource`) -- audio file metadata. Props: `header` (AudioInfo, rw), `ingestionDate`.
- `AudioInfo` -- metadata on `header` properties. Props: `sampleRate`, `nChannels`, `nSamples`, `duration`, `codecName`.
- `AudioLink` (`Resource`) -- AudioAnalyser signal routing. Props: `line` (AudioLine), `from_` (trailing underscore: `from` is a keyword), `to`, `mode` (0=off/1=raw/2=fft/3=pitch), `decay`.
- `LogicalAudioOutDevice` (`LogicalDevice` > `Resource`) -- logical output device. Match devices by `description` string.
- `MtcModule` (`Module` > `Resource`) -- MIDI Time Code output layer. Props: `iDevice`, `play_mode` (0=Locked/1=Normal), `type` (0=MTC24/1=MTC25/2=MTC29.97/3=MTC30/4=MTC30DF), `start_hour/min/sec/frame`.

## Access
```python
audio_sys = subsystems.getSystem(AudioSystem)
max_patch = audio_sys.maxNumberOfPatches()

modules = resourceManager.allResources(AudioModule)
tracks = resourceManager.allResources(AudioTrack)
files = resourceManager.allResources(AudioFile)
devices = resourceManager.allResources(LogicalAudioOutDevice)
links = resourceManager.allResources(AudioLink)

# By path
trk = resourceManager.load("objects/audiotrack/music.apx", AudioTrack)
```

## AudioTrack Configuration
```python
trk = resourceManager.loadOrCreate("objects/audiotrack/stem_vox.apx", AudioTrack)
af = resourceManager.loadOrCreate("objects/audiofile/vox.wav.apx", AudioFile)

trk.audioFile = af
trk.stereoOption = 0     # 0=Both, 1=Left Only, 2=Right Only
trk.nBeatsPerLoop = 32.0
trk.iPivotBeat = 0.0

# Inspect audio metadata
info = af.header  # AudioInfo: sampleRate, nChannels, nSamples, duration, codecName
print(trk.filename)
```

## AudioModule Volume & Routing
```python
mod = resourceManager.loadOrCreate("objects/audiomodule/audio_mod.apx", AudioModule)

mod.volume = 0.8         # 0.0-1.0
mod.balance = 0.0        # -1.0=left .. 1.0=right
mod.mode = 0             # 0=Normal, 1=Locked (synced to transport)
mod.at_end_point = 0     # 0=Loop, 1=Pause at end
mod.transition_time = 0.0

audibility = mod.prevPlayerAudibility()  # last played volume level
```

## Audio Analysis (AudioLink)
```python
link = resourceManager.loadOrCreate("objects/audiolink/analyser_link.apx", AudioLink)

link.mode = 2      # 0=off, 1=raw (amplitude), 2=fft, 3=pitch
link.decay = 0.3
link.from_ = 0     # source channel (trailing underscore: from is a keyword)
link.to = 1        # destination parameter index

line = link.line   # AudioLine: real-time signal data
```

## MTC Output
```python
mtc = resourceManager.loadOrCreate("objects/mtcmodule/mtc_out.apx", MtcModule)

mtc.type = 3           # 0=MTC24, 1=MTC25, 2=MTC29.97, 3=MTC30, 4=MTC30DF
mtc.play_mode = 0      # 0=Locked (chase transport), 1=Normal
mtc.iDevice = 0        # MIDI output device index
mtc.start_hour = 0
mtc.start_min = 0
mtc.start_sec = 0
mtc.start_frame = 0
```

## Notes
- `AudioLink.from_` uses a trailing underscore — `from` is a Python keyword.
- Transport master volume lives on the `TransportVolumeLocal` layer, not on `AudioSystem`.
- `AudioSystem.maxNumberOfPatches()` caps the number of audio output mappings; exceeding it silently ignores extras.
- `AudioTrack.header` is read-only. Modify `AudioFile.header` to set format metadata.
- Multichannel routing (ASIO/WASAPI) is configured in the Designer UI, not exposed as writable Python properties.

## Userguide
- [Audio overview](https://help.disguise.one/designer/audio/audio-overview) - [Setup audio output](https://help.disguise.one/designer/audio/setup-audio-output) - [Quantised audio](https://help.disguise.one/designer/audio/quantised-audio)
- [Multichannel audio](https://help.disguise.one/designer/audio/output-multichannel-audio) - [Professional audio](https://help.disguise.one/designer/audio/output-professional-audio) - [Video-embedded audio](https://help.disguise.one/designer/audio/output-video-embedded-audio)
- [Python plugin guide: audio](https://developer.disguise.one/plugins/guides/audio)
