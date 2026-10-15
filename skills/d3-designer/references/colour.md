# Colour Management

## Key Classes
- `ColourProfile` (`Resource`) — colour space + gamma definition. Props: `colourspace` (int), `gammacurve` (int), `gammaLevel`, `paperwhite`, `peakwhite`, `tonemapping`, `profilename`, `customPrimaries`.
- `ColourShift` (`Resource`) — per-layer grade: brightness/contrast, hue, saturation, chroma key. Per-channel (R/G/B) control via `RGB_controlled`.
- `LutFile` (`Resource`) — `.cube` LUT file reference with optional ACES/OCIO wrapping.
- `CDL` (`Resource`) — ASC CDL grade (slope/offset/power/saturation). Method: `exportCC(path, id)`.
- `LutModule` (`ProjectionAwareModule`) — effect layer applying a LUT. Props: `lutfile`, `lutLumaIntensity`, `lutChromaIntensity`.
- `ColourModule` (`ProjectionAwareModule`) — solid colour / tint layer inheriting `tint`, `brightness`, `ocioInputSpace`.
- `Colour` (value type) — RGBA floats. Methods: `mix()`, `toHSL()`, `fromHSL()`, `toNormalisedColour()`, `toVec()`.
- `AcesInputTransformParameters` / `AcesOutputTransformParameters` — embedded ACES transforms in `LutFile` / `CDL`.
- `OcioColourSpace` — OCIO colour space embedded in `LutFile` / `CDL`. Method: `set(name, view, isBuiltin)`.
- `ChromaticitySet` — custom primary chromaticities: `red`, `green`, `blue`, `white` (Vec2 xy), `ca`.

## Access
```python
profiles = resourceManager.allResources(ColourProfile)
shifts   = resourceManager.allResources(ColourShift)
luts     = resourceManager.allResources(LutFile)
cdls     = resourceManager.allResources(CDL)

prof = resourceManager.loadOrCreate("objects/colourprofile/rec709.apx", ColourProfile)
cs   = resourceManager.loadOrCreate("objects/colourshift/grade.apx", ColourShift)
cdl  = resourceManager.loadOrCreate("objects/cdl/grade1.apx", CDL)

# Find existing LUT (can't create without .cube file on disk)
luts = resourceManager.allResources(LutFile)
if luts:
    lut = luts[0]
```

## Colour Profiles
```python
prof.colourspace = 0    # 0=BT.709, 1=BT.2020, 2=ACES AP0, 3=ACES AP1, 4=ALEXA WG, etc.
prof.gammacurve  = 0    # 0=sRGB, 1=Linear, 2=PQ ST.2084, 3=HLG, etc.
prof.gammaLevel  = 2.2  # only used when gammacurve == 13
prof.paperwhite  = 100.0   # SDR reference white (nits)
prof.peakwhite   = 1000.0  # HDR peak (nits)
prof.tonemapping = 0       # HDR->SDR technique (int)
prof.profilename = "Rec709 SDR"

# Custom primaries (colourspace == 14)
markDirty(prof)
prof.customPrimaries.red   = Vec2(0.640, 0.330)
prof.customPrimaries.green = Vec2(0.300, 0.600)
prof.customPrimaries.blue  = Vec2(0.150, 0.060)
prof.customPrimaries.white = Vec2(0.3127, 0.3290)
prof.customPrimaries.ca    = 0  # chromatic adaptation
```

## Colour Shifts (Grades)
```python
cs.brightness__shift_ = 0.0    # additive offset
cs.contrast__scale_   = 1.0    # scale
cs.saturation_scale   = 1.0    # 0=b/w, 1=normal, >1=saturated
cs.hue_shift          = 0.0    # degrees

# Per-channel levels (requires RGB_controlled = 1)
cs.RGB_controlled = 1           # 0=linked, 1=separate R/G/B
cs.red_min = 0.0;   cs.red_max = 1.0;   cs.red_gamma = 1.0
cs.green_min = 0.0; cs.green_max = 1.0; cs.green_gamma = 1.0
cs.blue_min = 0.0;  cs.blue_max = 1.0;  cs.blue_gamma = 1.0

# Chroma key (e.g. green screen)
cs.key_colour = Colour(0.0, 1.0, 0.0, 1.0)
cs.threshold  = 0.1   # colour distance to become transparent
cs.hardness   = 0.8   # edge softness
```

## LUT Files & Module Tint
```python
# Configure LutFile resource
luts = resourceManager.allResources(LutFile)
if luts:
    lut = luts[0]
    markDirty(lut)                   # sub-object mutation (acesPreTransform, acesPostTransform, ocioTransform)
    lut.acesPreTransform.type  = 0   # Optional ACES output transform
    lut.acesPostTransform.type = 0   # Optional ACES input transform
    lut.ocioTransform.set("Filmic Log", "", True)  # Optional OCIO wrapping

# Apply LUT via LutModule layer
track = guisystem.track
if track and track.layers:
    layer = track.layers[0]
    lut_mod = layer.module
    if luts:
        lut_mod.lutfile            = luts[0]
        lut_mod.lutLumaIntensity   = 1.0   # 0-1
        lut_mod.lutChromaIntensity = 1.0   # 0-1
```

