# Layers & Modules

Contents: Key Classes, Access, Modifying Layer Properties, Common Layer Properties, Video & Audio Modules, Generative & Effect Modules, Compositing & Arrows, Keyframing Layer Properties, Deleting Layers, Helpers, Gotchas, Userguide.

## Key Classes
- `SuperLayer` (`Resource`) -- base for all layer types. Props: `name`, `tStart`, `tEnd`, `tLength`, `render`, `renderEnable`, `track`, `container`, `crashed`, `isDormant`.
- `Layer` (`SuperLayer`) -- concrete layer. Props: `fields`, `moduleType`, `controlPatch`, `dmxIsolated`. Methods: `findSequence()`, `sequence(i)`, `nSequences()`, `keyTimes()`.
- `GroupLayer` (`SuperLayer`) -- group container. Props: `layers`, `arrows`, `expanded`. Methods: `nLayers()`, `removeChild()`.
- `Module` (`Resource`) -- base for all module types. Props: `blendMode`, `brightness`, `mapping`, `palette`, `tint`, `xCol`, `yCol`, `canvas`, `canvasSize`, `layer`, `isRendering`, `isGraphical`.

Common module types: `VariableVideoModule`, `AudioModule`, `BitmapModule`, `ColourModule`, `GradientModule`, `TextModule`, `BlurModule`, `ComposeModule`, `FadeModule`, `WebModule`, `RenderStreamModule`. d3 has 88+ module types — run `d3-ref.py --search <keyword>` to find others (e.g. `--search radar`, `--search particle`).

## Access
```python
# Layer access -- see timeline.md for track.layers / findLayerByName / addNewLayer
track  = guisystem.track              # current track (editor context)
layers = track.layers                 # List[SuperLayer]
layer  = track.findLayerByName("Bg")  # Layer or None (does not find GroupLayers)

# Access module type -- layer.moduleType returns the Python Type of the module class
if layer and layer.moduleType == VariableVideoModule:
    print("Layer is a video module")

# Enumerate all layers across all tracks
for layer in resourceManager.allResources(Layer):
    print("%s  module=%s" % (layer.name, layer.moduleType))
```

## Modifying Layer Properties
**Important**: Layer properties (brightness, video, position, etc.) are accessed via FieldSequence, not directly. Use `layer.findSequence(name)` to get a FieldSequence, then modify the underlying sequence.

**Preferred**: use the `set_layer_values` helper to set multiple values in one call:
```python
set_layer_values(layer, 0.0, speed=80.0, beamSize=180.0, mapping=dp, xCol=0.5)
```
It auto-detects float vs Resource values. The `findSequence` examples below document available sequence names per module — use them as a reference for `set_layer_values` kwargs.

**Sequence names vary per module — when in doubt, introspect.** Names use both dotted (`tint.r`, `pos.x`) and flat (`xPosition`, `yPosition`, `xCol`) forms with no consistent rule. Setting an unknown name throws `'NoneType' object has no attribute 'sequence'` from `findSequence`. Before writing layer code for an unfamiliar module type, dump the actual sequences:

```python
tmp = track.addNewLayer(SomeModule, 200.0, 1.0, "tmp")
names = [tmp.sequence(i).name for i in range(tmp.nSequences())]
track.removeLayer(tmp)
return names
```

Sequence types and their setters (when not using `set_layer_values`):
- **Numeric** (`FloatSequence`): `fseq.sequence.setFloat(beat, value)` — sets a float value at a beat time.
- **Resource** (`ResourceSequence`): `fseq.sequence.setResource(beat, resource)` — sets a resource reference at a beat time.
- **String** (`StringSequence`): `fseq.sequence.setString(index, "text")` — sets a string at a key index. Only for text-valued properties (e.g. TextModule "text").

Do **not** use `setString` for numeric properties — it is inherited from `KeySequence`, takes a key index (not beat time), and accepts strings (not floats). Use `setFloat` instead.

```python
# Enable keyframing on a property
fseq = layer.findSequence("brightness")
fseq.disableSequencing = False          # must be False to enable keyframing

# Modify numeric properties (FloatSequence)
ks = fseq.sequence                      # KeySequence (runtime: FloatSequence)
ks.setFloat(0.0, 0.5)                   # setFloat(beat, value)

# Modify resource properties (e.g. video, textures, layers)
fseq = layer.findSequence("video")      # for VariableVideoModule
clip = resourceManager.load("objects/videoclip/intro.apx", VideoClip)
fseq.sequence.setResource(layer.tStart, clip)  # ResourceSequence.setResource
```

