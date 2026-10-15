# Content & Media

## Key Classes
- `VideoAsset` (`Resource`) -- A video file registered in the project. Props: `fragments`, `regionSet`, `resolution`, `fps`, `nFrames`, `hasAlpha`, `hasAudio`, `codec`, `bitDepth`. Methods: `add()`, `remove()`, `insert()`, `enableFragment()`, `hasMultipleFragments()`.
- `VideoFragment` (`Resource`) -- One version/region entry inside a `VideoAsset`. Props: `version`, `region`, `enabled`, `proxies` (List[VideoFile]), `proxyInfo`. Methods: `findVideoFile(proxyLevel)`, `isNewerThan(version)`.
- `VideoFile` (`Resource`) -- The actual file on disk. Props: `info` (VideoInfo), `nFrames`, `ingestionDate`. Read-only metadata; never modified directly.
- `VideoClip` (`Resource`) -- Clip placed on a layer; references a `VideoAsset`. Props: `file`/`video_file`, `start`, `end`, `in_`, `out`, `fps`, `speed`, `quantised`, `nBeats`, `prefetchOptions`, `colourProfile`, `colourShift`, `audioBiasSec`, `audioOuts`, `enabledVersion`.
- `PrefetchLookaheads` (`Resource`) -- On `VideoClip.prefetchOptions`. Props: `Video_high_priority`, `Video_low_priority`, `Audio_high_priority`, `Audio_low_priority` (frame counts).
- `VideoRegion` -- Named rectangular region. Props: `name` (str), `region` (Rect).
- `VideoRegionSet` (`Resource`) -- Container of `VideoRegion` entries for SLC assets. Props: `regions` (List[VideoRegion]).
- `SlideShow` (`ResourceSequence`) -- Timed sequence of `VideoClip` slides. Props: `slides` (List[VideoClip]), `imageLength` (float, seconds), `sorted` (int 0/1), `looping` (int).
- `MediaManager` (`Subsystem`) -- Subsystem for media-related queries. Methods: `getMediaSize(filename)` -> int (bytes).

## Access
```python
# All video assets
assets = resourceManager.allResources(VideoAsset)

# By path (path segment is lowercase class name)
asset = resourceManager.load("objects/videoasset/my_clip.apx", VideoAsset)
clip  = resourceManager.load("objects/videoclip/my_clip.apx", VideoClip)

# Create if absent
clip = resourceManager.loadOrCreate("objects/videoclip/intro.apx", VideoClip)

# All clips
clips = resourceManager.allResources(VideoClip)

# MediaManager subsystem
mm = subsystems.getSystem(MediaManager)
```

## Video Assets & Fragments
```python
# Inspect an asset
asset = resourceManager.allResources(VideoAsset)[0]
print(asset.description, asset.resolution, asset.fps, asset.nFrames)
print(asset.codec, asset.bitDepth, asset.hasAlpha, asset.hasAudio)

# Fragments (versions/regions inside an asset)
for frag in asset.fragments:
    print(frag.version, frag.region, frag.enabled, frag.proxyInfo)
    vfile = frag.findVideoFile(0)   # proxyLevel 0 = full res
    if vfile:
        print(vfile.info.width, vfile.info.height, vfile.nFrames)

# Enable/disable a fragment
markDirty(asset)
asset.enableFragment(frag, False)

# Multiple fragments (SLC or versioned asset)
if asset.hasMultipleFragments():
    asset.moveFragment(0, 1)        # reorder by index

# Region sets (SLC: Single Large Canvas)
rset = asset.regionSet              # VideoRegionSet or None
if rset:
    for r in rset.regions:
        print(r.name, r.region)     # Rect: x, y, w, h
```

## Video Clips
```python
# Inspect a clip
clip = resourceManager.allResources(VideoClip)[0]
print(clip.enabledVersion, clip.proxyInfo)
print(clip.fps, clip.fileFps, clip.fileFrameSize, clip.fileNFrames)

# Trim / in-out points (frame indices)
clip.start = 0          # skip first N frames from file
clip.end   = 200        # last frame to use
clip.in_   = 0          # loop in-point
clip.out   = 200        # loop out-point

# Assign a video asset to a clip
clip.file = asset       # or clip.video_file = asset

# Beat-quantised playback
clip.quantised = 1      # 0=off, 1=on
clip.nBeats    = 120.0  # duration in beats when quantised
clip.speed     = 1.0    # playback speed multiplier

# Prefetch tuning (for large/slow clips) — optional
if clip.prefetchOptions:
    pf = clip.prefetchOptions
    markDirty(pf)
    pf.Video_high_priority = 120   # frames to prefetch while playing
    pf.Video_low_priority  = 60    # frames to prefetch while scrubbing
    pf.saveOnDelete()

# Crop (pixels from each edge)
clip.top = 0; clip.bottom = 0; clip.left = 0; clip.right = 0

# Consolidate all clips (remove unused fragment references)
VideoClip.consolidateAllClips()
```

