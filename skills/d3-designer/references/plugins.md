# Designer Plugins

## Overview

Plugins are HTML/JavaScript frontends rendered in Designer's embedded Chromium (CEF) browser. They communicate with Designer via the Python Execution API over HTTP. Two types exist:

- **Local** -- placed in `{project_root}/plugins/{name}/` or `common/plugins/{name}/`; distributed with the project
- **Remote** -- hosted on network devices; discovered via DNS-SD (`_d3plugin._tcp.local.`)

## File Structure

```
{project_root}/plugins/{plugin_name}/
    index.html          # entry point (required)
    d3plugin.json       # metadata (optional)
    index.js            # supporting scripts
```

## Metadata: d3plugin.json

```json
{
    "name": "My Plugin",
    "url": "http://custom-host/index.html",
    "requiresSession": true
}
```

All fields are optional. `requiresSession: true` means Designer must be running a session.

## Window Size (HTML meta tags)

```html
<meta name="disguise-plugin-window-size"      content="512,512">
<meta name="disguise-plugin-window-min-size"  content="200,200">
<meta name="disguise-plugin-window-resizable" content="true">
```

## Python Execution API

### Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/session/python/execute` | POST | Run a Python 2.7 script in the current session |
| `/api/session/python/registermodule` | POST | Register a reusable named module |

### Execute Request / Response

```json
{ "moduleName": "my_plugin", "script": "return resourceManager.allResources(Track)" }
```

Response fields: `d3Log` (console output), `pythonLog` (Python stdout), serialized return value as JSON.

### JavaScript: Calling the API

```javascript
var urlParams = new URLSearchParams(window.location.search);
var director  = urlParams.get('director') || 'localhost';
var apiUrl    = 'http://' + director + '/api/session/python/execute';

function runPython(script) {
    return fetch(apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ script: script })
    }).then(function(r) { return r.json(); });
}
```

### Register Module

```json
{ "moduleName": "my_utils", "contents": "def helper():\n    return guisystem.track.description" }
```

Modules auto-load from `{project_root}/plugins` on startup. Internally prefixed `user_module_`. Cross-module import: `import user_module_my_utils`. Module names: alphanumeric, dots, hyphens, underscores only.

## Python Execution Environment

- **Python 2.7** -- no f-strings, print is a statement, `/` is integer division
- Scripts wrapped in `userScript()`; error line numbers are offset ~10 from reported value
- No state persists between `execute` calls -- each call is isolated
- Runs on Designer's **main thread**; subject to timeout via `pythonApiExecutionTimeout`
- **Unavailable**: `threading`, `sys` modules; `from pkg import *` syntax

### Available Globals (module-less execute)

```python
guisystem        # GUI system: guisystem.track, guisystem.currentTransportManager
state            # current Designer state (stage, devices) -- REQUIRED as TransportCommand source
d3               # global Designer application object
resourceManager  # resource loading and management
subsystems       # subsystem access
d3NetManager     # network manager
paths            # file/path helpers
colours          # colour constants
undo             # undo system
Resource         # base resource class

trackTime()      # current track position in seconds (utility fn)
runningTime()    # application uptime in seconds (utility fn)
```

## Common Python Snippets

```python
# Add a video layer at current time
guisystem.track.addNewLayer(VariableVideoModule, trackTime(), 60, 'Video')

# Split section at current time
guisystem.track.splitSectionAtBeat(trackTime())

# Load or create a projector (resource paths are lowercase with .apx extension)
proj = resourceManager.loadOrCreate('objects/projector/myprojector.apx', Projector)
proj.resolution = Vec2(3840, 2160)

# Enumerate all resources of a type
devices = resourceManager.allResources(OscDevice)

# Modify an expression variable
evd_list = resourceManager.allResources(ExpressionVariablesDevice)
if evd_list:
    evd = evd_list[0]
    container = evd.container
    for var in container.variables:
        if var.name == 'speed':
            var.defaultFloat = 0.5
```