## Common Layer Properties
All modules have these properties (access via FieldSequence):
```python
# Blending & opacity
fseq = layer.findSequence("blendMode")
fseq.sequence.setFloat(0.0, 0)          # 0=Normal, 1=Add, 2=Multiply, 3=Screen, ...

fseq = layer.findSequence("brightness")
fseq.sequence.setFloat(0.0, 1.0)        # 0.0-1.0; also controls alpha in alpha mode

# Projection mapping
fseq = layer.findSequence("mapping")
proj = resourceManager.load("objects/projection/MainScreen.apx", Projection)
fseq.sequence.setResource(layer.tStart, proj)
```

### Palette & Colour System
Colour in d3 layers is controlled by `palette` + `xCol`/`yCol`, NOT by `tint.r/g/b` directly:
- **palette**: a 2D colour lookup texture (DxTexture). Default: HSVPAL (full range of hues and saturations).
- **xCol**: horizontal position in palette. API range 0.0–1.0 (UI shows 0–255). 0=left, 1=right.
- **yCol**: vertical position in palette. API range 0.0–1.0 (UI shows 0–255). 0=top, 1=bottom.
- The palette colour at (xCol, yCol) is **multiplied** with the layer's generated output.
- Default (0, 0) in HSVPAL = white, so no colour change. To get a specific hue, increase yCol toward 1.0 (full saturation) and set xCol to the desired hue position.

HSVPAL approximate hue positions (at yCol=1.0 for full saturation):
- Red: xCol=0.0 — Orange: xCol=0.08 — Yellow: xCol=0.16 — Green: xCol=0.33
- Cyan: xCol=0.5 — Blue: xCol=0.66 — Purple: xCol=0.75 — Pink: xCol=0.83

```python
# Set layer colour to blue via palette lookup
fseq = layer.findSequence("xCol")
fseq.sequence.setFloat(0.0, 0.66)       # blue hue on HSVPAL
fseq = layer.findSequence("yCol")
fseq.sequence.setFloat(0.0, 1.0)        # full saturation

# Load a custom palette texture (overrides HSVPAL)
fseq = layer.findSequence("palette")
pal = resourceManager.load("objects/dxtexture/pal.apx", DxTexture)
fseq.sequence.setResource(layer.tStart, pal)

# tint.r/g/b — secondary multiplier (RGBA). Multiplies the palette-coloured output.
# Most use cases are served by xCol/yCol alone. tint is useful for dimming individual
# channels or when a custom palette is loaded.
fseq = layer.findSequence("tint.r")
fseq.sequence.setFloat(0.0, 1.0)        # access r/g/b/a separately
```

## Video & Audio Modules
```python
# VariableVideoModule — set video
fseq = layer.findSequence("video")
clip = resourceManager.load("objects/videoclip/intro.apx", VideoClip)
fseq.sequence.setResource(layer.tStart, clip)

# Playback settings
fseq = layer.findSequence("mode")
fseq.sequence.setFloat(0.0, 1)          # 0=Locked (chase timecode), 1=Normal (free-run)

fseq = layer.findSequence("speed")
fseq.sequence.setFloat(0.0, 1.0)        # playback speed multiplier

fseq = layer.findSequence("at end point")
fseq.sequence.setFloat(0.0, 0)          # 0=Loop, 1=Ping-pong, 2=Pause

fseq = layer.findSequence("transition time")
fseq.sequence.setFloat(0.0, 0.0)        # cross-fade time

fseq = layer.findSequence("volume")
fseq.sequence.setFloat(0.0, 1.0)

# Position / scale / crop
fseq = layer.findSequence("pos.x")      # also pos.y
fseq.sequence.setFloat(0.0, 0.0)

fseq = layer.findSequence("scale.x")    # also scale.y
fseq.sequence.setFloat(0.0, 1.0)

fseq = layer.findSequence("rotation")
fseq.sequence.setFloat(0.0, 0.0)

for side in ["left", "right", "top", "bottom"]:
    fseq = layer.findSequence(side)
    fseq.sequence.setFloat(0.0, 0.0)    # crop fractions

# AudioModule
amod_layer = track.addNewLayer(AudioModule, 0.0, 120.0, "Audio")
fseq = amod_layer.findSequence("track")
audio = resourceManager.load("objects/audioclip/sfx.apx", AudioTrack)
fseq.sequence.setResource(amod_layer.tStart, audio)

fseq = amod_layer.findSequence("balance")
fseq.sequence.setFloat(0.0, 0.0)        # -1=left, 0=centre, 1=right
```

