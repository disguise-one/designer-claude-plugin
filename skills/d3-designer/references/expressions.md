# Expressions

## Key Classes
- `Expression` (`Resource`) -- Compiled expression attached to a field. Props: `expression` (str, rw), `isOK`, `error`, `isSelf`. Methods: `reset()`, `Expression.evaluateFromString(s)` (static), `Expression.cleanName(n)` (static).
- `FieldSequence` (`Resource`) -- Animatable layer property. Props: `expression` (Expression), `name`, `disableSequencing`, `sequence` (KeySequence), `layer`. Methods: `setExpression(expr)`, `eval(t, ttl)`, `notifyEdit()`.
- `ExpressionVariable` -- Typed variable value. Props: `name`, `type` (int), `defaultFloat`, `defaultString`, `errorText`. Methods: `makeExpression()` -> str.
- `ExpressionVariablesContainer` -- Holds list of variables. Props: `variables` (List[ExpressionVariable]).
- `ExpressionVariablesDevice` (`Device` > `Resource`) -- Device-scoped variable store. Props: `container` (ExpressionVariablesContainer).
- `ExpressionVariablesModule` (`Module` > `Resource`) -- Layer module that exposes variables on a track layer. Props: `fields` (List[ConnectedField]).

## Access
```python
# FieldSequence on a layer (iterate fields by name)
track = guisystem.track
layer = track.addNewLayer(VariableVideoModule, 0.0, 120.0, "MyLayer")
for field in layer.fields:
    if field.name == "brightness":
        seq = field
        break

# All ExpressionVariablesDevice resources
for dev in resourceManager.allResources(ExpressionVariablesDevice):
    print(dev.description, [v.name for v in dev.container.variables])

# Create or get a variable device
dev = resourceManager.loadOrCreate("objects/expressionvariablesdevice/my_vars.apx",
                                   ExpressionVariablesDevice)
```

## Setting Expressions on Layer Properties
```python
# Assuming field is a FieldSequence found via iteration above

# Simple expression
field.setExpression("0.5 + 0.5 * sin(time)")

# Link to another layer (no spaces in layer name)
field.setExpression("module:SourceLayerName.brightness * 0.5")

# Clear expression (revert to keyframe sequencing)
field.setExpression("")

# Read back
print(field.expression.expression)   # the raw expression string
print(field.expression.isOK)         # True if compiled without error
print(field.expression.error)        # error text if not OK
```

## ExpressionVariable API
```python
# Create a variable
markDirty(dev)
v = ExpressionVariable()
v.name = "myVar"
v.type = 0            # 0=float, 1=string
v.defaultFloat = 1.0
dev.container.variables.append(v)

# Get variable reference string for use in expressions
ref = v.makeExpression()            # returns variable name as string
field.setExpression(ref)            # variable reference in expression
```

## Expression Syntax Reference

### Literals & Operators
```
42  3.14  true  false  "text"
+  -  *  /                    # arithmetic
==  !=  <  >  <=  >=          # comparison
and  or  not                  # logical
[]                            # index operator
```

### Built-in Functions
```
# Logic
if(cond, thenVal, elseVal)
and(a, b)   or(a, b)   step(x)

# Math
sin(x)  cos(x)  tan(x)  asin(x)  acos(x)  atan(x)  atan2(y, x)
abs(x)  floor(x)  ceil(x)  round(x)  sqrt(x)  pow(x, n)  log(x)  exp(x)
min(a, b)  max(a, b)  clamp(x, lo, hi)  lerp(a, b, t)  mod(x, y)

# String manipulation
split(text, delim)  replace(text, old, new)  strip(text)
title(text)  upper(text)  lower(text)
```

### Common Datatypes
```
# Colour
Colour.mix(other, ratio)       # blend two colours
ColourFromHSL(h, s, l)

# Vectors
Vec2(x, y)   Vec3(x, y, z)   Vec4(x, y, z, w)
v.dot(other)   v.abs()
v.minComponent   v.maxComponent
```

### Built-in Variables
```
time          # current playhead time in seconds
self          # the current layer (in layer expressions)
```

### Accessing Resources & Protocols
```
resource:ResourceName.fieldName   # by name
resource:#1234.fieldName          # by UID
module:LayerName.brightness       # cross-layer reference (no spaces in name)

osc:/address/path[index]          # OSC value; missing address -> 0
dmx:universeN.channel             # DMX channel value; missing universe -> 0
midi:deviceName.cc[n]             # MIDI CC
audio:channelN.frequency[band]    # Audio analysis frequency band
```

### Text Formatting
```
# Replacement fields in curly braces (Python-style format spec)
"Value: {:.2f}"            # float, 2 decimal places
"Hex: {:x}"                # hex
"Padded: {:>10}"           # right-align, width 10
```

## Static Evaluation & Name Utilities
```python
# Evaluate an expression outside a layer context
result = Expression.evaluateFromString("sin(0.5) * 2")   # -> float

# Sanitise a name for safe use in module: references
safe = Expression.cleanName("My Layer Name")  # removes spaces/special chars
```

## Gotchas
- Layer names with spaces cause syntax errors in `module:Name.prop` — use `Expression.cleanName()` or rename the layer.
- `expression.isSelf` is true when no real expression is set (field returns its own keyframe value).
- `ExpressionVariable.makeExpression()` returns the variable name as a plain string — use it directly in expressions.
- `FieldSequence.expression` is an `Expression` resource object, not a plain string — read the string via `.expression.expression`.
- Variable `type` int values: 0=float, 1=string (no named constants in Python API).
- r27.10 introduced backwards-incompatible changes to undefined-variable handling; projects from earlier releases may need expression updates.

## Userguide
- [Overview](https://help.disguise.one/designer/configuration/expressions/expressions-overview) · [Variables](https://help.disguise.one/designer/configuration/expressions/variables) · [Functions](https://help.disguise.one/designer/configuration/expressions/functions) · [Operators](https://help.disguise.one/designer/configuration/expressions/operators) · [Datatypes](https://help.disguise.one/designer/configuration/expressions/common-datatypes)
- [Resources](https://help.disguise.one/designer/configuration/expressions/accessing-resources) · [External protocols](https://help.disguise.one/designer/configuration/expressions/accessing-external-protocols) · [Text formatting](https://help.disguise.one/designer/configuration/expressions/text-formatting) · [String manipulation](https://help.disguise.one/designer/configuration/expressions/string-manipulation)
- [Layer expressions](https://help.disguise.one/designer/configuration/expressions/layer-expressions) · [Linking layers](https://help.disguise.one/designer/configuration/expressions/linking-layers) · [Backward compat (r27.10)](https://help.disguise.one/designer/configuration/expressions/backward-compatibility) · [Camera angle example](https://help.disguise.one/designer/configuration/expressions/examples/camera-angle-example) · [Python plugin guide](https://developer.disguise.one/plugins/guides/expressions)