## CDL (ASC Color Decision List)
```python
cdl = resourceManager.loadOrCreate("objects/cdl/grade1.apx", CDL)

cdl.slope      = Vec(1.1, 1.0, 0.9)     # (R, G, B) multiply
cdl.offset     = Vec(0.02, 0.0, -0.01)  # (R, G, B) additive
cdl.power      = Vec(0.9, 1.0, 1.1)     # (R, G, B) gamma
cdl.saturation = 1.2

# Optional ACES/OCIO context (sub-object mutation — markDirty needed)
markDirty(cdl)
cdl.acesPreTransform.type  = 0
cdl.acesPostTransform.type = 0
cdl.ocioTransform.set("ACES - ACEScct", "", True)

# Export to ASC .cc file
ok = cdl.exportCC("<folder>/grade1.cc", "grade1_id")
```

## OCIO & ACES Transforms (embedded sub-objects)
```python
# OcioColourSpace — embedded in LutFile or CDL
luts = resourceManager.allResources(LutFile)
if luts:
    lut = luts[0]
    ocs = lut.ocioTransform
    ocs.set("Filmic sRGB", "", True)          # built-in space by name
    ocs.set("My Display", "My View", False)   # display-view pair
    # ocs.type: 0=input, 1=output, 2=working

    # AcesInputTransformParameters / AcesOutputTransformParameters
    lut.acesPreTransform.type         = 0
    lut.acesPreTransform.genericSpace = 0
    lut.acesPreTransform.genericCurve = 0
```

## Colour Value Type
```python
c = Colour(1.0, 0.5, 0.0, 1.0)    # r, g, b, a
c.r = 0.8; c.g = 0.4; c.b = 0.2; c.a = 1.0

# Operations
mid  = c.mix(Colour(0.0, 0.0, 0.0, 1.0), 0.5)  # 50% blend to black
hsl  = c.toHSL()                    # returns Vec (h, s, l)
c2   = Colour.fromHSL(0.5, 0.8, 0.5)
norm = c.toNormalisedColour()        # clamp to 0-1
v    = c.toVec()                     # returns Vec (r, g, b, a)
```

## Module Tint & OCIO Input
```python
# All Module subclasses (VariableVideoModule, LutModule, ColourModule, etc.) have:
track = guisystem.track
if track and track.layers:
    mod = track.layers[0].module
    mod.tint       = Colour(1.0, 0.8, 0.8, 1.0)  # tint applied on top
    mod.brightness = 1.0                          # 0=transparent, 1=normal
    # mod.ocioInputSpace: OcioColourSpace (read-only) — OCIO input colour space
```

## Gotchas
- Histogram, vectorscope, waveform — UI-only analysis tools, no Python API.
- `description` is a property, not a method: `prof.description` (not `prof.description()`).
- `ColourShift.RGB_controlled=0` means linked channels; set to `1` before per-channel min/max/gamma.
- `ColourProfile.colourspace` and `.gammacurve` are raw ints — no named Python constants; use comment tables as reference.
- `OcioColourSpace.set(name, view, isBuiltin)` — pass `""` for `view` when not a display-view pair.
- `AcesInputTransformParameters` / `AcesOutputTransformParameters` are embedded sub-objects, not resources.
- `LutFile` wraps an external `.cube` file (must exist on disk); `ColourProfile` is self-contained.
- `exportCC()` accepts both plain strings and `Path()` objects for the file path.
- Project-level colour management mode (Disabled / Gamma Space / ACES / OCIO) is not scriptable.

## Userguide
- [Overview](https://help.disguise.one/designer/colour-management/colour-management-overview) | [Colour Profiles](https://help.disguise.one/designer/colour-management/colour-profiles) | [Colour Shifts](https://help.disguise.one/designer/colour-management/colour-shifts) | [Colour Transforms](https://help.disguise.one/designer/colour-management/colour-transforms)
- [ACES](https://help.disguise.one/designer/colour-management/aces) | [OCIO](https://help.disguise.one/designer/colour-management/ocio) | [LUT Files](https://help.disguise.one/designer/colour-management/lut-files) | [CDL](https://help.disguise.one/designer/colour-management/cdl)
- [Histogram](https://help.disguise.one/designer/colour-management/histogram) | [Vectorscope](https://help.disguise.one/designer/colour-management/vectorscope) | [Waveform](https://help.disguise.one/designer/colour-management/waveform) | [Colour Inspector](https://help.disguise.one/designer/colour-management/colour-inspector) | [Livegrade Integration](https://help.disguise.one/designer/colour-management/livegrade-studio-integration)
