# Figma Plugin API Reference

## CRITICAL: Async API Required
```
ERROR: "Cannot call with documentAccess: dynamic-page. Use figma.getNodeByIdAsync instead."
CAUSE: Plugin uses dynamic-page documentAccess (default for dev plugins)
FIX: Always use async node lookup methods
```

## Sync→Async API Map
| WRONG (sync)                     | CORRECT (async)                              |
|----------------------------------|----------------------------------------------|
| `figma.getNodeById(id)`          | `await figma.getNodeByIdAsync(id)`           |
| `figma.getStyleById(id)`         | `await figma.getStyleByIdAsync(id)`          |
| `figma.getLocalPaintStyles()`    | `await figma.getLocalPaintStylesAsync()`     |
| `figma.getLocalTextStyles()`     | `await figma.getLocalTextStylesAsync()`      |
| `figma.getLocalEffectStyles()`   | `await figma.getLocalEffectStylesAsync()`    |
| `figma.getLocalGridStyles()`     | `await figma.getLocalGridStylesAsync()`      |
| `figma.getFileThumbnailNode()`   | `await figma.getFileThumbnailNodeAsync()`    |

**Note:** `findAll(predicate)` sync works. `getNodeById` does NOT.

---

## Plugin Location
```
C:\Users\Brian\AppData\Local\Figma\app-125.10.8\Claude_direct\code.js
```
Run: `Plugins → Development → Claude_direct`

---

## MCP Tools
```
mcp__figma__get_figma_data
  fileKey: string          // from figma.com/design/{fileKey}/...
  nodeId?: string          // "123:456" or "I123:456;789:012"

mcp__figma__download_figma_images
  fileKey: string
  nodes: [{ nodeId, fileName, imageRef? }]
  localPath: string
```

---

## Master Template
```javascript
(async () => {
  try {
    // NODE LOOKUP (async required)
    const node = await figma.getNodeByIdAsync("123:456");
    if (!node) { figma.notify("Not found"); figma.closePlugin(); return; }

    // MODIFICATIONS HERE

    figma.viewport.scrollAndZoomIntoView([node]);
    figma.notify("Done!");
  } catch (e) {
    figma.notify("Error: " + e.message);
    console.error(e);
  }
  figma.closePlugin();
})();
```

---

## CRITICAL: Font Discovery (Autonomous Design)

**Problem:** Font style names vary by system. "SemiBold" vs "Semi Bold" will error.

### Safe Font Loading Pattern
```javascript
// 1. Discover available styles for a font family
const allFonts = await figma.listAvailableFontsAsync();
const interStyles = allFonts
  .filter(f => f.fontName.family === "Inter")
  .map(f => f.fontName.style);
// Returns: ["Black", "Bold", "Extra Bold", "Light", "Medium", "Regular", "Semi Bold", "Thin", ...]

// 2. Safe load with fallback
async function loadFont(family, preferredStyle, fallbackStyle = "Regular") {
  const fonts = await figma.listAvailableFontsAsync();
  const available = fonts.filter(f => f.fontName.family === family).map(f => f.fontName.style);
  const style = available.includes(preferredStyle) ? preferredStyle : fallbackStyle;
  await figma.loadFontAsync({ family, style });
  return { family, style };
}

// Usage
const bold = await loadFont("Inter", "Semi Bold", "Bold");
text.fontName = bold;
```

### Common Font Style Names (with spaces!)
```
Inter:     "Thin", "Extra Light", "Light", "Regular", "Medium", "Semi Bold", "Bold", "Extra Bold", "Black"
Roboto:    "Thin", "Light", "Regular", "Medium", "Bold", "Black"
Open Sans: "Light", "Regular", "Semi Bold", "Bold", "Extra Bold"
```

