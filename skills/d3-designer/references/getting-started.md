# Getting Started

Licensing and the first-show recipes. Video input formats (`VideoInFormat`) are in `video-input.md`.

## Licensing Capability Matrix

Hardware platform + license tier together determine available features. Key constraints for automation:

| Capability                        | Starter / PC | Pro / PC | Starter / Disguise HW | Pro / Disguise HW |
|-----------------------------------|:---:|:---:|:---:|:---:|
| Editor (local design/programming) | Yes | Yes | Yes | Yes |
| Director / Actor / Understudy     | No  | No  | Yes | Yes |
| Unwatermarked feed/DMX outputs    | No  | No  | No  | Yes |

- **Director/Actor/Understudy roles** require Disguise hardware regardless of license tier.
- **Unwatermarked outputs** require Disguise hardware **and** Pro license.
- **Networked multi-machine sessions** are not available on non-Disguise hardware.

Licence activation, transfer and system requirements are in the user guide links below.

## Supported File Formats

**Video**: MOV, MP4, AVI, MXF, DPX, EXR, ProRes, DNxHD, HAP, HAP-Q, DXV

**Audio** (r14.4+): WAV, AIFF, MP3, OGG, FLAC, AAC, WMA
Audio embedded in video containers supported from r15.2.

**Still images**: JPEG, PNG, TIFF, EXR, DPX, BMP, GIF

**Image sequences**: DPX, EXR, JPEG, PNG sequences

**Alpha handling**: premultiplied vs. straight (matted) alpha behave differently during compositing — match the source file's alpha mode.

## Gotchas
- Director/Actor/Understudy roles are **hardware-gated**, not just license-gated — automating a multi-machine session requires Disguise hardware even with Pro license.
- Filename tags must be correctly formatted — malformed tags prevent media from loading.

## Basic Show Recipe (clean → screens → mapping → layers → capture)

End-to-end pattern for "set up a show with N screens, some content, and verify it
looks right." Shape this whole flow before improvising — most
show-building requests reduce to it. References for each step in parens.

```python
# 0. Register helpers (once per session). Verification uses the inline
#    internal_gui_capture MCP tool (step 5) — no capture dir needed. Only the
#    capture_stage() fallback writes PNGs, and then output_dir must be valid for
#    the d3 host (writer) AND visible to the agent host (reader).

# 1. Clear the blank-project defaults ("surface 1", "projector 1").
#    Use moveToTrash + emptyTrash — resourceManager.remove(path) does NOT delete.
#    Filter stage lists by reassignment; del stage.<list>[:] fails on Boundindexer.
markDirty(stage)
stage.surfaces   = [s for s in stage.surfaces   if s.path.filename != "surface 1"]
stage.projectors = [p for p in stage.projectors if p.path.filename != "projector 1"]
to_trash = [resourceManager.load(p) for p in (
    "objects/screen2/surface 1.apx", "objects/projector/projector 1.apx", ...)]
for r in to_trash: r.moveToTrash()
resourceManager.emptyTrash(to_trash)

# 2. Create N LedScreens. rename(scr.path) auto-adds them to stage.ledScreens AND
#    auto-creates a DirectProjection. You MUST set dp.mode=1 before dp.resolution or
#    it re-derives a huge canvas and can exhaust VRAM — see stage-projection.md DP warning.
scr = resourceManager.loadOrCreate("objects/ledscreen/center.apx", LedScreen)
scr.rename(scr.path)
scr.resolution = Vec2(3840, 2160); scr.scale = Vec(8.0, 4.5, 0.05)
scr.offset = Vec(0, 3.5, 5); scr.rotation = Vec(0, 0, 0)
dp = resourceManager.load("objects/directprojection/%s (direct).apx" % scr.path.filename, DirectProjection)
dp.mode = 1                                   # REQUIRED before setting resolution
dp.resolution = Vec2(2048, 1152); dp.save()   # aspect = screen; cap the long edge

# 3. Build a Parallel projection across all screens for cross-stage content.
#    compute_screen_bbox handles non-coplanar (toed-in) screens correctly.
pp = resourceManager.loadOrCreate("objects/parallel/all.apx", Parallel)
pp.screens = screens
pp.lock = 0
bbox = compute_screen_bbox(screens)
pp.size = Vec2(bbox["size"][0], bbox["size"][1])
pp.resolution = Vec2(4096, 1024)
pp.projectionObject.offset = Vec(*bbox["centre"])

# 4. Add layers. Order matters: bottom of track.layers = renders first.
#    Always introspect sequence names for unfamiliar modules (see layers-modules.md).
#    TextModule uses xPosition/yPosition (not pos.x/pos.y).
bg = track.addNewLayer(SockPuppetGradientModule, 0.0, length, "BG")
set_layer_values(bg, 0.0, mapping=pp, xCol=0.75, yCol=1.0, ...)
text = track.addNewLayer(TextModule, 0.0, length, "Title")
set_layer_values(text, 0.0, mapping=pp, fontSize=240.0, hAlignment=1.0, vAlignment=1.0,
                 xPosition=0.0, yPosition=0.0)
text.findSequence("text").sequence.setString(0, "TITLE")

# 5. Verify. Capture with the internal_gui_capture MCP tool — the image is
#    returned inline (no output dir, no file to Read):
#      mcp__d3service__internal_gui_capture { "width": 1920, "height": 1080 }
#    For a controlled overhead overview instead, use capture_stage() (fallback):
#    it writes a PNG to a writable output_dir you then Read. Editor display
#    labels ("center", "left", ...) only overlay localVisualiserCamera captures,
#    not the dedicated visualiser camera — don't mistake them for a broken layer.
```

