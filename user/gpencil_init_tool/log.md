# Grease Pencil Quick Init — Version differences (1.0.0 vs 1.1.0)

The two files are recovered from deleting mistakenly, and unable to identify which one is newer.Below is the comparison of two files.

## Version and metadata
- **1.0.0**: version (1, 0, 0). Description: "Complete grease pencil setup: object, draw mode, optimal brush, and overlay settings for best drawing experience"
- **1.1.0**: version (1, 1, 0). Description: "Quickly initialize or reuse a grease pencil object at origin and switch to draw mode"

## Overlay configuration
- **1.0.0**: Has full GP overlay setup via `configure_grease_pencil_overlays()`: enables fade layers (0.5), fade objects (0.5), grid opacity (0.5). Overlay logic is also duplicated at the end of `execute()` (including `use_gpencil_grid`).
- **1.1.0**: No overlay configuration; all overlay code removed.

## Brush handling
- **1.0.0**: Tries to load/activate "Ink Pen" from Essentials asset library (`bpy.ops.brush.asset_activate`). Fallback: Pencil → current brush. Sets brush size after potential switch.
- **1.1.0**: Creates "Ink Pen" by copying the Pencil brush if it doesn't exist. If current brush is not Ink Pen, reports message asking user to manually select Ink Pen. Sets brush size on current brush.

## Error handling and compatibility
- **1.0.0**: try/except around mode switch to PAINT_GREASE_PENCIL; returns CANCELLED on RuntimeError. Layer name uses hasattr check for Blender 4.x.
- **1.1.0**: No try/except for mode switch. Direct `.name` access on layers.

## Panel (UI)
- **1.0.0**: Features list includes "Auto-select: Ink Pen → Pencil fallback", "Configure GP overlay settings", "Works on all Blender installs".
- **1.1.0**: Features list includes "Create Ink Pen brush if needed"; no overlay or "works on all installs" lines.

## Code size and structure
- **1.0.0**: ~328 lines; overlay logic in dedicated method and again at end of execute(); more status reports and comments.
- **1.1.0**: ~168 lines; single linear execute(); no overlay; fewer reports.

## Summary
- **1.0.0**: Feature-rich: overlay tuning, asset-based Ink Pen activation, more defensive code; some duplication in overlay logic.
- **1.1.0**: Minimal: object + mode + brush size; creates Ink Pen by copy, no overlays; simpler and shorter. Version number (1.1.0) is higher than 1.0.0.