### Pre-flight Font Check Template
```javascript
(async () => {
  try {
    // STEP 1: Discover fonts
    const fonts = await figma.listAvailableFontsAsync();
    const getStyles = (family) => fonts.filter(f => f.fontName.family === family).map(f => f.fontName.style);

    const interStyles = getStyles("Inter");
    const hasInterSemiBold = interStyles.includes("Semi Bold");
    const hasInterBold = interStyles.includes("Bold");

    // STEP 2: Load with correct names
    await figma.loadFontAsync({ family: "Inter", style: hasInterSemiBold ? "Semi Bold" : "Bold" });
    await figma.loadFontAsync({ family: "Inter", style: "Regular" });
    await figma.loadFontAsync({ family: "Inter", style: "Medium" });

    // STEP 3: Store for use
    const FONTS = {
      heading: { family: "Inter", style: hasInterSemiBold ? "Semi Bold" : "Bold" },
      body: { family: "Inter", style: "Regular" },
      label: { family: "Inter", style: "Medium" }
    };

    // Now use FONTS.heading, FONTS.body, etc.
    const text = figma.createText();
    text.fontName = FONTS.heading;
    text.characters = "Hello";

  } catch (e) {
    figma.notify("Error: " + e.message);
  }
  figma.closePlugin();
})();
```

### Font Discovery Diagnostic
```javascript
// Run this first to see available fonts
(async () => {
  const fonts = await figma.listAvailableFontsAsync();
  const families = [...new Set(fonts.map(f => f.fontName.family))].slice(0, 50);
  console.log("Font families:", families.join(", "));

  // Check specific family
  const inter = fonts.filter(f => f.fontName.family === "Inter");
  console.log("Inter styles:", inter.map(f => f.fontName.style).join(", "));
  figma.notify("Check console for fonts");
  figma.closePlugin();
})();
```

---

## figma Global Object

### Properties (readonly)
```javascript
figma.apiVersion        // '1.0.0'
figma.fileKey           // string | undefined
figma.command           // string
figma.pluginId          // string | undefined
figma.editorType        // 'figma' | 'figjam' | 'dev' | 'slides' | 'buzz'
figma.mode              // 'default' | 'textreview' | 'inspect' | 'codegen' | 'linkpreview' | 'auth'
figma.root              // DocumentNode
figma.currentUser       // User | null
figma.activeUsers       // ActiveUser[]
figma.hasMissingFont    // boolean
figma.mixed             // unique symbol (for mixed values)
```

### Properties (get/set)
```javascript
figma.currentPage                    // PageNode
figma.skipInvisibleInstanceChildren  // boolean
```

### Sub-APIs
```javascript
figma.ui           // UIAPI
figma.util         // UtilAPI
figma.constants    // ConstantsAPI
figma.timer        // TimerAPI
figma.viewport     // ViewportAPI
figma.clientStorage // ClientStorageAPI
figma.parameters   // ParametersAPI
figma.payments     // PaymentsAPI
figma.textreview   // TextReviewAPI
figma.variables    // VariablesAPI
figma.teamLibrary  // TeamLibraryAPI
figma.annotations  // AnnotationsAPI
figma.codegen      // CodegenAPI (Dev Mode)
figma.vscode       // VSCodeAPI (Dev Mode)
figma.devResources // DevResourcesAPI (Dev Mode)
```

---

## Node Lookup

### By ID (preferred)
```javascript
const node = await figma.getNodeByIdAsync("9:8");
```

### By Name
```javascript
const nodes = figma.currentPage.findAll(n => n.name === "Login Card");
```

### By Type
```javascript
const frames = figma.currentPage.findAll(n => n.type === "FRAME");
const texts = figma.currentPage.findAll(n => n.type === "TEXT");
```

### By Type (typed return)
```javascript
const texts = figma.currentPage.findAllWithCriteria({ types: ['TEXT'] }); // returns TextNode[]
```

### By Text Content
```javascript
const nodes = figma.currentPage.findAll(n => n.type === "TEXT" && n.characters === "Hello");
```

### Within Parent
```javascript
const parent = await figma.getNodeByIdAsync("9:8");
const children = parent.findAll(n => n.type === "TEXT");
```

### Single Match
```javascript
const node = figma.currentPage.findOne(n => n.name === "Button");
```

---

