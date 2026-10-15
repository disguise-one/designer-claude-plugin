"""MCP helper functions for d3 Designer automation.

Register once per session via MCP:
    mcp__d3service__python_register_module(
        moduleName="mcp_helpers",
        contents=<file contents>)

Then call any function with a one-liner via MCP - `moduleName="mcp_helpers"`
runs the script inside this module's namespace, so functions are accessible by
bare name:
    mcp__d3service__python_execute(
        moduleName="mcp_helpers",
        script='return search_resources("keyword", [VideoClip])')
"""

from d3 import *


def search_resources(keyword, types=None):
    # type: (str, list[type] | None) -> dict
    """Search resources by keyword against path.

    search_resources("intro", [VideoClip])
    search_resources("test pattern", [VideoClip, DxTexture])
    search_resources("audio")  # searches default types

    Args:
        keyword (str): Space-separated words -- all must appear in the resource path.
        types (list[type]): d3 type objects, e.g. [VideoClip], [DxTexture].
            Defaults to [VideoClip, AudioTrack, DxTexture].

    Returns:
        dict: {"matches": [...]}. The list is empty when nothing matches.
            Each entry: {"path": "<resource path>", "type": "<class name>"}

    Raises:
        ValueError: if keyword has no words.
    """
    words = keyword.lower().split()
    if not words:
        raise ValueError("keyword must contain at least one word")

    if types is None:
        types = [VideoClip, AudioTrack, DxTexture]
    elif not isinstance(types, list):
        types = [types]

    matches = []
    for rtype in types:
        type_name = rtype.__name__
        for r in resourceManager.allResources(rtype):
            path = str(r.path).lower() if r.path else ""
            if all(w in path for w in words):
                matches.append({"path": str(r.path), "type": type_name})

    return {"matches": matches}


def compute_screen_bbox(screens):
    # type: (list) -> dict
    """World-space axis-aligned bounding box of a list of Displays.

    Uses mesh.extent * scale for physical size (handles both unit meshes
    and pre-sized user meshes), then rotates corners through each screen's
    Y rotation and translates by offset.

    Returns dict with:
        min: [x, y, z], max: [x, y, z],
        size: [x_extent, y_extent] (for Parallel.size),
        centre: [cx, cy, cz] (for projectionObject.offset)
    """
    import math
    all_x, all_y, all_z = [], [], []
    for scr in screens:
        ext = scr.mesh.extent
        ext_min, ext_max = ext[0], ext[1]
        hw_x = (ext_max.x - ext_min.x) * scr.scale.x / 2.0
        hw_y = (ext_max.y - ext_min.y) * scr.scale.y / 2.0
        theta = math.radians(scr.rotation.y)
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)
        for sx in (-1, 1):
            for sy in (-1, 1):
                lx = sx * hw_x
                ly = sy * hw_y
                all_x.append(scr.offset.x + lx * cos_t)
                all_y.append(scr.offset.y + ly)
                all_z.append(scr.offset.z - lx * sin_t)
    mn = [min(all_x), min(all_y), min(all_z)]
    mx = [max(all_x), max(all_y), max(all_z)]
    return {
        "min": mn,
        "max": mx,
        "size": [mx[0] - mn[0], mx[1] - mn[1]],
        "centre": [(mn[0]+mx[0])/2.0, (mn[1]+mx[1])/2.0, (mn[2]+mx[2])/2.0],
    }


def set_layer_values(layer, beat, **kwargs):
    # type: (Layer, float, ...) -> None
    """Set sequence values on a layer. Float values use setFloat, Resources use setResource.

    set_layer_values(layer, 0.0, speed=80.0, beamSize=180.0, mapping=dp)
    """
    for name, val in kwargs.items():
        fseq = layer.findSequence(name)
        if isinstance(val, Resource):
            fseq.sequence.setResource(beat, val)
        else:
            fseq.sequence.setFloat(beat, val)


def _lookat_rotation(eye, target):
    """Compute camera rotation Vec to look from eye toward target.

    Camera view matrix = inverse(worldTransform), so world rotation
    is negated in the rendered output. This function accounts for that.
    d3 coordinate system: +X right, +Y up, +Z into stage.
    Default camera faces +Z with no rotation.
    """
    import math
    dx = target.x - eye.x
    dy = target.y - eye.y
    dz = target.z - eye.z
    dist_xz = math.sqrt(dx * dx + dz * dz)
    pitch = math.degrees(math.atan2(dy, dist_xz))
    yaw = math.degrees(math.atan2(dx, dz))
    return Vec(pitch, yaw, 0.0)


def _is_content_display(d):
    """True for display objects that count as visible show content (LED screens,
    projectors, surfaces, DMX screens). Filters out cameras and editor helpers
    living under internal/* paths."""
    if isinstance(d, Camera):
        return False
    path = str(d.path) if d.path else ""
    if path.startswith("internal/"):
        return False
    return True


MCP_CAMERA_PATH = "objects/camera/mcp_visualiser.apx"


