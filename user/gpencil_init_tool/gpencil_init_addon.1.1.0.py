bl_info = {
    "name": "Grease Pencil Quick Init",
    "author": "User",
    "version": (1, 1, 0),
    "blender": (4, 0, 0),
    "location": "3D Viewport > N Panel > GP Init / Search Menu (F3) > 'Grease Pencil Quick Init'",
    "description": "Quickly initialize or reuse a grease pencil object at origin and switch to draw mode",
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

    def execute(self, context):
        try:
            # Look for existing grease pencil objects
            gpencil_objects = [obj for obj in bpy.data.objects if obj.type == 'GREASEPENCIL']
            
            if gpencil_objects:
                gpencil_obj = gpencil_objects[0]
                self.report({'INFO'}, f"Reusing existing grease pencil object: {gpencil_obj.name}")
            else:
                bpy.ops.object.grease_pencil_add(type='EMPTY')
                gpencil_obj = context.active_object
                gpencil_obj.name = "GPencil"
                self.report({'INFO'}, f"Created new grease pencil object: {gpencil_obj.name}")
            
            # Move object to origin
            gpencil_obj.location = Vector((0.0, 0.0, 0.0))
            
            # Ensure we're in object mode first
            if context.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
            
            # Select and make the grease pencil object active
            if context.mode == 'OBJECT':
                bpy.ops.object.select_all(action='DESELECT')
            gpencil_obj.select_set(True)
            context.view_layer.objects.active = gpencil_obj
            
            # Switch to grease pencil draw mode
            if context.mode != 'PAINT_GREASE_PENCIL':
                bpy.ops.object.mode_set(mode='PAINT_GREASE_PENCIL')
                self.report({'INFO'}, "Switched to Grease Pencil Draw mode")
            else:
                self.report({'INFO'}, "Already in Grease Pencil Draw mode")
            
            # Handle brush setup
            if context.mode == 'PAINT_GREASE_PENCIL':
                gpencil_paint = context.tool_settings.gpencil_paint
                
                if gpencil_paint and gpencil_paint.brush:
                    # Show current brush
                    current_brush = gpencil_paint.brush
                    self.report({'INFO'}, f"Current brush: {current_brush.name}")
                    
                    # Create Ink Pen brush if it doesn't exist
                    ink_pen_exists = False
                    for brush in bpy.data.brushes:
                        if (hasattr(brush, 'use_paint_grease_pencil') and 
                            brush.use_paint_grease_pencil and 
                            brush.name == 'Ink Pen'):
                            ink_pen_exists = True
                            break
                    
                    if not ink_pen_exists:
                        self.report({'INFO'}, "Creating 'Ink Pen' brush...")
                        # Find Pencil brush to copy
                        pencil_brush = None
                        for brush in bpy.data.brushes:
                            if (hasattr(brush, 'use_paint_grease_pencil') and 
                                brush.use_paint_grease_pencil and 
                                brush.name == 'Pencil'):
                                pencil_brush = brush
                                break
                        
                        if pencil_brush:
                            new_brush = pencil_brush.copy()
                            new_brush.name = "Ink Pen"
                            self.report({'INFO'}, "Successfully created 'Ink Pen' brush")
                        else:
                            self.report({'WARNING'}, "Could not find 'Pencil' brush to copy")
                    
                    # Set brush size to 2
                    current_brush.size = 2
                    self.report({'INFO'}, f"Set brush '{current_brush.name}' radius to 2")
                    
                    # Guide user about brush selection
                    if current_brush.name != 'Ink Pen' and ink_pen_exists:
                        self.report({'INFO'}, "Please manually select the 'Ink Pen' brush for optimal results")
                    elif current_brush.name == 'Ink Pen':
                        self.report({'INFO'}, "Perfect! Already using 'Ink Pen' brush")
                else:
                    self.report({'WARNING'}, "Could not access brush settings")
            
            # Handle layers
            if gpencil_obj.data.layers:
                layer_name = gpencil_obj.data.layers[0].name
                self.report({'INFO'}, f"Using existing layer: {layer_name}")
            else:
                layer = gpencil_obj.data.layers.new("Lines", set_active=True)
                self.report({'INFO'}, f"Created default layer: {layer.name}")
            
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
        box.label(text="• Create Ink Pen brush if needed")
        box.label(text="• Set radius to 2")
        
        # Current status
        if context.active_object and context.active_object.type == 'GREASEPENCIL':
            box = layout.box()
            box.label(text="Current GP Object:", icon='GREASEPENCIL')
            box.label(text=f"Name: {context.active_object.name}")
            box.label(text=f"Mode: {context.mode}")
            
            if context.mode == 'PAINT_GREASE_PENCIL':
                gpencil_paint = context.tool_settings.gpencil_paint
                if gpencil_paint and gpencil_paint.brush:
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