## Project & Session Discovery

```python
# Check session status
# GET http://localhost/api/session/status/session
# Returns: { "running": bool, "directorHostname": str }

# Discover d3 machines via DNS-SD
# _d3api._tcp.local.       -- any d3 machine
# _d3director._tcp.local.  -- director in a session

# List projects on a machine
# GET http://{ip}:{port}/api/service/system/projects
# Returns: [{ "path": str, "modified": str, "d3Version": str }]

# Access project files
# UNC:   \\{machine}\d3 Projects\{project_path}
# rsync: rsync://{machine}:{port}/d3projects/{project_path}
```

## Remote Plugin DNS-SD Registration

Remote plugins register via DNS-SD TXT records:

| TXT Key | Purpose | Required |
|---|---|---|
| `t` | Must be `"web"` | Yes |
| `u` | Web resource URL | No |
| `s` | `"true"` if session required | No |

Service name pattern: `<instance>._d3plugin._tcp.local.`

Official Python library for auto-registration: [disguise-one/python-plugin](https://github.com/disguise-one/python-plugin).

## Stylesheet / CSS

Designer enforces dark mode in the plugin host. Use CSS variables and media queries for consistency:

```css
:root { --bg: #1a1a1a; --text: #ffffff; }

/* Transparent overlay blends with Designer's UI chrome */
body { background-color: rgba(0, 0, 0, 0); }

/* Optional light theme support */
@media (prefers-color-scheme: light) {
    :root { --bg: #ffffff; --text: #000000; }
}
```

## CEF Constraints

- HTTP only (not HTTPS) for local plugins -- blocks WebUSB, WebBluetooth, service workers, some clipboard APIs
- WebGL is **disabled by default** -- enable per-project via Advanced Project Settings > `enableWebGL`
- Vue.js, React and other JS frameworks are supported

## Gotchas

- `execute` has **no persistent state** between calls -- use `registermodule` for shared helpers/state
- `director` hostname comes from URL query string `?director=hostname`; defaults to `localhost` (solo mode)
- Error line numbers in tracebacks are offset ~10 due to script wrapping in `userScript()`
- Local plugins take precedence over common plugins when names conflict
- `from package import *` is explicitly blocked by the execution environment
- Do **not** poll `/execute` -- it is not designed for frame-rate queries; use WebSockets or SSE instead
- WebGL must be enabled per-project, not per-plugin

## Userguide

- [Plugin Introduction](https://developer.disguise.one/plugins/introduction) | [Getting Started](https://developer.disguise.one/plugins/getting-started) | [Architecture](https://developer.disguise.one/plugins/architecture)
- [Python Execution API](https://developer.disguise.one/plugins/python-execution-api) | [Python Environment](https://developer.disguise.one/plugins/python-environment)
- [Metadata](https://developer.disguise.one/plugins/metadata) | [Discovery](https://developer.disguise.one/plugins/discovery) | [Distribution](https://developer.disguise.one/plugins/distribution)
- [Useful Python Strings](https://developer.disguise.one/plugins/useful-python-strings) | [d3projects Access](https://developer.disguise.one/plugins/d3projects-access)
- [API Docs Index](https://developer.disguise.one/plugins/docs) | [Stylesheet](https://developer.disguise.one/plugins/stylesheet) | [Useful Links](https://developer.disguise.one/plugins/useful-links)
- [Designer Plugin Overview](https://help.disguise.one/designer/plugins/designer-plugin-overview) | [Chromium Web Integration](https://help.disguise.one/designer/plugins/chromium-web-integration)
- [GitHub: python-plugin](https://github.com/disguise-one/python-plugin) | [GitHub: designer-pythonapi](https://github.com/disguise-one/designer-pythonapi) | [GitHub: vue-liveupdate](https://github.com/disguise-one/vue-liveupdate)