def get_visualiser_camera():
    # type: () -> Camera
    """Return (or create) the dedicated `mcp_visualiser` Camera on the stage.

    This is a separate Camera resource from `Camera.localVisualiserCamera()` -
    using a dedicated camera means `capture_stage()` can be repositioned freely
    WITHOUT snapping the user's editor stage view. The camera is added to
    `stage.cameras` once; subsequent calls return the existing one.
    """
    cam = resourceManager.loadOrCreate(MCP_CAMERA_PATH, Camera)
    if cam.path.filename == "mcp_visualiser":
        cam.rename(cam.path)
    stage = state.stage
    if cam not in list(stage.cameras):
        markDirty(stage)
        stage.cameras.append(cam)
    return cam


def capture_stage(output_dir=None, width=1280, height=720, fov=60.0,
                   eye=None, target=None, auto_position=True):
    # type: (str, int, int, float, tuple, tuple, bool) -> dict
    """Capture a frame from a dedicated `mcp_visualiser` Camera on the stage.

    A separate camera (created on first call) means we can reposition for the
    capture WITHOUT touching the user's editor stage view.
    `Camera.localVisualiserCamera()` is the editor preview camera - driving
    that one would visibly snap the user's view, which is why this helper
    deliberately uses its own camera.

    With auto_position=True (default), the camera is moved above and in front
    of all on-stage content displays so the resulting PNG is a third-person
    overview. With explicit eye and/or target tuples, uses those instead;
    auto_position is ignored when either is given.

    Args:
        output_dir: absolute path for output PNGs (must exist or be creatable).
        width, height: capture resolution.
        fov: horizontal field of view in degrees.
        eye: camera position as (x, y, z). None = auto-compute (when
            auto_position=True) or leave the camera in its current pose
            (when False).
        target: look-at point as (x, y, z). None = centroid of all content
            displays (when repositioning) or leave alone.
        auto_position: when True and no explicit eye/target, recompute an
            overhead overview pose. When False, capture from the camera's
            current pose unchanged.
    """
    if output_dir is None:
        raise ValueError(
            "output_dir is required. Pick a path that is (a) writable by the d3 "
            "host and (b) visible to the agent host that will Read the PNG. On a "
            "single machine these are the same path; in split-host setups the "
            "directory must exist in both views."
        )

    cam = get_visualiser_camera()
    cam.resolution = Vec2(width, height)
    cam.fieldOfViewH = fov
    cam.zNear = 0.1
    cam.zFar = 200.0

    displays = [d for d in state.stage.displays if _is_content_display(d)]
    reposition = (eye is not None) or (target is not None) or auto_position

    if reposition:
        if not displays:
            return {"error": "No content displays on stage to frame"}

        xs, ys, zs = [], [], []
        for d in displays:
            xs.append(d.offset.x)
            ys.append(d.offset.y)
            zs.append(d.offset.z)

        cx = sum(xs) / len(xs)
        cy = sum(ys) / len(ys)
        cz = sum(zs) / len(zs)

        if target is not None:
            target_pos = Vec(target[0], target[1], target[2])
        else:
            target_pos = Vec(cx, cy, cz)

        if eye is not None:
            cam_pos = Vec(eye[0], eye[1], eye[2])
        else:
            x_spread = max(xs) - min(xs) + 6.0
            y_spread = max(ys) - min(ys) + 4.0
            extent = max(x_spread, y_spread)
            cam_dist = max(extent * 1.2, 8.0)
            cam_height = cy + cam_dist * 0.5
            cam_pos = Vec(cx, cam_height, cz - cam_dist)

        cam.offset = cam_pos
        cam.rotation = _lookat_rotation(cam_pos, target_pos)
    else:
        cam_pos = cam.offset
        target_pos = None

    sfs = subsystems.getSystem(SaveFrameSystem)
    sfs.deferSaveScreenFrame(cam, 0, output_dir)

    result = {
        "status": "capture_deferred",
        "output_dir": output_dir,
        "resolution": "%dx%d" % (width, height),
        "camera": "mcp_visualiser",
        "eye": [cam_pos.x, cam_pos.y, cam_pos.z],
    }
    if target_pos is not None:
        result["target"] = [target_pos.x, target_pos.y, target_pos.z]
    return result


# ---------------------------------------------------------------------------
# Lineup track - per-screen test pattern validation
# ---------------------------------------------------------------------------

LINEUP_TRACK_NAME = "mcp_lineup"
LINEUP_TRACK_PATH = "objects/track/%s.apx" % LINEUP_TRACK_NAME
LINEUP_CHECKOUT_BEAT = 30.0
LINEUP_TRACK_LENGTH = 60.0

_LINEUP_COLOURS = [
    (0.0, 0.8),    # red
    (0.08, 0.8),   # orange
    (0.16, 0.8),   # yellow
    (0.33, 0.8),   # green
    (0.5, 0.8),    # cyan
    (0.58, 0.8),   # sky blue
    (0.66, 0.8),   # blue
    (0.75, 0.8),   # purple
    (0.83, 0.8),   # magenta
    (0.91, 0.8),   # pink
    (0.0, 0.4),    # desaturated red
    (0.33, 0.4),   # desaturated green
]