## Generative & Effect Modules
```python
# ColourModule — solid fill; colour via palette xCol/yCol (see Palette & Colour System)
# For simple RGB control, prefer RGBColourModule (explicit red/green/blue sequences)
col = track.addNewLayer(RGBColourModule, 0.0, 120.0, "Solid")
set_layer_values(col, col.tStart, mapping=dp, red=0.0, green=0.0, blue=1.0, brightness=1.0)

# GradientModule — colour comes from palette lookup via xCol/yCol, NOT from tint.r/g/b
# Default palette: hsvpalette.png (X=hue 0-1, Y=saturation 0=white,1=full colour)
# Sequences: type, angle, length, position.x/y, Inner radius, scale.x/y, gamma, dither, interpolation
#
# SockPuppetGradientModule adds: col2.r, col2.g, col2.b, bright2, "1st brightness"
# Stop 1: palette at (xCol, yCol) * "1st brightness"
# Stop 2: col2.r/g/b * bright2
# tint.r/g/b has NO effect on gradient colours — use xCol/yCol instead
grad = track.addNewLayer(SockPuppetGradientModule, 0.0, 120.0, "Gradient")
set_layer_values(grad, grad.tStart,
    mapping=dp, blendMode=0.0,
    **{"type": 0, "angle": 90.0, "length": 1.0,
       "xCol": 0.66, "yCol": 1.0,          # blue on HSV palette (hue=0.66)
       "1st brightness": 1.0,
       "col2.r": 0.0, "col2.g": 0.0, "col2.b": 0.0,
       "bright2": 1.0})

# TextModule
# Full sequences: blendMode, brightness, mapping, palette, xCol, yCol,
#                 tint.r/g/b/a, text, fontSize, xPosition, yPosition,
#                 font, hAlignment, vAlignment
# Position sequences are xPosition / yPosition — NOT pos.x / pos.y.
# pos.* and scale.* are VariableVideoModule sequences; they do not exist on TextModule.
fseq = layer.findSequence("text")
fseq.sequence.setString(0, "Hello World")  # string property — uses setString(index, text)

fseq = layer.findSequence("fontSize")
fseq.sequence.setFloat(0.0, 72)

fseq = layer.findSequence("hAlignment")
fseq.sequence.setFloat(0.0, 1)          # 0=Left, 1=Centre, 2=Right

fseq = layer.findSequence("vAlignment")
fseq.sequence.setFloat(0.0, 1)

fseq = layer.findSequence("xPosition")  # offset within mapping (~ -0.5 .. 0.5)
fseq.sequence.setFloat(0.0, 0.0)
fseq = layer.findSequence("yPosition")  # negative = down
fseq.sequence.setFloat(0.0, -0.3)

# BlurModule
fseq = layer.findSequence("radius")
fseq.sequence.setFloat(0.0, 5.0)

# FadeModule — per-Projection brightness control (up to 8 groups)
fade_layer = track.addNewLayer(FadeModule, 0.0, 120.0, "Fade")
fseq = fade_layer.findSequence("fade_0")
fseq.sequence.setFloat(0.0, 0.5)
fseq = fade_layer.findSequence("group_0")
proj = resourceManager.load("objects/projection/Stage.apx", Projection)
fseq.sequence.setResource(fade_layer.tStart, proj)
```

### GradientModule value semantics

The sequence *names* of GradientModule do not show how the *values* work. The notes below come from `d3.pyi` unless marked "observed":