## All Node Types (37)
```
BOOLEAN_OPERATION    CODE_BLOCK          COMPONENT           COMPONENT_SET
CONNECTOR            DOCUMENT            ELLIPSE             EMBED
FRAME                GROUP               HIGHLIGHT           INSTANCE
INTERACTIVE_SLIDE_ELEMENT                LINE                LINK_UNFURL
MEDIA                PAGE                POLYGON             RECTANGLE
SECTION              SHAPE_WITH_TEXT     SLICE               SLIDE
SLIDE_GRID           SLIDE_ROW           STAMP               STAR
STICKY               TABLE               TABLE_CELL          TEXT
TEXT_PATH            TRANSFORM_GROUP     VECTOR              WASHI_TAPE
WIDGET
```

---

## Mixins (Shared Properties)

### BaseNodeMixin (all nodes)
```javascript
node.id              // readonly string "123:456"
node.name            // string
node.removed         // readonly boolean
node.remove()        // delete node
```

### SceneNodeMixin
```javascript
node.visible         // boolean
node.locked          // boolean
```

### LayoutMixin
```javascript
node.x               // number (relative to parent)
node.y               // number
node.width           // readonly number
node.height          // readonly number
node.rotation        // number (degrees)
node.absoluteTransform      // readonly Transform
node.absoluteBoundingBox    // readonly Rect | null
node.absoluteRenderBounds   // readonly Rect | null (includes effects)
node.relativeTransform      // Transform
node.resize(w, h)           // method
node.resizeWithoutConstraints(w, h)
node.rescale(scale)
```

### BlendMixin
```javascript
node.opacity         // number 0-1
node.blendMode       // BlendMode
node.isMask          // boolean
node.effects         // Effect[]
node.effectStyleId   // string
```

### GeometryMixin
```javascript
node.fills           // Paint[] | typeof figma.mixed
node.strokes         // Paint[]
node.strokeWeight    // number
node.strokeAlign     // "INSIDE" | "OUTSIDE" | "CENTER"
node.strokeCap       // "NONE" | "ROUND" | "SQUARE" | "ARROW_LINES" | "ARROW_EQUILATERAL"
node.strokeJoin      // "MITER" | "BEVEL" | "ROUND"
node.dashPattern     // number[]
node.fillStyleId     // string | typeof figma.mixed
node.strokeStyleId   // string
```

### CornerMixin
```javascript
node.cornerRadius    // number | typeof figma.mixed
node.cornerSmoothing // number 0-1
```

### RectangleCornerMixin
```javascript
node.topLeftRadius       // number
node.topRightRadius      // number
node.bottomLeftRadius    // number
node.bottomRightRadius   // number
```

### ChildrenMixin
```javascript
node.children        // readonly SceneNode[]
node.appendChild(child)
node.insertChild(index, child)
node.findAll(callback)
node.findOne(callback)
node.findAllWithCriteria({ types: [] })
node.findChild(callback)
node.findChildren(callback)
```

### FramePrototypingMixin
```javascript
node.overflowDirection    // "NONE" | "HORIZONTAL" | "VERTICAL" | "BOTH"
node.numberOfFixedChildren // number
```

### AutoLayoutMixin
```javascript
node.layoutMode           // "NONE" | "HORIZONTAL" | "VERTICAL"
node.layoutWrap           // "NO_WRAP" | "WRAP"
node.primaryAxisSizingMode   // "FIXED" | "AUTO"
node.counterAxisSizingMode   // "FIXED" | "AUTO"
node.primaryAxisAlignItems   // "MIN" | "CENTER" | "MAX" | "SPACE_BETWEEN"
node.counterAxisAlignItems   // "MIN" | "CENTER" | "MAX" | "BASELINE"
node.paddingTop           // number
node.paddingRight         // number
node.paddingBottom        // number
node.paddingLeft          // number
node.itemSpacing          // number
node.counterAxisSpacing   // number
node.itemReverseZIndex    // boolean
node.strokesIncludedInLayout // boolean
```

### AutoLayoutChildMixin
```javascript
node.layoutAlign          // "MIN" | "CENTER" | "MAX" | "STRETCH" | "INHERIT"
node.layoutGrow           // number (0 = fixed, 1 = fill)
node.layoutPositioning    // "AUTO" | "ABSOLUTE"
node.layoutSizingHorizontal  // "FIXED" | "HUG" | "FILL"
node.layoutSizingVertical    // "FIXED" | "HUG" | "FILL"
```