def create_lineup_track():
    # type: () -> dict
    """Create a lineup track with per-screen test patterns.

    Auto-discovers displays, creates a DirectProjection + TestPatternModule layer
    per screen in section 0, each tinted a different colour. Section 1 (beat 30+)
    is empty, reserved for checkout_mapping().

    Returns:
        dict: {"track": "mcp_lineup", "screens": [{"name": ..., "colour": [x, y]}],
               "checkout_beat": 30.0}
    """
    track = resourceManager.loadOrCreate(LINEUP_TRACK_PATH, Track)
    markDirty(track)
    track.lengthInBeats = LINEUP_TRACK_LENGTH
    track.bpm = 120.0

    for layer in list(track.layers):
        track.removeLayer(layer)

    displays = [d for d in state.stage.displays if _is_content_display(d)]
    if not displays:
        return {"error": "No content displays on stage", "track": LINEUP_TRACK_NAME}

    screens = []
    for i, display in enumerate(displays):
        colour = _LINEUP_COLOURS[i % len(_LINEUP_COLOURS)]
        disp_name = display.description
        safe_name = disp_name.lower().replace(" ", "_")

        dp_path = "objects/directprojection/mcp_lineup_%s.apx" % safe_name
        dp = resourceManager.loadOrCreate(dp_path, DirectProjection)
        dp.screens = [display]
        dp.resolution = display.resolution

        layer_name = "Lineup: %s" % disp_name
        layer = track.addNewLayer(TestPatternModule, 0.0, LINEUP_CHECKOUT_BEAT, layer_name)
        set_layer_values(layer, 0.0, mapping=dp, xCol=colour[0], yCol=colour[1],
                         gridMode=1, label=1)

        screens.append({"name": disp_name, "colour": list(colour)})

    track.splitSectionAtBeat(LINEUP_CHECKOUT_BEAT)

    tm = guisystem.currentTransportManager
    if tm and tm.setList and not tm.setList.containsTrack(track):
        markDirty(tm.setList)
        tm.setList.tracks.append(track)

    track.saveOnDelete()

    return {
        "track": LINEUP_TRACK_NAME,
        "screens": screens,
        "checkout_beat": LINEUP_CHECKOUT_BEAT,
    }


def cleanup_checkout():
    # type: () -> dict
    """Remove all checkout layers from the lineup track's section 1.

    Returns:
        dict: {"removed": int}
    """
    track = resourceManager.load(LINEUP_TRACK_PATH, Track)
    if not track:
        return {"error": "Lineup track not found"}

    markDirty(track)
    removed = 0
    for layer in list(track.layers):
        if layer.tStart >= LINEUP_CHECKOUT_BEAT:
            track.removeLayer(layer)
            removed += 1

    return {"removed": removed}


def checkout_mapping(projection_path, colour=None):
    # type: (str, tuple) -> dict
    """Check out a mapping by showing it on the lineup checkout section.

    Creates a temporary TestPatternModule layer in section 1 (beat 30+),
    assigns the given projection, and jumps to beat 30. Previous checkout
    layers are cleaned up first. The caller must ensure the transport is
    already on the lineup track (use REST gototrack) and should call
    capture_stage() separately after a short sleep to capture the frame.

    Args:
        projection_path: resource path of the Projection to verify
            (e.g. "objects/directprojection/centre.apx")
        colour: optional (x, y) tuple for tint hue/saturation. Random if None.

    Returns:
        dict: {"status": "ready", "projection": ..., "colour": ..., "beat": ...}
    """
    import random

    track = resourceManager.load(LINEUP_TRACK_PATH, Track)
    if not track:
        return {"error": "Lineup track not found. Call create_lineup_track() first."}

    projection = resourceManager.load(projection_path, Projection)
    if not projection:
        return {"error": "Projection not found: %s" % projection_path}

    cleanup_checkout()

    if colour is None:
        colour = (random.random(), 0.7 + random.random() * 0.3)

    duration = LINEUP_TRACK_LENGTH - LINEUP_CHECKOUT_BEAT
    layer = track.addNewLayer(
        TestPatternModule, LINEUP_CHECKOUT_BEAT, duration, "Checkout"
    )
    set_layer_values(layer, LINEUP_CHECKOUT_BEAT, mapping=projection,
                     xCol=colour[0], yCol=colour[1], gridMode=1, label=1)

    track.saveOnDelete()

    tm = guisystem.currentTransportManager
    tm.addCommand(TransportCommand.makeJumpToBeat(state, tm, LINEUP_CHECKOUT_BEAT))

    return {
        "status": "ready",
        "projection": projection_path,
        "colour": list(colour),
        "beat": LINEUP_CHECKOUT_BEAT,
    }