- **`type`** — `{0: 'Linear', 1: 'Radial'}`.
- **`angle`** — gradient direction in degrees (observed: `90` = vertical).
- **`length`** — extent of the gradient ramp across the canvas.
- **Two colour stops.** Stop 1 = palette lookup at (`xCol`, `yCol`) scaled by `"1st brightness"`; stop 2 = `"2nd xCol"`/`"2nd yCol"` (or, on `SockPuppetGradientModule`, `col2.r/g/b`) scaled by `"2nd brightness"` / `bright2`. **`"2nd brightness" = 0.0` blacks out the far end of the ramp** — combined with a mis-centred radial this makes one side of a wall go fully dark, which reads like a mapping bug but is a content setting.
- **`position`** — a `Vec2`. The unit and origin are not documented. In one test, `position = (0.5, 0.5)` did **not** centre a radial (`type=1`): the centre was near 25% of the canvas width. To centre a radial, change `position` step by step and capture the result. Do not assume that `0.5,0.5` is the centre.
- **`Inner radius`** — inner falloff radius for radial gradients.
- Note a *separate* interpolation field, `{0: 'Linear', 1: 'SmoothStep'}` — distinct from `type`.

**Sequence-name forms are mixed:** dotted (`position.x`, `angle`, `length`) alongside space-containing (`"1st brightness"`, `"2nd brightness"`, `"2nd xCol"`, `"Inner radius"`). Dotted names pass as normal kwargs; space-containing ones must go through `**{...}`:

```python
# Full-width LINEAR wash across a multi-screen Parallel (the common wall case)
grad = track.addNewLayer(SockPuppetGradientModule, 0.0, length, "Wash")
set_layer_values(grad, grad.tStart,
    mapping=pp, blendMode=0.0,
    **{"type": 0,               # 0 = Linear
       "angle": 0.0,            # 0 = horizontal ramp across the wall (degrees, observed)
       "length": 1.0,           # span the full canvas
       "xCol": 0.66, "yCol": 1.0,          # stop 1: blue (HSV palette hue 0.66)
       "1st brightness": 1.0,
       "2nd xCol": 0.66, "2nd yCol": 1.0,  # stop 2: same hue...
       "2nd brightness": 1.0})             # ...keep >0 or that end goes black
```

### Stage bring-up modules: TestPattern & Radar

These two modules are the most common checks for a rig. The sequence names below come from introspection of a running project. Use introspection to confirm them in your build.

**`TestPatternModule`** — `brightness`, `mapping`, `palette`, `xCol`, `yCol`, `tint.r/g/b/a`, `circles`, `circleRadius`, `label`, `gridMode`, `gridSpacing`, `subGridSpacing`, `logoTopLeft`, `logoBottomRight`, `acesExposure`, `acesGamma`, `ocioExposure`, `ocioContrast`, `ocioGamma`.
> **⚠️ No `blendMode`** (unlike almost every other module — verified against d3.pyi). `set_layer_values(..., blendMode=...)` on a TestPatternModule **throws**. `label = 1` renders legible text + the disguise logo — invaluable for UV verification (see `references/blender-meshes.md`).

**`RadarModule`** — `blendMode`, `brightness`, `mapping`, `palette`, `xCol`, `yCol`, `tint.r/g/b/a`, `speed`, `beamSize`, `direction` (`0` H / `1` V), `timing` (`0` per-sec / `1` per-beat / `2` per-frame), `pixelPerBeatOffset`.

**Make a test-pattern rig read as lit LED.** Test patterns are thin light lines on black, so a big lineup rig renders as near-black rectangles and contributes nothing to `Area_lighting`. Add an `RGBColourModule` wash per region with **`blendMode = 1` (Add)** at ~0.6–0.8 brightness, hue-coded per zone: pattern/radar stay legible, the rig looks alive, and the screens spill coloured light onto scenic geometry (see `references/lighting-rendering.md`).

## Compositing & Arrows
```python
# Arrow = feeds one layer's output as the source for another
track.makeArrow(video_layer, blur_layer)

# ComposeModule merges up to 4 sources
compose_layer = track.addNewLayer(ComposeModule, 0.0, 120.0, "Composer")
fseq = compose_layer.findSequence("content source 1.texture")
fseq.sequence.setResource(compose_layer.tStart, video_layer_a)
fseq = compose_layer.findSequence("source 1")
fseq.sequence.setFloat(0.0, 0.7)        # 70% proportion

# GroupLayer — logical container (not a rendering node)
for l in track.layers:
    if isinstance(l, GroupLayer):
        for child in l.layers:
            print(child.name)
```