Common mistakes this avoids: assuming `resourceManager.remove` deletes (it doesn't);
treating `stage.displays` as mutable (it's a read-only `Boundindexer`); guessing
TextModule sequence names; defaulting to a capture dir that isn't mounted.

## Imported model → mapped rig recipe (Blender/OBJ)

The common real job: someone hands you a model or reference and you need a mapped rig. **Order matters** — getting it wrong is the biggest time sink. Detail for each step is in `references/blender-meshes.md` and `references/stage-projection.md`.

1. Model in Blender: **+X audience-right, +Z up, audience at −Y**, real-world metres.
2. One object per LED region; **planar UVs** (blender-meshes.md §UV); normals facing −Y.
3. Export one OBJ per region **plus** one combined OBJ for scenic into `<project>/objects/Mesh/` (defaults `NEGATIVE_Z`/`Y`, `global_scale=1.0`, `export_triangulated_mesh=True`).
4. Per region in d3: `loadOrCreate` → `rename` → **assign `mesh`** → zero the transform (world-space-mesh pattern) → set `LedScreen.resolution` → **`dp.mode = 1`** → set `dp.resolution` → `save`.
5. **Audit total DP megapixels** (stage-projection.md DP warning) **before rendering anything.**
6. Scenic as a `Prop` in a `Venue` (`stage.venue` is `None` in a blank project — create it); set `renderSettings.displayMode = 1` and `renderSettings.diffuseMap`.
7. Add stock `man.obj` props as scale references — cheap, exposes scale errors instantly.
8. Build the track layers.
9. **Set up lights, ambient, area lighting and `stageRenderSettings`** (lighting-rendering.md) **before judging how it looks.** Flat/dull is almost always renderer defaults, not your model.
10. Verify: per-region `deferSaveScreenFrame` for UVs; `internal_gui_capture` (or the dedicated-camera fallback) for layout and occlusion.

Keep `LedScreen.resolution` at the true pixel pitch and cap the DP canvas.

## Userguide
- [Licensing overview & comparison](https://help.disguise.one/designer/getting-started/designer-licensing-comparison)
- [System requirements](https://help.disguise.one/designer/getting-started/system-requirements) · [Download & install](https://help.disguise.one/designer/getting-started/download-install) · [Supported formats](https://help.disguise.one/designer/getting-started/supported-file-formats)
- [License activation](https://help.disguise.one/designer/getting-started/license-activation) · [License transfer](https://help.disguise.one/designer/getting-started/designer-pro-license-transfer) · [Licensing FAQs](https://help.disguise.one/designer/getting-started/licensing-faqs)
- [Known issues](https://help.disguise.one/designer/getting-started/known-issues) · [Support tips](https://help.disguise.one/designer/getting-started/support-tips) · [Developer portal](https://help.disguise.one/designer/getting-started/developer-portal)