### ExportMixin
```javascript
node.exportSettings       // ExportSettings[]
node.exportAsync(settings?)  // Promise<Uint8Array>
```

### MinimalFillsMixin
```javascript
node.fills               // Paint[]
```

### MinimalStrokesMixin
```javascript
node.strokes             // Paint[]
node.strokeWeight        // number
node.strokeAlign         // StrokeAlign
```

---

## TextNode Properties

### Requires Font Load
```javascript
await figma.loadFontAsync({ family: "Inter", style: "Regular" });
// OR load existing font
await figma.loadFontAsync(textNode.fontName);
```

### Properties
```javascript
text.characters           // string
text.fontSize             // number | typeof figma.mixed
text.fontName             // FontName | typeof figma.mixed
text.fontWeight           // number | typeof figma.mixed
text.textAlignHorizontal  // "LEFT" | "CENTER" | "RIGHT" | "JUSTIFIED"
text.textAlignVertical    // "TOP" | "CENTER" | "BOTTOM"
text.lineHeight           // LineHeight | typeof figma.mixed
text.letterSpacing        // LetterSpacing | typeof figma.mixed
text.textCase             // "ORIGINAL" | "UPPER" | "LOWER" | "TITLE" | typeof figma.mixed
text.textDecoration       // "NONE" | "UNDERLINE" | "STRIKETHROUGH" | typeof figma.mixed
text.textAutoResize       // "NONE" | "WIDTH_AND_HEIGHT" | "HEIGHT" | "TRUNCATE"
text.paragraphIndent      // number
text.paragraphSpacing     // number
text.autoRename           // boolean
text.textStyleId          // string | typeof figma.mixed
text.hyperlink            // HyperlinkTarget | null | typeof figma.mixed
text.hasMissingFont       // readonly boolean
```

### Range Methods (styled segments)
```javascript
text.getRangeFontSize(start, end)
text.setRangeFontSize(start, end, value)
text.getRangeFontName(start, end)
text.setRangeFontName(start, end, value)
text.getRangeTextCase(start, end)
text.setRangeTextCase(start, end, value)
text.getRangeTextDecoration(start, end)
text.setRangeTextDecoration(start, end, value)
text.getRangeLetterSpacing(start, end)
text.setRangeLetterSpacing(start, end, value)
text.getRangeLineHeight(start, end)
text.setRangeLineHeight(start, end, value)
text.getRangeFills(start, end)
text.setRangeFills(start, end, value)
text.getRangeTextStyleId(start, end)
text.setRangeTextStyleId(start, end, value)
text.getRangeHyperlink(start, end)
text.setRangeHyperlink(start, end, value)
text.getStyledTextSegments(fields)
text.getRangeAllFontNames(start, end)  // for loading all fonts
```

### Font Loading Pattern
```javascript
// Single font text
await figma.loadFontAsync(textNode.fontName);
textNode.characters = "New text";

// Multi-font text
const fonts = textNode.getRangeAllFontNames(0, textNode.characters.length);
await Promise.all(fonts.map(f => figma.loadFontAsync(f)));
textNode.characters = "New text";
```

---

## Paint (fills/strokes)

### Solid
```javascript
{
  type: 'SOLID',
  color: { r: 0.09, g: 0.09, b: 0.11 },  // 0-1 range NOT 0-255
  opacity: 0.5,                          // on paint, not color
  visible: true,
  blendMode: 'NORMAL'
}
```

### Linear Gradient
```javascript
{
  type: 'GRADIENT_LINEAR',
  gradientStops: [
    { position: 0, color: { r: 1, g: 0, b: 0, a: 1 } },
    { position: 1, color: { r: 0, g: 0, b: 1, a: 1 } }
  ],
  gradientTransform: [[1, 0, 0], [0, 1, 0]]  // 2x3 matrix
}
```

### Other Gradients
```javascript
type: 'GRADIENT_RADIAL'
type: 'GRADIENT_ANGULAR'
type: 'GRADIENT_DIAMOND'
```

