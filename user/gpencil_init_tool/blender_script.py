import bpy
from mathutils import Vector

def create_or_reuse_gpencil():
    """
    Create or reuse a grease pencil object at origin and switch to draw mode
    """
    
    # Look for existing grease pencil objects (updated type name for Blender 4.x)
    gpencil_objects = [obj for obj in bpy.data.objects if obj.type == 'GREASEPENCIL']
    
    if gpencil_objects:
        # Reuse the first grease pencil object found
        gpencil_obj = gpencil_objects[0]
        print(f"Reusing existing grease pencil object: {gpencil_obj.name}")
    else:
        # Create a new grease pencil object using the proper operator
        bpy.ops.object.grease_pencil_add(type='EMPTY')
        
        # Get the newly created object (it will be the active object)
        gpencil_obj = bpy.context.active_object
        gpencil_obj.name = "GPencil"
        
        print(f"Created new grease pencil object: {gpencil_obj.name}")
    
    # Move object to origin
    gpencil_obj.location = Vector((0.0, 0.0, 0.0))
    
    # Ensure we're in object mode and have proper context
    if bpy.context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    
    # Deselect all objects first (with context check)
    if bpy.context.mode == 'OBJECT':
        bpy.ops.object.select_all(action='DESELECT')
    
    # Select and make the grease pencil object active
    gpencil_obj.select_set(True)
    bpy.context.view_layer.objects.active = gpencil_obj
    
    # Switch to grease pencil draw mode if not already in it
    current_mode = bpy.context.mode
    print(f"Current mode: {current_mode}")
    
    if current_mode != 'PAINT_GREASE_PENCIL':
        try:
            # Make sure we're in object mode first
            if current_mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
            
            # Switch to grease pencil draw mode (updated for Blender 4.x)
            bpy.ops.object.mode_set(mode='PAINT_GREASE_PENCIL')
            print("Switched to Grease Pencil Draw mode")
        except RuntimeError as e:
            print(f"Could not switch to draw mode: {e}")
            print("Make sure a grease pencil object is selected and active")
    else:
        print("Already in Grease Pencil Draw mode")
    
    # Set stroke mode to Ink Pen and adjust radius
    if bpy.context.mode == 'PAINT_GREASE_PENCIL':
        try:
            # Get the grease pencil paint context
            gpencil_paint = bpy.context.tool_settings.gpencil_paint
            
            # Set brush to Ink Pen if not already
            current_brush_name = gpencil_paint.brush.name if gpencil_paint.brush else "None"
            print(f"Current brush: {current_brush_name}")
            
            if gpencil_paint.brush and gpencil_paint.brush.name != 'Ink Pen':
                # Find the Ink Pen brush (try multiple possible names)
                ink_pen_brush = None
                possible_names = ['Ink Pen', 'Pen', 'Draw Pencil', 'Pencil']
                
                for brush_name in possible_names:
                    for brush in bpy.data.brushes:
                        if brush.name == brush_name and brush.use_paint_grease_pencil:
                            ink_pen_brush = brush
                            break
                    if ink_pen_brush:
                        break
                
                if ink_pen_brush:
                    gpencil_paint.brush = ink_pen_brush
                    print(f"Switched to {ink_pen_brush.name} brush")
                else:
                    # List available grease pencil brushes for debugging
                    available_brushes = [b.name for b in bpy.data.brushes if b.use_paint_grease_pencil]
                    print(f"Available GP brushes: {available_brushes}")
                    print("Ink Pen brush not found, using current brush")
            else:
                print("Already using Ink Pen brush")
            
            # Set radius to 2
            if gpencil_paint.brush:
                gpencil_paint.brush.size = 2
                print("Set brush radius to 2")
                
        except Exception as e:
            print(f"Error setting brush properties: {e}")
    
    return gpencil_obj

def main():
    """
    Main function to execute the grease pencil initialization
    """
    try:
        gpencil_obj = create_or_reuse_gpencil()
        print(f"Grease pencil setup complete. Active object: {gpencil_obj.name}")
        print(f"Final mode: {bpy.context.mode}")
        
        # Check if it has layers and create one if needed
        if gpencil_obj.data.layers:
            # Use 'name' instead of 'info' for Blender 4.x compatibility
            layer_name = gpencil_obj.data.layers[0].name if hasattr(gpencil_obj.data.layers[0], 'name') else str(gpencil_obj.data.layers[0])
            print(f"Using existing layer: {layer_name}")
        else:
            # Create a default layer
            layer = gpencil_obj.data.layers.new("Lines", set_active=True)
            layer_name = layer.name if hasattr(layer, 'name') else str(layer)
            print(f"Created default layer: {layer_name}")
            
    except Exception as e:
        print(f"Error during grease pencil setup: {e}")
        import traceback
        traceback.print_exc()

# Execute the script
if __name__ == "__main__":
    main()