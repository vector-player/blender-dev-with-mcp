import bpy
import mathutils

# Script: Create camera with Follow Path constraint
# Purpose: Creates a new camera "motion_curve_cam" with Follow Path constraint
#         that follows "curve_path" using keyframes from source camera

# Step 1: Assign variables
followpath_tgt = "curve_path"
keyframes_src = "cam_0-96"

# Step 2: Get the constraint target (curve) and keyframes source (camera)
curve_target = bpy.data.objects.get(followpath_tgt)
source_camera = bpy.data.objects.get(keyframes_src)

if not curve_target:
    print(f"Error: Curve target '{followpath_tgt}' not found")
elif not source_camera:
    print(f"Error: Source camera '{keyframes_src}' not found")
else:
    print(f"Found curve target: {followpath_tgt}")
    print(f"Found source camera: {keyframes_src}")
    
    # Step 3: Get keyframes from source camera
    keyframe_frames = []
    keyframe_positions = {}
    
    if source_camera.animation_data and source_camera.animation_data.action:
        action = source_camera.animation_data.action
        
        # Get all keyframe frames from location channels
        for fcurve in action.fcurves:
            if fcurve.data_path == "location":
                for kf in fcurve.keyframe_points:
                    frame = int(kf.co[0])
                    if frame not in keyframe_frames:
                        keyframe_frames.append(frame)
        
        keyframe_frames = sorted(keyframe_frames)
        print(f"Found {len(keyframe_frames)} keyframe frames")
        
        # Get positions at each keyframe
        for frame in keyframe_frames:
            # Evaluate camera location at this frame
            bpy.context.scene.frame_set(frame)
            bpy.context.view_layer.update()
            location = source_camera.location.copy()
            keyframe_positions[frame] = location
    
    if not keyframe_frames:
        print(f"Warning: No keyframes found on {keyframes_src}")
    else:
        # Step 4: Create new camera "motion_curve_cam"
        # Remove existing camera if it exists
        existing_cam = bpy.data.objects.get("motion_curve_cam")
        if existing_cam:
            bpy.data.objects.remove(existing_cam)
            print("Removed existing 'motion_curve_cam'")
        
        # Create camera data
        cam_data = bpy.data.cameras.new(name="motion_curve_cam")
        motion_curve_cam = bpy.data.objects.new("motion_curve_cam", cam_data)
        bpy.context.collection.objects.link(motion_curve_cam)
        print("Created camera 'motion_curve_cam'")
        
        # Step 5: Add Follow Path constraint
        # Remove existing Follow Path constraint if any
        for constraint in list(motion_curve_cam.constraints):
            if constraint.type == 'FOLLOW_PATH':
                motion_curve_cam.constraints.remove(constraint)
        
        # Add Follow Path constraint
        follow_path_constraint = motion_curve_cam.constraints.new(type='FOLLOW_PATH')
        follow_path_constraint.name = "Follow Path"
        
        # Step 6: Configure constraint properties
        follow_path_constraint.target = curve_target
        follow_path_constraint.forward_axis = 'FORWARD_X'  # Forward Axis: X
        follow_path_constraint.up_axis = 'UP_Z'  # Up Axis: Z
        follow_path_constraint.use_fixed_location = True  # Fixed Position: enabled
        follow_path_constraint.use_curve_follow = True  # Follow Curve: enabled
        
        print("Configured Follow Path constraint:")
        print(f"  Target: {followpath_tgt}")
        print(f"  Forward Axis: X")
        print(f"  Up Axis: Z")
        print(f"  Fixed Position: enabled")
        print(f"  Follow Curve: enabled")
        
        # Step 7: Create keyframes on Offset Factor
        # Map keyframe positions to offset_factor values (0.0 to 1.0)
        # The offset_factor should correspond to where each keyframe frame falls
        # within the motion path range (since curve_path was created from motion path)
        
        # Get motion path frame range and points from source camera
        # This represents the full range that the curve_path covers
        motion_path_frame_start = 1
        motion_path_frame_end = 961
        motion_path_points = None
        
        if source_camera.animation_data:
            # Try to get motion path frame range and points
            motion_path = source_camera.motion_path
            if motion_path is not None:
                motion_path_frame_start = motion_path.frame_start
                motion_path_frame_end = motion_path.frame_end
                motion_path_points = motion_path.points
            elif source_camera.animation_data.action:
                # Fallback to action frame range
                if source_camera.animation_data.action.frame_range:
                    motion_path_frame_start = int(source_camera.animation_data.action.frame_range[0])
                    motion_path_frame_end = int(source_camera.animation_data.action.frame_range[1])
        
        # Calculate total frames (inclusive range)
        motion_path_total_frames = motion_path_frame_end - motion_path_frame_start + 1
        
        # Get number of points in the curve (should match motion path points)
        curve_point_count = 0
        if curve_target.data.splines:
            curve_point_count = len(curve_target.data.splines[0].points)
        
        print(f"Motion path info:")
        print(f"  Frame range: {motion_path_frame_start} to {motion_path_frame_end}")
        print(f"  Motion path points: {len(motion_path_points) if motion_path_points else 0}")
        print(f"  Curve points: {curve_point_count}")
        
        # Step 7: Create keyframes on Offset Factor
        # Use keyframe_insert directly on the constraint property for reliable keyframe creation
        
        # Ensure camera has animation_data (required for keyframe_insert)
        if not motion_curve_cam.animation_data:
            motion_curve_cam.animation_data_create()
        
        # Create and assign action before inserting keyframes
        # This ensures the action is properly linked to the camera
        action_name = "motion_curve_cam_Action"
        
        # Remove existing action if it exists
        if motion_curve_cam.animation_data.action:
            existing_action = motion_curve_cam.animation_data.action
            # Don't remove if it's the one we want to use
            if existing_action.name != action_name:
                bpy.data.actions.remove(existing_action)
        
        # Create or get the action
        if action_name in bpy.data.actions:
            action = bpy.data.actions[action_name]
        else:
            action = bpy.data.actions.new(name=action_name)
        
        # Assign action to camera
        motion_curve_cam.animation_data.action = action
        
        # Map each keyframe to offset_factor based on motion path frame range
        if keyframe_frames:
            print(f"\nCreating offset_factor keyframes:")
            print(f"  Motion path frame range: {motion_path_frame_start} to {motion_path_frame_end}")
            print(f"  Keyframe frames: {min(keyframe_frames)} to {max(keyframe_frames)}")
            
            # Store current frame and active object to restore later
            scene = bpy.context.scene
            original_frame = scene.frame_current
            original_active = bpy.context.view_layer.objects.active
            
            # Set camera as active (required for keyframe_insert to work properly)
            bpy.context.view_layer.objects.active = motion_curve_cam
            
            # CRITICAL FIX: Map offset_factor based on CUMULATIVE DISTANCE traveled, not frame numbers!
            # The issue: cam_0-96 moves at varying speeds (fast in some frames, slow in others)
            # But we were mapping frames linearly to offset_factor, causing even movement along curve
            # Solution: Calculate cumulative distance along motion path and map offset_factor based on that
            
            keyframe_frame_start = min(keyframe_frames) if keyframe_frames else motion_path_frame_start
            keyframe_frame_end = max(keyframe_frames) if keyframe_frames else motion_path_frame_end
            
            print(f"  Motion path frame range: {motion_path_frame_start} to {motion_path_frame_end} ({motion_path_total_frames} frames)")
            print(f"  Keyframe range: {keyframe_frame_start} to {keyframe_frame_end}")
            
            # Calculate cumulative distances along motion path for each keyframe
            # This preserves the actual speed variations of cam_0-96
            print(f"  Calculating cumulative distances along motion path...")
            
            # Get motion path points if available
            motion_path = source_camera.motion_path
            cumulative_distances = {}
            total_distance = 0.0
            
            if motion_path and motion_path.points:
                # Use motion path points directly (more efficient and accurate)
                motion_path_points = motion_path.points
                num_points = len(motion_path_points)
                
                prev_pos = None
                for i, point in enumerate(motion_path_points):
                    # Map point index to frame number
                    # Point 0 = frame_start, Point (N-1) = frame_end
                    if num_points > 1:
                        frame = motion_path_frame_start + int((i / (num_points - 1)) * (motion_path_frame_end - motion_path_frame_start))
                    else:
                        frame = motion_path_frame_start
                    
                    current_pos = mathutils.Vector(point.co)
                    
                    if prev_pos is not None:
                        segment_distance = (current_pos - prev_pos).length
                        total_distance += segment_distance
                    
                    cumulative_distances[frame] = total_distance
                    prev_pos = current_pos
                
                # Also calculate for exact frame_end
                if motion_path_frame_end not in cumulative_distances and len(motion_path_points) > 0:
                    cumulative_distances[motion_path_frame_end] = total_distance
            else:
                # Fallback: evaluate at each frame
                prev_pos = None
                for frame in range(motion_path_frame_start, motion_path_frame_end + 1):
                    scene.frame_set(frame)
                    bpy.context.view_layer.update()
                    current_pos = source_camera.location.copy()
                    
                    if prev_pos is not None:
                        segment_distance = (current_pos - prev_pos).length
                        total_distance += segment_distance
                    
                    cumulative_distances[frame] = total_distance
                    prev_pos = current_pos
            
            print(f"  Total distance along motion path: {total_distance:.4f}")
            
            for frame in keyframe_frames:
                # Get the original camera position at this keyframe
                target_position = keyframe_positions.get(frame)
                
                # CRITICAL FIX: Map based on cumulative distance, not frame number
                # This ensures motion_curve_cam moves at the same speed as cam_0-96
                # Find the closest frame in cumulative_distances
                frame_distance = None
                if frame in cumulative_distances:
                    frame_distance = cumulative_distances[frame]
                else:
                    # Interpolate between nearest frames
                    sorted_frames = sorted(cumulative_distances.keys())
                    if sorted_frames:
                        if frame < sorted_frames[0]:
                            frame_distance = cumulative_distances[sorted_frames[0]]
                        elif frame > sorted_frames[-1]:
                            frame_distance = cumulative_distances[sorted_frames[-1]]
                        else:
                            # Find frames to interpolate between
                            for i in range(len(sorted_frames) - 1):
                                if sorted_frames[i] <= frame <= sorted_frames[i+1]:
                                    f1, f2 = sorted_frames[i], sorted_frames[i+1]
                                    d1, d2 = cumulative_distances[f1], cumulative_distances[f2]
                                    if f2 > f1:
                                        t = (frame - f1) / (f2 - f1)
                                        frame_distance = d1 + t * (d2 - d1)
                                    else:
                                        frame_distance = d1
                                    break
                
                if frame_distance is not None and total_distance > 0.0:
                    offset_factor = frame_distance / total_distance
                else:
                    # Fallback to frame-based mapping if distance not available
                    if motion_path_total_frames > 1:
                        offset_factor = (frame - motion_path_frame_start) / (motion_path_total_frames - 1)
                    else:
                        offset_factor = 0.0
                
                # Ensure exact endpoints
                if frame == motion_path_frame_start:
                    offset_factor = 0.0
                elif frame >= motion_path_frame_end:
                    offset_factor = 1.0
                
                offset_factor = max(0.0, min(1.0, offset_factor))
                
                # Verify position match for debugging
                if target_position:
                    original_offset = follow_path_constraint.offset_factor
                    follow_path_constraint.offset_factor = offset_factor
                    bpy.context.view_layer.update()
                    cam_pos = motion_curve_cam.location.copy()
                    distance = (target_position - cam_pos).length
                    follow_path_constraint.offset_factor = original_offset
                    print(f"  Frame {frame}: offset_factor = {offset_factor:.4f} (distance: {distance:.4f})")
                else:
                    print(f"  Frame {frame}: offset_factor = {offset_factor:.4f}")
                
                # Set frame and constraint value
                scene.frame_set(frame)
                
                # Set the constraint's offset_factor value
                follow_path_constraint.offset_factor = offset_factor
                
                # CRITICAL FIX: Insert keyframe using the full data path
                # Use the object's keyframe_insert with full constraint path for reliability
                motion_curve_cam.keyframe_insert(
                    data_path=f'constraints["{follow_path_constraint.name}"].offset_factor',
                    frame=frame
                )
                
                print(f"  Frame {frame}: offset_factor = {offset_factor:.4f}")
            
            # Verify the action is assigned and has keyframes
            if motion_curve_cam.animation_data and motion_curve_cam.animation_data.action:
                action = motion_curve_cam.animation_data.action
                print(f"\nAction '{action.name}' is assigned to camera")
                print(f"  Action has {len(action.fcurves)} fcurves")
                
                # Count total keyframes
                total_keyframes = 0
                for fcurve in action.fcurves:
                    if 'offset_factor' in fcurve.data_path:
                        total_keyframes += len(fcurve.keyframe_points)
                        print(f"  Found offset_factor fcurve with {len(fcurve.keyframe_points)} keyframes")
                
                if total_keyframes == 0:
                    print(f"  WARNING: No keyframes found in action!")
            else:
                print(f"\nERROR: Action not assigned to camera after keyframe insertion")
            
            # CRITICAL FIX: Activate Follow Path constraint animation using operator
            # This is equivalent to pressing "Animate Path" button in Blender UI
            # Without this, the constraint won't use the animated offset_factor
            
            # Ensure constraint is enabled and properly configured
            follow_path_constraint.mute = False
            
            # Set camera as active and selected (required for operator)
            bpy.context.view_layer.objects.active = motion_curve_cam
            motion_curve_cam.select_set(True)
            
            # Call the operator to activate path animation
            # This makes the constraint use the animated offset_factor keyframes
            try:
                result = bpy.ops.constraint.followpath_path_animate(
                    constraint=follow_path_constraint.name,
                    owner='OBJECT'
                )
                if result == {'FINISHED'}:
                    print("  Successfully activated Follow Path constraint animation")
                else:
                    print(f"  Warning: Operator returned: {result}")
            except Exception as e:
                print(f"  Error activating path animation: {e}")
                import traceback
                traceback.print_exc()
            
            # Verify the action and fcurves are properly set up
            if motion_curve_cam.animation_data and motion_curve_cam.animation_data.action:
                action = motion_curve_cam.animation_data.action
                # Ensure action is not fake user (so it persists)
                action.use_fake_user = False
                print("  Constraint animation setup complete")
            
            # Restore original frame and active object
            scene.frame_set(original_frame)
            bpy.context.view_layer.objects.active = original_active
            motion_curve_cam.select_set(False)
            
            # Update view layer to ensure keyframes are committed
            bpy.context.view_layer.update()
        
        print(f"\nSuccessfully created {len(keyframe_frames)} offset_factor keyframes")
        print(f"Camera 'motion_curve_cam' is ready with Follow Path constraint")
        print(f"Animation should be active - scrub timeline to verify")