### Image
```javascript
{
  type: 'IMAGE',
  imageHash: string,          // from figma.createImage()
  scaleMode: 'FILL',          // 'FILL' | 'FIT' | 'CROP' | 'TILE'
  imageTransform?: Transform,
  scalingFactor?: number,
  rotation?: number,
  filters?: ImageFilters
}
```

### Video
```javascript
{
  type: 'VIDEO',
  videoHash: string
}
```

### No Fill
```javascript
node.fills = [];
```

---

## Effects

### Drop Shadow
```javascript
{
  type: 'DROP_SHADOW',
  color: { r: 0, g: 0, b: 0, a: 0.25 },
  offset: { x: 0, y: 4 },
  radius: 16,         // blur
  spread: 0,
  visible: true,
  blendMode: 'NORMAL',
  showShadowBehindNode?: boolean
}
```

### Inner Shadow
```javascript
{
  type: 'INNER_SHADOW',
  color: { r: 0, g: 0, b: 0, a: 0.1 },
  offset: { x: 0, y: 2 },
  radius: 4,
  spread: 0,
  visible: true,
  blendMode: 'NORMAL'
}
```

### Layer Blur
```javascript
{
  type: 'LAYER_BLUR',
  radius: 10,
  visible: true
}
```

### Background Blur
```javascript
{
  type: 'BACKGROUND_BLUR',
  radius: 20,
  visible: true
}
```

---

## Strokes

```javascript
node.strokes = [{ type: 'SOLID', color: { r: 0.9, g: 0.9, b: 0.91 } }];
node.strokeWeight = 1;
node.strokeAlign = "INSIDE";     // "INSIDE" | "OUTSIDE" | "CENTER"
node.strokeCap = "ROUND";        // "NONE" | "ROUND" | "SQUARE" | "ARROW_LINES" | "ARROW_EQUILATERAL"
node.strokeJoin = "ROUND";       // "MITER" | "BEVEL" | "ROUND"
node.dashPattern = [4, 4];       // [dash, gap]
node.strokeMiterLimit = 4;       // for MITER join
```

---

## Creating Nodes

### Shapes
```javascript
figma.createRectangle()      // RectangleNode
figma.createEllipse()        // EllipseNode
figma.createLine()           // LineNode
figma.createPolygon()        // PolygonNode
figma.createStar()           // StarNode
figma.createVector()         // VectorNode
```

### Containers
```javascript
figma.createFrame()          // FrameNode
figma.createComponent()      // ComponentNode
figma.createSection()        // SectionNode
figma.createPage()           // PageNode
figma.createSlice()          // SliceNode
```

### Text
```javascript
figma.createText()           // TextNode
```

### Boolean Operations
```javascript
figma.createBooleanOperation()
figma.union(nodes, parent, index?)
figma.subtract(nodes, parent, index?)
figma.intersect(nodes, parent, index?)
figma.exclude(nodes, parent, index?)
```

### Grouping
```javascript
figma.group(nodes, parent, index?)
figma.ungroup(node)
figma.flatten(nodes, parent?, index?)
```

### FigJam
```javascript
figma.createSticky()
figma.createShapeWithText()
figma.createConnector()
figma.createCodeBlock()
figma.createTable(numRows?, numColumns?)
figma.createStamp()
figma.createHighlight()
```

### From Data
```javascript
figma.createNodeFromSvg(svgString)          // FrameNode
figma.createImage(Uint8Array)               // Image
await figma.createImageAsync(url)           // Image
figma.createGif(hash)                       // MediaNode
await figma.createVideoAsync(Uint8Array)    // Video
await figma.createNodeFromJSXAsync(jsx)     // SceneNode
await figma.createLinkPreviewAsync(url)     // EmbedNode | LinkUnfurlNode
```

### After Creating
```javascript
// MUST add to parent
figma.currentPage.appendChild(node);  // top-level
parentFrame.appendChild(node);        // nested

// Set properties
node.name = "My Shape";
node.resize(100, 50);
node.x = 200;
node.y = 100;
node.fills = [{ type: 'SOLID', color: { r: 1, g: 0, b: 0 } }];
```

---

## Selection

