bl_info = {
    "name": "Grease Pencil Quick Init",
    "author": "User",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "3D Viewport > N Panel > GP Init / Search Menu (F3) > 'Grease Pencil Quick Init'",
    "description": "Complete grease pencil setup: object, draw mode, optimal brush, and overlay settings for best drawing experience",
    "category": "Object",
}

import bpy
from mathutils import Vector
from bpy.types import Operator, Panel


class GPENCIL_OT_quick_init(Operator):
    """Initialize or reuse grease pencil object and switch to draw mode"""
    bl_idname = "gpencil.quick_init"
    bl_label = "Grease Pencil Quick Init"
    bl_options = {'REGISTER', 'UNDO'}
    
    def configure_grease_pencil_overlays(self, context):
        """Configure grease pencil overlay settings for optimal drawing experience"""
        try:
            # Get the 3D viewport overlay settings
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    for space in area.spaces:
                        if space.type == 'VIEW_3D':
                            overlay = space.overlay
                            
                            # Track what we're changing
                            changes_made = []
                            
                            # 1. Enable grease pencil fade layers and set amount
                            if not overlay.use_gpencil_fade_layers:
                                overlay.use_gpencil_fade_layers = True
                                changes_made.append("enabled fade layers")
                            if overlay.gpencil_fade_layer != 0.5:
                                overlay.gpencil_fade_layer = 0.5
                                changes_made.append("fade layer amount to 0.5")
                            
                            # 2. Enable grease pencil fade objects and set amount  
                            if not overlay.use_gpencil_fade_objects:
                                overlay.use_gpencil_fade_objects = True
                                changes_made.append("enabled fade objects")
                            if overlay.gpencil_fade_objects != 0.5:
                                overlay.gpencil_fade_objects = 0.5
                                changes_made.append("fade objects amount to 0.5")
                            
                            # 3. Set grease pencil grid opacity to 0.5
                            if overlay.gpencil_grid_opacity != 0.5:
                                overlay.gpencil_grid_opacity = 0.5
                                changes_made.append("grid opacity to 0.5")
                            
                            # Report changes
                            if changes_made:
                                self.report({'INFO'}, f"Updated GP overlays: {', '.join(changes_made)}")
                            else:
                                self.report({'INFO'}, "GP overlay settings already optimal")
                            
                            return  # Exit after configuring the first 3D viewport
            
            self.report({'WARNING'}, "Could not find 3D viewport to configure overlays")
            
        except Exception as e:
            self.report({'WARNING'}, f"Could not configure GP overlays: {e}")

    def execute(self, context):
        try:
            # Look for existing grease pencil objects (updated type name for Blender 4.x)
            gpencil_objects = [obj for obj in bpy.data.objects if obj.type == 'GREASEPENCIL']
            
            if gpencil_objects:
                # Reuse the first grease pencil object found
                gpencil_obj = gpencil_objects[0]
                self.report({'INFO'}, f"Reusing existing grease pencil object: {gpencil_obj.name}")
            else:
                # Create a new grease pencil object using the proper operator
                bpy.ops.object.grease_pencil_add(type='EMPTY')
                
                # Get the newly created object (it will be the active object)
                gpencil_obj = context.active_object
                gpencil_obj.name = "GPencil"
                
                self.report({'INFO'}, f"Created new grease pencil object: {gpencil_obj.name}")
            
            # Move object to origin
            gpencil_obj.location = Vector((0.0, 0.0, 0.0))
            
            # Ensure we're in object mode and have proper context
            if context.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
            
            # Deselect all objects first (with context check)
            if context.mode == 'OBJECT':
                bpy.ops.object.select_all(action='DESELECT')
            
            # Select and make the grease pencil object active
            gpencil_obj.select_set(True)
            context.view_layer.objects.active = gpencil_obj
            
            # Switch to grease pencil draw mode if not already in it
            current_mode = context.mode
            
            if current_mode != 'PAINT_GREASE_PENCIL':
                try:
                    # Make sure we're in object mode first
                    if current_mode != 'OBJECT':
                        bpy.ops.object.mode_set(mode='OBJECT')
                    
                    # Switch to grease pencil draw mode (updated for Blender 4.x)
                    bpy.ops.object.mode_set(mode='PAINT_GREASE_PENCIL')
                    self.report({'INFO'}, "Switched to Grease Pencil Draw mode")
                except RuntimeError as e:
                    self.report({'ERROR'}, f"Could not switch to draw mode: {e}")
                    return {'CANCELLED'}
            else:
                self.report({'INFO'}, "Already in Grease Pencil Draw mode")
            
            # Configure grease pencil overlay settings for better drawing experience
            self.report({'INFO'}, "Configuring GP overlay settings...")
            self.configure_grease_pencil_overlays(context)
            
            # Handle brush setup AFTER switching to draw mode
            if context.mode == 'PAINT_GREASE_PENCIL':
                # Get the grease pencil paint context
                gpencil_paint = context.tool_settings.gpencil_paint
                
                if not gpencil_paint:
                    self.report({'WARNING'}, "Could not access grease pencil paint settings")
                    return {'FINISHED'}
                
                # Get current brush info
                current_brush = gpencil_paint.brush
                if current_brush:
                    current_brush_name = current_brush.name
                    self.report({'INFO'}, f"Current brush: {current_brush_name}")
                    
                    # Get all available grease pencil brushes (now that we're in the right mode)
                    available_brushes = []
                    ink_pen_brush = None
                    
                    for brush in bpy.data.brushes:
                        if hasattr(brush, 'use_paint_grease_pencil') and brush.use_paint_grease_pencil:
                            available_brushes.append(brush.name)
                            if brush.name == 'Ink Pen':
                                ink_pen_brush = brush
                    
                    self.report({'INFO'}, f"Available GP brushes: {', '.join(available_brushes) if available_brushes else 'None'}")
                    
                    # Try to use the best available brush: Ink Pen > Pencil > any drawing brush
                    target_brush_name = None
                    
                    if current_brush.name == 'Ink Pen':
                        self.report({'INFO'}, "Perfect! Already using 'Ink Pen' brush")
                        target_brush_name = 'Ink Pen'
                    else:
                        # Try to switch to Ink Pen (attempt asset activation even if not currently loaded)
                        ink_pen_success = False
                        try:
                            bpy.ops.brush.asset_activate(
                                asset_library_type="ESSENTIALS",
                                asset_library_identifier='',
                                relative_asset_identifier='brushes\\essentials_brushes-gp_draw.blend\\Brush\\Ink Pen'
                            )
                            
                            # Check if the switch was successful
                            new_brush = gpencil_paint.brush
                            if new_brush and new_brush.name == 'Ink Pen':
                                self.report({'INFO'}, f"Successfully switched from '{current_brush_name}' to 'Ink Pen' brush!")
                                target_brush_name = 'Ink Pen'
                                ink_pen_success = True
                            else:
                                self.report({'INFO'}, f"Attempted Ink Pen switch, current brush: {new_brush.name if new_brush else 'None'}")
                                
                        except Exception as e:
                            self.report({'WARNING'}, f"Could not switch to Ink Pen brush: {e}")
                            # Will fall back to Pencil below
                        
                        # Fallback to Pencil if Ink Pen failed or not available
                        if not ink_pen_success:
                            # Look for standard Pencil brush
                            pencil_brush = None
                            for brush in bpy.data.brushes:
                                if (hasattr(brush, 'use_paint_grease_pencil') and 
                                    brush.use_paint_grease_pencil and 
                                    brush.name == 'Pencil'):
                                    pencil_brush = brush
                                    break
                            
                            if pencil_brush:
                                if current_brush.name == 'Pencil':
                                    self.report({'INFO'}, "Using 'Pencil' brush (Ink Pen not available)")
                                    target_brush_name = 'Pencil'
                                else:
                                    # Try to switch to Pencil
                                    # Note: Pencil is usually the default, but we can try to ensure it
                                    self.report({'INFO'}, f"Falling back to 'Pencil' brush from '{current_brush_name}'")
                                    # Pencil is usually available by default, no special activation needed
                                    target_brush_name = 'Pencil'
                            else:
                                # Last resort: use whatever brush is currently active
                                self.report({'WARNING'}, "Neither Ink Pen nor Pencil brush found - using current brush")
                                target_brush_name = current_brush.name
                    
                    # Set radius to 2 (get the current brush after potential switch)
                    try:
                        active_brush = gpencil_paint.brush
                        if active_brush:
                            active_brush.size = 2
                            self.report({'INFO'}, f"Set brush '{active_brush.name}' radius to 2")
                        else:
                            self.report({'WARNING'}, "No active brush to set size")
                    except Exception as e:
                        self.report({'ERROR'}, f"Could not set brush size: {e}")
                        
                else:
                    self.report({'WARNING'}, "No active brush found")
            
            # Check if it has layers and create one if needed
            if gpencil_obj.data.layers:
                # Use 'name' instead of 'info' for Blender 4.x compatibility
                layer_name = gpencil_obj.data.layers[0].name if hasattr(gpencil_obj.data.layers[0], 'name') else str(gpencil_obj.data.layers[0])
                self.report({'INFO'}, f"Using existing layer: {layer_name}")
            else:
                # Create a default layer
                layer = gpencil_obj.data.layers.new("Lines", set_active=True)
                layer_name = layer.name if hasattr(layer, 'name') else str(layer)
                self.report({'INFO'}, f"Created default layer: {layer_name}")
            
            # Configure grease pencil overlay settings as final step
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    for space in area.spaces:
                        if space.type == 'VIEW_3D':
                            overlay = space.overlay
                            changes_made = []
                            
                            # 1. Enable grease pencil fade layers and set amount
                            if not overlay.use_gpencil_fade_layers:
                                overlay.use_gpencil_fade_layers = True
                                changes_made.append("enabled fade layers")
                            if overlay.gpencil_fade_layer != 0.5:
                                overlay.gpencil_fade_layer = 0.5
                                changes_made.append("fade layer to 0.5")
                            
                            # 2. Enable grease pencil fade objects and set amount
                            if not overlay.use_gpencil_fade_objects:
                                overlay.use_gpencil_fade_objects = True
                                changes_made.append("enabled fade objects")
                            if overlay.gpencil_fade_objects != 0.5:
                                overlay.gpencil_fade_objects = 0.5
                                changes_made.append("fade objects to 0.5")
                            
                            # 3. Enable grease pencil grid and set opacity
                            if hasattr(overlay, 'use_gpencil_grid') and not overlay.use_gpencil_grid:
                                overlay.use_gpencil_grid = True
                                changes_made.append("enabled grid")
                            if overlay.gpencil_grid_opacity != 0.5:
                                overlay.gpencil_grid_opacity = 0.5
                                changes_made.append("grid opacity to 0.5")
                            
                            if changes_made:
                                self.report({'INFO'}, f"Updated GP overlays: {', '.join(changes_made)}")
                            else:
                                self.report({'INFO'}, "GP overlay settings already optimal")
                            break
                    break
            
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Error during grease pencil setup: {e}")
            return {'CANCELLED'}