## Keyframing Layer Properties
```python
# See timeline.md "Layer Field Sequences" for full keyframe API.
fseq = layer.findSequence("brightness")
fseq.disableSequencing = False          # enable keyframing

ks = fseq.sequence                      # FloatSequence at runtime
ks.setFloat(0.0, 1.0)                   # value at beat 0
ks.setFloat(30.0, 0.5)                  # value at beat 30

val = fseq.eval(60.0, 0)               # evaluate at beat

# Enumerate available sequences
for i in range(layer.nSequences()):
    print(layer.sequence(i).name)
```

## Deleting Layers
```python
# Remove one layer
markDirty(track)
track.removeLayer(layer)

# Clear all layers
markDirty(track)
del track.layers[:]
```

## Helpers (mcp_helpers)

`set_layer_values(layer, beat, **kwargs)` — set multiple sequence values on a layer. Auto-detects float vs Resource. **kwargs, not a dict.**

```python
set_layer_values(layer, 0.0, video=clip, mapping=dp, brightness=0.8)
# Module-less scripts: from user_module_mcp_helpers import set_layer_values
```

`search_resources(keyword, types=None)` — search resources by keyword against path.

```python
search_resources("intro", [VideoClip])    # returns {"matches": [...]}
search_resources("test pattern")          # defaults to [VideoClip, AudioTrack, DxTexture]
# Module-less scripts: from user_module_mcp_helpers import search_resources
```

## Gotchas
- `Layer` properties are accessed via `findSequence()` + FieldSequence. `layer.moduleConfig` is separate and most module types return `None` for it.
- Sequence names use spaces and dots: `"at end point"`, `"source 1"`, `"content source 1.texture"`, `"1st brightness"`, `"col2.r"`.
- **TextModule positions are `xPosition` / `yPosition`** — NOT `pos.x` / `pos.y`. `pos.*` and `scale.*` exist on `VariableVideoModule` but not on TextModule. When unsure of a module's sequence names, dump them via `[layer.sequence(i).name for i in range(layer.nSequences())]`.
- `VideoModule` is deprecated — use `VariableVideoModule`.
- Numeric properties use `fseq.sequence.setFloat(beat, value)` (FloatSequence); resource properties use `fseq.sequence.setResource(beat, resource)` (ResourceSequence); string properties use `fseq.sequence.setString(index, "text")` (StringSequence).
- `GroupLayer` is a `SuperLayer` but not a `Layer` — `track.findLayerByName()` won't find groups.
- `addNewLayer(ModuleType, tStart, length, name)` — third arg is **duration** (not end beat).
- `nSequences()` is a **method** (needs `()`) — `range(layer.nSequences())`.
- Module-specific property values use the same scale as the d3 UI. Look up default values via `d3-ref.py --classes` — e.g. `RadarModule.beamSize` defaults to 128 (range 0-255), not 0.0-1.0.
- For solid colour fills use `RGBColourModule` (explicit `red`/`green`/`blue` sequences) — simpler than `ColourModule` which requires palette tint manipulation.
- **Gradient colours come from the palette via `xCol`/`yCol`** — `tint.r/g/b` has NO effect. Default palette is `hsvpalette.png` (X=hue 0→1, Y=saturation 0=white→1=full colour). For blue: `xCol=0.66, yCol=1.0`. For red: `xCol=0.0, yCol=1.0`.
- For 2-colour gradients use `SockPuppetGradientModule` — stop 1 from palette `xCol`/`yCol`, stop 2 from `col2.r/g/b` + `bright2`.

## Userguide
- [Layers Overview](https://help.disguise.one/designer/layers/layers-overview) | [Layer Types](https://help.disguise.one/designer/layers/layer-types/layer-types-index) | [Common Properties](https://help.disguise.one/designer/layers/common-layer-properties/common-layer-properties-overview)
- [Editing Layers](https://help.disguise.one/designer/layers/editing-layers/working-with-layers-overview) | [Compositing](https://help.disguise.one/designer/layers/compositing-layers) | [Keyframing](https://help.disguise.one/designer/layers/keyframing-layers/keyframing-layers-overview)