### Get Selection
```javascript
const selected = figma.currentPage.selection;  // readonly SceneNode[]
```

### Set Selection
```javascript
// Replace
figma.currentPage.selection = [node1, node2];

// Add
figma.currentPage.selection = figma.currentPage.selection.concat(newNode);
```

### Clear Selection
```javascript
figma.currentPage.selection = [];
```

---

## Export

### PNG (default)
```javascript
const bytes = await node.exportAsync();  // Uint8Array, 1x PNG
```

### PNG Scaled
```javascript
const bytes = await node.exportAsync({
  format: 'PNG',
  constraint: { type: 'SCALE', value: 2 }  // 2x
});
```

### PNG Fixed Size
```javascript
const bytes = await node.exportAsync({
  format: 'PNG',
  constraint: { type: 'WIDTH', value: 800 }
});
```

### JPG
```javascript
const bytes = await node.exportAsync({
  format: 'JPG',
  constraint: { type: 'SCALE', value: 1 }
});
```

### SVG
```javascript
const bytes = await node.exportAsync({ format: 'SVG' });
```

### SVG String
```javascript
const svgString = await node.exportAsync({ format: 'SVG_STRING' });
```

### PDF
```javascript
const bytes = await node.exportAsync({ format: 'PDF' });
```

### Export Options
```javascript
{
  format: 'PNG' | 'JPG' | 'SVG' | 'PDF' | 'SVG_STRING',
  constraint?: { type: 'SCALE' | 'WIDTH' | 'HEIGHT', value: number },
  contentsOnly?: boolean,        // default true
  useAbsoluteBounds?: boolean,   // default false, use for text
  suffix?: string,
  // SVG only:
  svgOutlineText?: boolean,      // default true
  svgIdAttribute?: boolean,
  svgSimplifyStroke?: boolean    // default true
}
```

---

## Events

### Register
```javascript
figma.on('selectionchange', () => { ... });
figma.on('currentpagechange', () => { ... });
figma.on('documentchange', (event) => { ... });
figma.on('close', () => { ... });
figma.on('run', (event) => { ... });
figma.on('drop', (event) => { ... });
```

### One-time
```javascript
figma.once('selectionchange', () => { ... });
```

### Remove
```javascript
figma.off('selectionchange', callback);
```

### DocumentChange Event
```javascript
figma.on('documentchange', (event) => {
  for (const change of event.documentChanges) {
    // change.type: 'CREATE' | 'DELETE' | 'PROPERTY_CHANGE' |
    //              'STYLE_CREATE' | 'STYLE_DELETE' | 'STYLE_PROPERTY_CHANGE'
    // change.origin: 'LOCAL' | 'REMOTE'
    // change.id: string
    // change.node?: BaseNode (for node changes)
    // change.properties?: string[] (for property changes)
  }
});
```

### Timer Events
```javascript
figma.on('timerstart', () => { ... });
figma.on('timerstop', () => { ... });
figma.on('timerpause', () => { ... });
figma.on('timerresume', () => { ... });
figma.on('timeradjust', () => { ... });
figma.on('timerdone', () => { ... });
```

---

## Viewport

```javascript
figma.viewport.scrollAndZoomIntoView([node1, node2]);
figma.viewport.center = { x: 500, y: 500 };
figma.viewport.zoom = 1;         // 1 = 100%
figma.viewport.bounds            // readonly { x, y, width, height }
```

---

## Client Storage (persistent)

```javascript
await figma.clientStorage.setAsync('key', value);
const value = await figma.clientStorage.getAsync('key');
await figma.clientStorage.deleteAsync('key');
const keys = await figma.clientStorage.keysAsync();
```

---

## Styles

### Get Styles
```javascript
const paintStyles = await figma.getLocalPaintStylesAsync();
const textStyles = await figma.getLocalTextStylesAsync();
const effectStyles = await figma.getLocalEffectStylesAsync();
const gridStyles = await figma.getLocalGridStylesAsync();
```

### Create Styles
```javascript
const style = figma.createPaintStyle();
style.name = "Primary";
style.paints = [{ type: 'SOLID', color: { r: 0.09, g: 0.09, b: 0.11 } }];

const textStyle = figma.createTextStyle();
const effectStyle = figma.createEffectStyle();
const gridStyle = figma.createGridStyle();
```

