# Lighting & Rendering (previz)

**Set this up before judging how a stage looks.** Almost every "it looks flat / dull / washed out" conclusion is a renderer default you haven't found yet, not your model. A blank project has **no lights**, an **unlit** renderer, and near-black scene ambient. (Verified on Designer 34.0.1 / r257961.)

## The lit renderer lives on the CAMERA, not the stage

There is **no** stage-level Lux toggle.

> **`Stage.Chicago_renderer` is NOT the Lux toggle — do not use it.** It accepts `0/1` and reads your value back, but **reverts to `0` on every `stage.save()`**. It's the most plausible-looking wrong answer in `dir(stage)`; ignore it.

The real controls are on **`camera.stageRenderSettings`** (a `StageRenderSettings` resource).

> **⚠️ Shared resource.** `camera.stageRenderSettings` resolves to the shared `objects/stagerendersettings/default.apx`. Changing it affects the **user's editor viewport too**, not just your capture camera. That's usually what you want for previz, but say so / expect it.

| Property | Default | Notes |
|---|---|---|
| `Lux` | `1` | Already on in a blank project — **not** what makes it flat |
| `renderer` | `0` | Enum `{0:'Schematic', 1:'Lux', 2:'Heatmap', 3:'Depth'}` (d3.pyi). **`0` (Schematic) = flat/unlit; `1` (Lux) = lit.** Set `1` for lit previz — THIS is the switch |
| `exposure` | `200.0` | Camera white point, in Lux (d3.pyi). Match to `stage.ambientLight`: 200 against ~1700 lux ambient ≈ 8 stops over → milky/washed out. `1400` was right for that scene |
| `ssaoRadius` | `1.0` | Tiny for stage scale — `3.2` on a 150 m stage gave proper contact shadows |
| `ssaoPower` | `1.0` | `1.9` worked well |
| `ssaoKernelSize` | `16` | `32` for quality |
| `glowBrightness` | `0.5` | |
| `msaaMode` | `0` | Enum `{0:None, 1:'MSAA 2X', 2:'MSAA 4X', 3:'MSAA 8X'}` (d3.pyi) |
| `backgroundColour` | `Colour(0,0,0,1)` | |

(All `StageRenderSettings` members above verified against d3.pyi except the observed default values and scene-specific tuned values.)

> **Display-name labels can't be turned off here.** `drawLEDScreenLabels` / `drawPropLabels` / … and `setAllLabelVisibility()` had **no observable effect** — the editor draws the names regardless. Don't try to clean up captures this way.

```python
cam = <your camera>
srs = cam.stageRenderSettings          # shared objects/stagerendersettings/default.apx
srs.Lux = 1
srs.renderer = 1                       # 0 = unlit/flat, 1 = lit. THIS is the switch.
srs.exposure = 1400.0                  # match stage.ambientLight or the image washes out
srs.ssaoRadius = 3.2                   # default 1.0 is tiny for stage-scale geometry
srs.ssaoPower = 1.9
srs.ssaoKernelSize = 32
srs.glowBrightness = 0.75
srs.save()
```

`deferSaveScreenFrame` (the capture fallback, see `references/visual-verification.md`) renders **through the camera's `stageRenderSettings`**, so it picks up `renderer`/`exposure`/SSAO — the fallback is a genuine equivalent, not a downgrade.

## Stage lighting — a blank project has none

`stage.lights` is **empty** in a blank project; there is no default key light.

- **`Light`** is an `Object` subclass (`offset`, `rotation`, `scale`, `mesh`) plus **`brightness`** (lux, default `400.0`) and **`colour`** (`Colour`, floats 0–1). **No cone/spread/falloff — it's a directional light**, aimed by `rotation`.
- Creating one logs `!!! Main thread hung due to early render access < Mesh::makeEdgeTribuffer < Camera::createMesh` — **harmless**, not an error.

Stage-level lighting/atmosphere (types matter — note the two ambient colours differ):

| Property | Default | Notes |
|---|---|---|
| `ambientLight` | `890.0` | lux |
| `ambientColour` | `Colour(1,1,1,1)` | **floats 0–1** |
| `sceneAmbientColour` | `Col(25,25,25,255)` | **`Col`, 0–255 ints** — near-black by default, a major cause of dull previz |
| `depthFogDistance` | `50.0` | **Greys out most of a large model.** A 260 m-wide stage needed `420.0` — a top "why is my previz washed out" cause |
| `Area_lighting` (0/1) + `areaLightingBrightness` | | **LED screens cast light onto scenic geometry** — the single biggest previz win for an LED-heavy stage; recommend enabling by default |
| `Reflections`, `Glow`, `glowThreshold`, `Adaptive_Tone_map` | | persist through `save()` |

> **Persistence is inconsistent.** `Area_lighting`, `Reflections`, `Glow`, `Adaptive_Tone_map` persist through `stage.save()`; `Chicago_renderer` does not. **Re-assert runtime flags after any save and verify by read-back.**

Also present: `blurPasses`, `blurSigma`, `scatterDensity`, `shadowBias`, `lightBleedReduction`, `floorLuminosity`, `floorAlpha`, `luxTicks`, `heatMapMinLux`/`heatMapMaxLux`, `footprintsQuality`.

```python
st = state.stage
def add_light(nm, off, rot, lux, col):
    l = resourceManager.loadOrCreate("objects/light/%s.apx" % nm, Light)
    l.rename(l.path)
    l.offset, l.rotation, l.brightness = off, rot, lux
    l.colour = Colour(col[0], col[1], col[2], 1.0)
    l.save()
    return l

markDirty(st)
have = [str(x.path.filename) for x in st.lights]
for nm, off, rot, lux, col in [
    ("key",  Vec(-70, 60, -120), Vec(-38,  30, 0), 6500.0, (1.00, 0.86, 0.68)),
    ("fill", Vec( 85, 40, -110), Vec(-24, -38, 0), 2600.0, (0.72, 0.84, 1.00)),
    ("rim",  Vec(  0, 70,   90), Vec( 28, 180, 0), 3200.0, (1.00, 0.78, 0.58)),
    ("up",   Vec(  0,  2,  -40), Vec( 52,   0, 0), 1500.0, (1.00, 0.90, 0.74))]:
    l = add_light("tml " + nm, off, rot, lux, col)
    if str(l.path.filename) not in have:
        st.lights.append(l)

st.ambientLight        = 1700.0
st.ambientColour       = Colour(1.0, 0.93, 0.84, 1.0)
st.sceneAmbientColour  = Col(64, 58, 54, 255)    # NB: 0-255 ints, unlike ambientColour
st.depthFogDistance    = 420.0                   # default 50 greys out large stages
st.Area_lighting       = 1
st.areaLightingBrightness = 4.5                  # LED spills onto scenic — big win
st.Reflections         = 1
st.Glow                = 1
st.glowThreshold       = 0.85
st.Adaptive_Tone_map   = 1
st.saveOnDelete(); st.save()
# Re-assert + read-back the runtime flags after save (persistence is inconsistent).
```

## Making a test-pattern rig read as lit

Test patterns are thin light lines on black, so a big lineup rig renders as rows of near-black rectangles and contributes nothing to `Area_lighting`. Add an `RGBColourModule` wash per region with **`blendMode = 1` (Add)** at ~0.6–0.8 brightness, hue-coded per zone: the pattern/radar stay legible, the rig looks alive, and the screens spill coloured light onto the scenic geometry.