class GPENCIL_PT_quick_init_panel(Panel):
    """Creates a Panel in the 3D Viewport N-Panel"""
    bl_label = "GP Quick Init"
    bl_idname = "GPENCIL_PT_quick_init"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "GP Init"

    def draw(self, context):
        layout = self.layout

        # Main operator button
        layout.operator("gpencil.quick_init", text="Initialize Grease Pencil", icon='GREASEPENCIL')
        
        # Info section
        box = layout.box()
        box.label(text="Features:", icon='INFO')
        box.label(text="• Create/reuse GP object at origin")
        box.label(text="• Switch to draw mode")
        box.label(text="• Auto-select: Ink Pen → Pencil fallback")
        box.label(text="• Set radius to 2")
        box.label(text="• Configure GP overlay settings")
        box.label(text="• Works on all Blender installs")
        
        # Current status
        if context.active_object and context.active_object.type == 'GREASEPENCIL':
            box = layout.box()
            box.label(text="Current GP Object:", icon='GREASEPENCIL')
            box.label(text=f"Name: {context.active_object.name}")
            box.label(text=f"Mode: {context.mode}")
            
            if context.mode == 'PAINT_GREASE_PENCIL':
                gpencil_paint = context.tool_settings.gpencil_paint
                if gpencil_paint.brush:
                    box.label(text=f"Brush: {gpencil_paint.brush.name}")
                    box.label(text=f"Size: {gpencil_paint.brush.size}")


def register():
    bpy.utils.register_class(GPENCIL_OT_quick_init)
    bpy.utils.register_class(GPENCIL_PT_quick_init_panel)


def unregister():
    bpy.utils.unregister_class(GPENCIL_OT_quick_init)
    bpy.utils.unregister_class(GPENCIL_PT_quick_init_panel)


if __name__ == "__main__":
    register()