### Apply Style
```javascript
node.fillStyleId = style.id;
node.strokeStyleId = style.id;
node.effectStyleId = effectStyle.id;
textNode.textStyleId = textStyle.id;
```

### Import from Library
```javascript
const component = await figma.importComponentByKeyAsync(key);
const style = await figma.importStyleByKeyAsync(key);
```

---

## Components & Instances

### Create Component
```javascript
const component = figma.createComponent();
// OR convert existing
const component = figma.createComponentFromNode(existingNode);
```

### Create Instance
```javascript
const instance = component.createInstance();
```

### Instance Overrides
```javascript
// Can override: fills, strokes, effects, opacity, visible, text.characters
// Cannot override: position, size (unless auto-layout), children order
instance.fills = [{ type: 'SOLID', color: { r: 1, g: 0, b: 0 } }];
```

### Detach Instance
```javascript
const frame = instance.detachInstance();
```

### Component Properties
```javascript
component.componentPropertyDefinitions  // readonly
component.addComponentProperty(name, type, defaultValue)
component.editComponentProperty(name, newValues)
component.deleteComponentProperty(name)
```

---

## Plugin Data

### Per-node Storage
```javascript
node.setPluginData('key', 'value');
const value = node.getPluginData('key');
node.setPluginDataKeys();  // string[]
```

### Shared (cross-plugin)
```javascript
node.setSharedPluginData('namespace', 'key', 'value');
const value = node.getSharedPluginData('namespace', 'key');
```

### Root-level
```javascript
figma.root.setPluginData('key', 'value');
```

---

## Notifications

```javascript
figma.notify("Success!");
figma.notify("Error!", { error: true });
figma.notify("Info", { timeout: 5000 });
figma.notify("Action", {
  timeout: Infinity,
  button: { text: "Undo", action: () => { ... } }
});

// Returns handler
const handler = figma.notify("Loading...", { timeout: Infinity });
handler.cancel();  // dismiss
```

---

## Error Patterns

| Error | Cause | Fix |
|-------|-------|-----|
| `Cannot call with documentAccess: dynamic-page` | Sync getNodeById | `await figma.getNodeByIdAsync()` |
| `Cannot read property 'x' of null` | Node not found | Add null check |
| `Cannot write to node with unloaded font` | Text edit without font | `await figma.loadFontAsync(text.fontName)` |
| `This property cannot be overridden on an instance` | Invalid instance override | Check allowed overrides |
| `Cannot write to internal and read-only nodes` | Editing protected node | Check editable properties |
| `Cannot access children on a page that has not been explicitly loaded` | Page not loaded | `await page.loadAsync()` |
| `Invalid discriminator value` (in set_fills) | Pattern fill exists | Remove pattern fills first |
| `Expected "opacity" to have type number but got string` | Wrong type | Match expected types |
| `fills is not iterable` | Node has no fills | Check GeometryMixin |
| Plugin timeout/hang | Complex auto-layout | Simplify operations |

---

## Workflow

```
1. User provides Figma URL
2. Extract fileKey: figma.com/design/{fileKey}/...
3. Extract nodeId (optional): node-id={nodeId} in URL params
4. Call mcp__figma__get_figma_data(fileKey, nodeId?)
5. Parse response: node IDs, types, structure
6. Write code.js using ASYNC APIs
7. User runs: Plugins → Development → Claude_direct
8. On error: read message, fix, repeat
```

---

## Common Patterns

### Move
```javascript
const node = await figma.getNodeByIdAsync("9:9");
node.x = 80;
node.y = 220;
```

### Resize
```javascript
node.resize(400, 300);
```

### Color
```javascript
node.fills = [{ type: 'SOLID', color: { r: 0.23, g: 0.51, b: 0.96 } }];
```

### Text Content
```javascript
const text = await figma.getNodeByIdAsync("9:10");
await figma.loadFontAsync(text.fontName);
text.characters = "New Text";
```

### Font Change
```javascript
await figma.loadFontAsync({ family: "Inter", style: "Bold" });
text.fontName = { family: "Inter", style: "Bold" };
text.fontSize = 24;
```