## Slideshows
```python
ss = resourceManager.loadOrCreate("objects/slideshow/my_show.apx", SlideShow)
ss.imageLength = 4.0      # seconds per slide
ss.sorted      = 1        # auto-sort slides alphabetically
ss.looping     = 1

# Add slides (VideoClip objects) — markDirty needed for in-place list mutation
clip = resourceManager.load("objects/videoclip/slide1.apx", VideoClip)
markDirty(ss)
ss.slides.append(clip)

# Refresh clip list (rescans disk order)
ss.refreshClips()
```

## Media Status & Diagnostics
```python
# Missing media: VideoAsset exists but file not found locally
bad_assets = [a for a in resourceManager.allResources(VideoAsset) if a.isNotFoundLocal]
for a in bad_assets:
    print("Missing: %s" % a.description)

# Unused media: VideoAsset not referenced by any clip
used = set(c.file.uid for c in resourceManager.allResources(VideoClip) if c.file)
unused = [a for a in resourceManager.allResources(VideoAsset) if a.uid not in used]

# File size query via MediaManager
mm = subsystems.getSystem(MediaManager)
size = mm.getMediaSize("MyClip.mov")   # bytes; filename only, not full path
```

## Gotchas
- `VideoAsset` and `VideoClip` are separate resources. A single `VideoAsset` (file) can be referenced by multiple `VideoClip` objects. Deleting a clip does not remove the asset.
- `clip.file` and `clip.video_file` are aliases for the same property; prefer `clip.file`.
- `VideoFragment.proxies` contains `VideoFile` objects for each proxy level (0=full, then 1/16, 1/8, 1/4...). `findVideoFile(0)` returns full resolution.
- `clip.in_` is the Python name for the `in` field (reserved keyword). `clip.out` is unambiguous.
- `PrefetchLookaheads` is a sub-resource on `clip.prefetchOptions`; call `markDirty(pf)` on it, not on the clip. Note: `clip.prefetchOptions` may be `None` if not configured.
- `VideoRegionSet.regions` is a `List[VideoRegion]`; `VideoRegion` is not a `Resource` — it cannot be loaded by path.
- `MediaManager.getMediaSize` takes a **filename only** (no path). Returns 0 if file not found.
- `SlideShow` inherits `ResourceSequence`; `slides` is its typed property — do not use `setResource(t, r)` for slides.
- `clip.quantised` and `clip.bilinear_filtering` are `int` fields (0/1), not `bool`.

## Userguide
- [Content management overview](https://help.disguise.one/designer/content-management/content-management-overview) | [Placing media files](https://help.disguise.one/designer/content-management/placing-media-files) | [VideoClip object](https://help.disguise.one/designer/content-management/video-clip-object) | [Image sequences](https://help.disguise.one/designer/content-management/image-sequences) | [Slideshows](https://help.disguise.one/designer/content-management/slideshows)
- [Video codecs overview](https://help.disguise.one/designer/content-management/video-codecs/video-codec-overview) | [DXV](https://help.disguise.one/designer/content-management/video-codecs/dxv-codec) | [HAP/HAPQ](https://help.disguise.one/designer/content-management/video-codecs/hap-hapq-codec) | [ProRes](https://help.disguise.one/designer/content-management/video-codecs/prores-codec) | [Supported formats](https://help.disguise.one/designer/getting-started/supported-file-formats)
- [Media distribution](https://help.disguise.one/designer/content-management/media-distribution) | [Missing & unused media](https://help.disguise.one/designer/content-management/missing-and-unused-media) | [Content versioning](https://help.disguise.one/designer/content-management/content-versioning) | [Rendering media](https://help.disguise.one/designer/content-management/rendering-media)
