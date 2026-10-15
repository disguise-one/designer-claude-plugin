# Visual Verification

Do this for any change to stage layout, projection mapping, or display geometry. Capture the result and look at it before you say the task is complete.

## Contents

- Default capture: `internal_gui_capture`
- When the capture times out
- Controlled overview pose (fallback)
- Capture through Python only
- Post-build checklist

## Default capture: `internal_gui_capture`

The `internal_gui_capture` tool captures the current GUI feed/space view. It returns the image *inline* in the tool result. It needs no output folder, shared drive, or file polling, and no file read.

```
internal_gui_capture   { "width": 1920, "height": 1080 }                    # feed/space only
internal_gui_capture   { "width": 1920, "height": 1080, "widgets": true }   # include GUI widgets
```

Look at the returned image. Look for: gaps between screens, wrong angles, objects in unexpected positions, missing elements. If something looks wrong, find the cause before you change anything:

- Read `object.world` to check the actual transform.
- Find out if the problem is position OR rotation (not both).
- Change one variable at a time.

Do not present a flawed result as complete. Do not play the timeline. Content is visible at beat 0.

**When text or bitmaps look the wrong size or in the wrong place on a wall that otherwise renders:** check that the DirectProjection resolution matches the screen resolution. Auto-created DPs have an inconsistent default (256x256, 16384x1393, and others). Pixel-space layer values (`fontSize`, `xPosition`/`yPosition`, bitmap scale) use the DP canvas, not the screen. A mismatch halves font sizes or squashes vertical positions without any error. See the LedScreen section in `references/stage-projection.md` for the fix.

## When the capture times out

`internal_gui_capture` can fail with HTTP 500 `Capture timed out` when d3 is not the foreground window. This is common during agent-driven work. The sign is `status_list_health` with Framelock = `"Not foreground window"`.

The cause: the render loop does the capture, and the loop waits for the frame present. When d3 is not in the foreground, the present is slow. The frame that makes the capture does not arrive within the short synchronous wait of `internal_gui_capture` (about 6 seconds). The Framelock text only shows the state. It does not block the capture.

When this happens, use the dedicated-camera `deferSaveScreenFrame` fallback below. It works in the same slow loop because it is asynchronous: you defer the save and poll for the file (about 8 to 10 seconds). It also renders through the camera's `stageRenderSettings`, so it uses `renderer`, `exposure` and SSAO. It is a full equivalent.

## Controlled overview pose (fallback)

`internal_gui_capture` shows the view that the editor shows now. You cannot set an angle with it. When you need a specific third-person overview (for example an overhead view, about 25 degrees down, that shows Z-depth errors) and you must not move the user's editor view, use the dedicated-camera capture. It writes a PNG that you then read.

```bash
# Auto overhead overview (puts the dedicated visualiser camera above and in front of all displays)
pwsh -File scripts/d3-capture-frame.ps1 [-Width 1280] [-Height 720]

# Per-mapping isolation (only when the overview is unclear)
pwsh -File scripts/d3-capture-lineup.ps1 \
  -Mappings '{"mappings": [{"name": "Centre", "path": "objects/directprojection/centre.apx"}]}'
```

Both scripts accept `-OutputDir`. The default is a `d3-captures` folder in the temp folder. A different folder must be writable by the d3 host and readable by the script.

The scripts drive a dedicated `mcp_visualiser` Camera. The camera is created when needed, added to `stage.cameras`. Remove it when the task is done, if the task made it. They never use `Camera.localVisualiserCamera()`. That camera is the editor preview camera, and using it would move the user's view.

## Capture through Python only

If you cannot run PowerShell, run the capture with `python_execute` (through the d3 API gateway - never use the internal d3service port directly):

1. Register `mcp_helpers`, then call `capture_stage(output_dir=...)`. You can also call `SaveFrameSystem.deferSaveScreenFrame(cam, 0, dir)` directly. This only **defers** the save. The render loop writes the PNG one or more frames later. **Wait about 8 to 10 seconds before you look for the file.**
2. Find the file: list the folder and take the **newest** entry. Do not hard-code the name. The pattern is `screen_<camera name> <hostname>_%05d.png`. The counter increases on every capture.
3. `output_dir` must be writable by the d3 host and readable by the agent. Use a folder that both can see. If the agent and d3 run on different machines, use a shared or mounted folder.
4. Read the newest PNG. The dedicated camera renders cleanly. `localVisualiserCamera` draws editor-only display labels ("center", "left", and others) that are not in the real output. Do not mistake them for content. If a screen looks blank, check the content brightness before you decide that a layer is broken.

## Post-build checklist

Run this after a stage build. Only a render and a look find these problems. Reasoning does not find them: mirrored UVs, screens hidden behind portal frames, screens buried inside scenery, a flat albedo-only bake.

1. **Front elevation** capture: layout, silhouette, proportion.
2. **Elevated 3/4** capture: Z-depth and occlusion. A flat front view hides both.
3. **Per-region `deferSaveScreenFrame`**: UV orientation and aspect (`TestPatternModule label=1`; see `references/blender-meshes.md`).
4. **DP megapixel audit** (`references/stage-projection.md`): do it before you render anything.
5. **`status_list_health` -> `averageFPS`** (not `d3.gpuLoad`).

**Before you decide that "d3 cannot do X" or "this is a d3 limitation", check the renderer and display-mode defaults first** (`stageRenderSettings.renderer`, `PropRenderer.displayMode`; see `references/lighting-rendering.md` and `references/stage-projection.md`). A dense mesh that shades black, or a scene that looks dull, is usually only a default setting.