### Add to Frame
```javascript
const parent = await figma.getNodeByIdAsync("9:8");
const rect = figma.createRectangle();
rect.resize(100, 100);
rect.x = 50;
rect.y = 50;
rect.fills = [{ type: 'SOLID', color: { r: 1, g: 0, b: 0 } }];
parent.appendChild(rect);
```

### Clone
```javascript
const original = await figma.getNodeByIdAsync("9:9");
const clone = original.clone();
clone.x = original.x + original.width + 20;
```

### Delete
```javascript
const node = await figma.getNodeByIdAsync("9:9");
node.remove();
```

### Reorder
```javascript
parent.insertChild(0, node);  // move to back
parent.insertChild(parent.children.length - 1, node);  // move to front
```

---

## Auto Layout

### Enable
```javascript
frame.layoutMode = "VERTICAL";  // or "HORIZONTAL"
frame.primaryAxisSizingMode = "AUTO";
frame.counterAxisSizingMode = "AUTO";
frame.paddingTop = 24;
frame.paddingRight = 24;
frame.paddingBottom = 24;
frame.paddingLeft = 24;
frame.itemSpacing = 16;
```

### Child Sizing
```javascript
child.layoutSizingHorizontal = "FILL";  // "FIXED" | "HUG" | "FILL"
child.layoutSizingVertical = "HUG";
```

### Alignment
```javascript
frame.primaryAxisAlignItems = "CENTER";    // "MIN" | "CENTER" | "MAX" | "SPACE_BETWEEN"
frame.counterAxisAlignItems = "CENTER";    // "MIN" | "CENTER" | "MAX" | "BASELINE"
```

### Wrap
```javascript
frame.layoutWrap = "WRAP";  // "NO_WRAP" | "WRAP"
frame.counterAxisSpacing = 8;  // gap between wrapped rows
```

**WARNING:** Complex auto-layout can hang. Keep simple.

---

## Design Tokens (shadcn)

```javascript
const colors = {
  bg:          { r: 1, g: 1, b: 1 },           // #FFFFFF
  fg:          { r: 0.09, g: 0.09, b: 0.11 },  // #171717
  muted:       { r: 0.96, g: 0.96, b: 0.96 },  // #F5F5F5
  mutedFg:     { r: 0.45, g: 0.45, b: 0.47 },  // #737373
  border:      { r: 0.9, g: 0.9, b: 0.91 },    // #E5E5E5
  primary:     { r: 0.09, g: 0.09, b: 0.11 },  // #171717
  primaryFg:   { r: 0.98, g: 0.98, b: 0.98 },  // #FAFAFA
  destructive: { r: 0.94, g: 0.27, b: 0.27 },  // #EF4444
  blue:        { r: 0.23, g: 0.51, b: 0.96 },  // #3B82F6
  green:       { r: 0.13, g: 0.77, b: 0.42 },  // #22C55E
  yellow:      { r: 0.98, g: 0.75, b: 0.18 },  // #FACC15
  purple:      { r: 0.56, g: 0.24, b: 0.86 },  // #8F3EDC
};

const spacing = [4, 8, 12, 16, 20, 24, 32, 40, 48, 64];
const radius = [4, 6, 8, 12, 16, 24];
const fontFamily = "Inter";
const fontWeights = ["Regular", "Medium", "SemiBold", "Bold"];
const fontSizes = [12, 13, 14, 16, 18, 20, 24, 30, 36, 48, 60];
```

---

## Limitations

- MCP tools require Claude Code restart to load
- Must load fonts before ANY text property changes
- User must manually run plugin in Figma
- No direct external image URLs (use bytes via createImage)
- Complex auto-layout can hang/timeout
- Cannot access other pages without `page.loadAsync()` or `figma.loadAllPagesAsync()`
- Plugin runs once then closes (no persistent state between runs)
- Pattern fills cannot be modified via plugin (will error)
- Instance overrides limited (no position/size unless auto-layout)
- Dev Mode plugins cannot edit nodes (metadata only)
- `figma.mixed` returned when property varies across selection/range
