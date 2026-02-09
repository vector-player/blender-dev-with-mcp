import bpy

# Script: Create curve object from object motion path
# Purpose: Creates a NURBS curve named "curve_path" that follows 
#          the same path as the motion path of a target object

# Step 1: Set target object name (for generic adaptability)
tgt_camera = "cam_0-96"

# Step 2: Get the motion object
motion_obj = bpy.data.objects.get(tgt_camera)

if motion_obj:
    # Step 3: Ensure motion path is available and calculated
    # Motion paths are calculated using bpy.ops.object.paths_calculate()
    # Note: This operator uses the scene frame range or animation range automatically
    # Reference: https://docs.blender.org/manual/en/latest/animation/motion_paths.html
    
    if motion_obj.animation_data:
        # Access motion path - it might be None
        motion_path = motion_obj.motion_path
        
        # CRITICAL FIX: Check if motion_path is None and calculate it
        if motion_path is None:
            print(f"Motion path is None for {tgt_camera} - calculating motion path...")
            
            # Get frame range from animation action (for reference)
            frame_start = 1
            frame_end = 100
            if motion_obj.animation_data.action:
                if motion_obj.animation_data.action.frame_range:
                    frame_start = int(motion_obj.animation_data.action.frame_range[0])
                    frame_end = int(motion_obj.animation_data.action.frame_range[1])
                else:
                    # Fallback to scene frame range
                    scene = bpy.context.scene
                    frame_start = scene.frame_start
                    frame_end = scene.frame_end
            
            print(f"  Animation frame range: {frame_start} to {frame_end}")
            
            # Select and activate the motion object (required for operator)
            # Store current selection to restore later
            previous_active = bpy.context.view_layer.objects.active
            previous_selected = bpy.context.selected_objects.copy()
            
            # Set motion object as active and selected
            bpy.context.view_layer.objects.active = motion_obj
            motion_obj.select_set(True)
            
            # Deselect other objects
            for obj in list(bpy.context.selected_objects):
                if obj != motion_obj:
                    obj.select_set(False)
            
            # Set scene frame range to match animation (if needed)
            scene = bpy.context.scene
            original_frame_start = scene.frame_start
            original_frame_end = scene.frame_end
            original_frame_current = scene.frame_current
            
            # Set scene frame range to animation range
            scene.frame_start = frame_start
            scene.frame_end = frame_end
            scene.frame_set(frame_start)
            bpy.context.view_layer.update()
            
            try:
                # Clear any existing motion paths first
                bpy.ops.object.paths_clear()
                print("  Cleared existing motion paths")
            except Exception as e:
                print(f"  Note: Clear operation: {e}")
            
            # Calculate motion path using the CORRECT operator
            # IMPORTANT: bpy.ops.object.paths_calculate() does NOT accept frame_start/frame_end parameters
            # It uses the scene frame range automatically
            try:
                result = bpy.ops.object.paths_calculate()
                
                if result == {'FINISHED'}:
                    print("  Successfully calculated motion path")
                else:
                    print(f"  Operator returned: {result}")
                
            except Exception as e:
                print(f"  Error calculating motion path: {e}")
                print(f"  Error type: {type(e).__name__}")
                import traceback
                traceback.print_exc()
            
            # Restore scene frame range
            scene.frame_start = original_frame_start
            scene.frame_end = original_frame_end
            scene.frame_set(original_frame_current)
            
            # Restore previous selection
            bpy.context.view_layer.objects.active = previous_active
            for obj in previous_selected:
                obj.select_set(True)
            if motion_obj not in previous_selected:
                motion_obj.select_set(False)
            
            # Check if motion path was created
            motion_path = motion_obj.motion_path
            
            if motion_path is None:
                print(f"  Warning: Motion path still None after calculation")
                print(f"  This may indicate the object has no keyframes or animation")
            elif hasattr(motion_path, 'points') and motion_path.points and len(motion_path.points) > 0:
                print(f"  Motion path calculated successfully!")
                print(f"  Frame range: {motion_path.frame_start} to {motion_path.frame_end}")
                print(f"  Points: {len(motion_path.points)}")
            else:
                print(f"  Motion path calculated but has no points")
        
        elif motion_path.points and len(motion_path.points) > 0:
            print(f"Motion path available for {tgt_camera}")
            print(f"  Frame range: {motion_path.frame_start} to {motion_path.frame_end}")
            print(f"  Points: {len(motion_path.points)}")
        else:
            print(f"Warning: Motion path exists but has no points for {tgt_camera}")
            print("  Motion path may need animation data to calculate")
    else:
        print(f"Warning: Object {tgt_camera} has no animation data")
        print("  Motion path requires animation data to calculate")
        motion_path = None
    
    # Step 4: Access motion path and create curve
    # FIXED: Check both that motion_path is not None AND has points
    if (motion_path is not None and 
        hasattr(motion_path, 'points') and 
        motion_path.points and 
        len(motion_path.points) > 0):
        
        # Step 5: Create a new curve data block
        curve_data = bpy.data.curves.new(name="curve_path", type='CURVE')
        curve_data.dimensions = '3D'
        
        # Step 6: Create a NURBS spline
        spline = curve_data.splines.new('NURBS')
        # Add points (subtract 1 because one point already exists by default)
        spline.points.add(len(motion_path.points) - 1)
        
        # Step 7: Copy coordinates from motion path points to curve spline points
        for i, point in enumerate(motion_path.points):
            if i < len(spline.points):
                # Motion path points have 'co' attribute (x, y, z coordinates)
                # NURBS points need 4D coordinates (x, y, z, w), so add w=1.0
                spline.points[i].co = (*point.co, 1.0)
        
        # Step 8: Create the curve object and link it to the scene
        # Remove existing curve_path if it exists
        existing_curve = bpy.data.objects.get("curve_path")
        if existing_curve:
            bpy.data.objects.remove(existing_curve)
            print("Removed existing 'curve_path' object")
        
        curve_obj = bpy.data.objects.new("curve_path", curve_data)
        bpy.context.collection.objects.link(curve_obj)
        
        print(f"\nSuccessfully created curve object 'curve_path'")
        print(f"  Points: {len(motion_path.points)}")
        print(f"  Curve object instance ID: {curve_obj.as_pointer()}")
    else:
        print(f"\nError: Cannot create curve - motion path is not available")
        print(f"  motion_path is None: {motion_path is None if 'motion_path' in locals() else 'variable not set'}")
        if motion_path is not None:
            print(f"  motion_path.points exists: {hasattr(motion_path, 'points')}")
            if hasattr(motion_path, 'points'):
                print(f"  motion_path.points value: {motion_path.points}")
                print(f"  motion_path.points length: {len(motion_path.points) if motion_path.points else 0}")
else:
    print(f"Error: Object '{tgt_camera}' not found")
