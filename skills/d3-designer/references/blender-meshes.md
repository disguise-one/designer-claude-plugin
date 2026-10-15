# Authoring meshes for d3 in Blender

For the common real job: someone hands you a model or reference and you need a mapped LED rig + scenic props. The steps use the OBJ format, which Blender and Designer both support.

## Blender → OBJ → d3 axis mapping (state it once, don't rediscover)

With Blender's OBJ export defaults **`forward_axis='NEGATIVE_Z'`, `up_axis='Y'`**:

```
d3 X (stage width)  =  Blender X
d3 Y (up)           =  Blender Z
d3 Z (upstage, +)   =  Blender Y
```

Verified three ways: a panel at Blender `y=+6` reported `extent.z=+6` in d3; `y=-2` → `-2`; a 260 m deck spanning Blender `y −82.5…+32.5` reported `z −82.5…+32.5`. **d3 negates the OBJ file's raw Z on import** (the file held `z=-6` for the `+6` case) — so **do not reason from the raw `.obj` text**, reason from `mesh.extent` in d3.

Consequences:
- **Build with the audience at Blender −Y.** Panel normals facing −Y then face the audience (d3 −Z) and render with `content = 0`.
- The conversion is a proper rotation (det = +1) → **winding and normals are preserved**.
- **Audience-right is +X.** (From a camera at −Y looking toward +Y with +Z up, screen-right = `forward × up` = +X.) Getting this backwards mirrors every UV.

### World-space-mesh pattern (recommended default)

Export every LED region **in world coordinates** and leave every screen at identity — this removes a whole class of placement bugs and makes `mesh.extent` directly comparable to the design drawing:

```python
scr.offset   = Vec(0.0, 0.0, 0.0)
scr.rotation = Vec(0.0, 0.0, 0.0)
scr.scale    = Vec(1.0, 1.0, 1.0)
```

Prefer this over per-screen transforms (`mesh.extent * scale`) for multi-region rigs.

## UV authoring for LED regions

- Author **planar UVs** per region: `u` increases with world **+X**, `v` with world **+Y (up)**, normalised to the region's bounding box. Arched/sculptural regions leave the corners of UV space unused — that's correct (a rectangular canvas feeding a shaped screen).
- **Verify with a capture, not by reasoning** — the fastest check in the toolkit:
  ```python
  sfs = subsystems.getSystem(SaveFrameSystem)
  sfs.deferSaveScreenFrame(scr, 0, "<capture folder>")   # writes at the LedScreen's resolution
  ```
  A `TestPatternModule` with `label = 1` puts legible text + the disguise logo on the screen. One look shows whether `u` is mirrored, `v` flipped, and whether the aspect is right (are the circles circular?).
- **Cheapest fix for an inverted map — no re-export:** `flip_U`, `flip_V`, `swap_U_V` (on the imported OBJ mesh — the `MeshFromObj` subclass you get from loading an `.obj`; verified in d3.pyi). `useFileNormals` (also on `MeshFromObj`) + `updateMesh()` forces a normal recompute.

## Baking a scenic diffuse map (previz)

**Light the Blender scene and bake the lighting in.** An albedo-only bake (`DIFFUSE`, `pass_filter={'COLOR'}`) × AO looks flat and no amount of Designer lighting fixes it — AO only darkens crevices; there's no key light, form, or cast shadow.

**Recipe that worked** — three passes composited in numpy:
```python
# 0) Light the scene: sky world (Sky Texture; Nishita may fall back to Preetham in 5.2 —
#    check sky.sky_type after setting) + a warm SUN (~4 W/m^2, low elevation) + a large
#    cool AREA fill from front + a warm AREA bounce off the deck.
# 1) albedo  : bake DIFFUSE, pass_filter={'COLOR'}                 (1 sample)
# 2) shading : bake DIFFUSE, pass_filter={'DIRECT','INDIRECT'}     (~24 samples)
#              -> irradiance WITHOUT albedo: near-greyscale, so it can be blurred to kill
#                 sampling noise without smearing colour
# 3) ao      : bake AO                                             (~24 samples)
shading = box_blur(shading, 2)
sh  = clip(shading / 0.95, 0, 1.7)
aos = 0.74 + 0.26 * clip(ao, 0, 1)
out = albedo * (0.26 + 0.88 * sh) * aos
# then chroma boost about luminance, gamma, exposure lift to taste
```
That took tonal range from ~none to p05 `0.07` / p50 `0.44` / p95 `0.85`.

**Three traps that cost real time:**
- **UV packing bleed.** `smart_project` fragments dense/curved meshes into thousands of tiny islands; gaps bake black → dark speckling. Fix:
  ```python
  bpy.ops.uv.smart_project(angle_limit=radians(70), island_margin=0.0,
                           area_weight=0.0, correct_aspect=True)
  bpy.ops.uv.average_islands_scale()
  bpy.ops.uv.pack_islands(margin=0.0016, rotate=True)
  scene.render.bake.margin_type = 'ADJACENT_FACES'
  scene.render.bake.margin = 16
  # then a numpy dilation pass over remaining near-black pixels (14% -> 0.1% of atlas)
  ```
- **Double gamma.** Pixels written with `img.pixels.foreach_set(...)` are treated as **already sRGB** on PNG save. Do **not** apply a `** 2.2` sRGB→linear first — write sRGB fractions directly, or everything comes out dark and over-saturated.
- **Subdivision compounds.** `SUBSURF`+`DISPLACE` on already-subdivided meshes went 174 k → **4 M verts**. Rebuild from clean primitives; pick subdivision from each object's dimensions (target ~2 m cells), not a fixed level.

Also: **reuse the AO pass** when only material colours change (UVs unchanged → AO still valid; ~40 s/iteration saved).

## Blender-MCP interop notes

- `render_thumbnail_to_path` returns a path under the add-on's **temp** dir (outside the agent's readable folders). Instead set `scene.render.filepath = <mounted path>` + `bpy.ops.render.render(write_still=True)`.
- `execute_blender_code` **times out ~60 s while the code keeps running** — poll for the artefact rather than re-running (a re-run of a non-idempotent build is worse than a wait).
- **Respect the user's scene:** build in new collections; stash/restore `scene.camera`, `render.engine`, `resolution_*`, `render.filepath`, the world, and any light's `hide_render` around a bake. The user often has a live scene open.
- `mesh.uv_layers.active` can be `None` on a freshly joined mesh even when `uv_layers` is non-empty — always `get("UVMap") or new(...)` **and** assign `.active`.
- **Do not** edit topology via `bpy.ops.mesh.delete` driven by polygon `.select` flags set in object mode — it silently deleted **all** geometry. Use explicit vertex/face reconstruction or bmesh.
