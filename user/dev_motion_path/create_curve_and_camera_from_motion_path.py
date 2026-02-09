import bpy
import mathutils


def get_animation_frame_range(obj):
    """
    Get the frame range from an object's animation data.
    
    Args:
        obj: Blender object with animation data
        
    Returns:
        tuple: (frame_start, frame_end)
    """
    frame_start = 1
    frame_end = 100
    
    if obj.animation_data and obj.animation_data.action:
        if obj.animation_data.action.frame_range:
            frame_start = int(obj.animation_data.action.frame_range[0])
            frame_end = int(obj.animation_data.action.frame_range[1])
        else:
            scene = bpy.context.scene
            frame_start = scene.frame_start
            frame_end = scene.frame_end
    else:
        scene = bpy.context.scene
        frame_start = scene.frame_start
        frame_end = scene.frame_end
    
    return frame_start, frame_end


def calculate_motion_path(obj):
    """
    Calculate motion path for an object if it doesn't exist.
    
    Args:
        obj: Blender object with animation data
        
    Returns:
        MotionPath or None: The calculated motion path
    """
    if not obj.animation_data:
        return None
    
    motion_path = obj.motion_path
    
    if motion_path is None:
        print(f"Motion path is None for {obj.name} - calculating motion path...")
        
        # Get frame range from animation action
        frame_start, frame_end = get_animation_frame_range(obj)
        print(f"  Animation frame range: {frame_start} to {frame_end}")
        
        # Store previous context
        previous_active = bpy.context.view_layer.objects.active
        previous_selected = list(bpy.context.selected_objects)
        
        # Select and activate the motion object
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        
        for other_obj in list(bpy.context.selected_objects):
            if other_obj != obj:
                other_obj.select_set(False)
        
        # Set scene frame range to match animation
        scene = bpy.context.scene
        original_frame_start = scene.frame_start
        original_frame_end = scene.frame_end
        original_frame_current = scene.frame_current
        
        scene.frame_start = frame_start
        scene.frame_end = frame_end
        scene.frame_set(frame_start)
        bpy.context.view_layer.update()
        
        try:
            bpy.ops.object.paths_clear()
            print("  Cleared existing motion paths")
        except Exception as e:
            print(f"  Note: Clear operation: {e}")
        
        try:
            result = bpy.ops.object.paths_calculate()
            if result == {'FINISHED'}:
                print("  Successfully calculated motion path")
        except Exception as e:
            print(f"  Error calculating motion path: {e}")
            import traceback
            traceback.print_exc()
        
        # Restore scene frame range
        scene.frame_start = original_frame_start
        scene.frame_end = original_frame_end
        scene.frame_set(original_frame_current)
        
        # Restore previous selection
        bpy.context.view_layer.objects.active = previous_active
        for other_obj in previous_selected:
            other_obj.select_set(True)
        if obj not in previous_selected:
            obj.select_set(False)
        
        # Check if motion path was created
        motion_path = obj.motion_path
    
    return motion_path


def create_curve_from_motion_path(motion_path, curve_name="curve_path"):
    """
    Create a NURBS curve from motion path points.
    
    Args:
        motion_path: MotionPath object with points
        curve_name: Name for the curve object
        
    Returns:
        bpy.types.Object: The created curve object, or None if motion path is invalid
    """
    if motion_path is None or not motion_path.points or len(motion_path.points) == 0:
        print("Error: Motion path has no points")
        return None
    
    motion_path_frame_start = motion_path.frame_start
    motion_path_frame_end = motion_path.frame_end
    motion_path_points = motion_path.points
    num_motion_path_points = len(motion_path_points)
    
    print(f"\nMotion path info:")
    print(f"  Frame range: {motion_path_frame_start} to {motion_path_frame_end}")
    print(f"  Points: {num_motion_path_points}")
    
    # Create curve from motion path points
    curve_data = bpy.data.curves.new(name=curve_name, type='CURVE')
    curve_data.dimensions = '3D'
    
    spline = curve_data.splines.new('NURBS')
    spline.points.add(num_motion_path_points - 1)
    
    for i, point in enumerate(motion_path_points):
        if i < len(spline.points):
            spline.points[i].co = (*point.co, 1.0)
    
    # Remove existing curve if it exists
    existing_curve = bpy.data.objects.get(curve_name)
    if existing_curve:
        bpy.data.objects.remove(existing_curve)
        print(f"Removed existing '{curve_name}' object")
    
    curve_obj = bpy.data.objects.new(curve_name, curve_data)
    bpy.context.collection.objects.link(curve_obj)
    print(f"Created curve object '{curve_name}' with {num_motion_path_points} points")
    
    return curve_obj


def extract_keyframes(obj):
    """
    Extract keyframe frames and positions from an object's animation.
    
    Args:
        obj: Blender object with animation data
        
    Returns:
        tuple: (keyframe_frames list, keyframe_positions dict)
    """
    keyframe_frames = []
    keyframe_positions = {}
    
    if obj.animation_data and obj.animation_data.action:
        action = obj.animation_data.action
        
        for fcurve in action.fcurves:
            if fcurve.data_path == "location":
                for kf in fcurve.keyframe_points:
                    frame = int(kf.co[0])
                    if frame not in keyframe_frames:
                        keyframe_frames.append(frame)
        
        keyframe_frames = sorted(keyframe_frames)
        print(f"\nFound {len(keyframe_frames)} keyframe frames")
        
        # Get positions at each keyframe
        for frame in keyframe_frames:
            bpy.context.scene.frame_set(frame)
            bpy.context.view_layer.update()
            location = obj.location.copy()
            keyframe_positions[frame] = location
    
    return keyframe_frames, keyframe_positions


def calculate_cumulative_distances(motion_path):
    """
    Calculate cumulative distances along motion path for each frame.
    
    This preserves speed variations by mapping based on distance traveled
    rather than frame numbers.
    
    Args:
        motion_path: MotionPath object with points
        
    Returns:
        tuple: (cumulative_distances dict, total_distance float)
    """
    if motion_path is None or not motion_path.points:
        return {}, 0.0
    
    motion_path_frame_start = motion_path.frame_start
    motion_path_frame_end = motion_path.frame_end
    motion_path_points = motion_path.points
    num_motion_path_points = len(motion_path_points)
    
    cumulative_distances = {}
    total_distance = 0.0
    
    print(f"  Calculating cumulative distances along motion path...")
    
    # Use motion path points directly (more efficient and accurate)
    # Motion path points correspond to frames from frame_start to frame_end
    prev_pos = None
    for i, point in enumerate(motion_path_points):
        # Map point index to frame number
        # Point 0 = frame_start, Point (N-1) = frame_end
        if num_motion_path_points > 1:
            frame = motion_path_frame_start + int(
                (i / (num_motion_path_points - 1)) * 
                (motion_path_frame_end - motion_path_frame_start)
            )
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
    
    print(f"  Total distance along motion path: {total_distance:.4f}")
    
    return cumulative_distances, total_distance


def create_trackto_target(target_name="trackto_tgt"):
    """
    Create an empty object to serve as Track To constraint target.
    
    Args:
        target_name: Name for the empty object
        
    Returns:
        bpy.types.Object: The created empty object, or None if creation failed
    """
    # Remove existing object if it exists
    existing_obj = bpy.data.objects.get(target_name)
    if existing_obj:
        bpy.data.objects.remove(existing_obj)
        print(f"Removed existing '{target_name}' object")
    
    # Create new empty object
    empty_data = bpy.data.objects.new(target_name, None)
    bpy.context.collection.objects.link(empty_data)
    print(f"Created empty object '{target_name}'")
    
    return empty_data


def copy_camera_focal_length(source_camera_obj, target_camera_obj):
    """
    Copy focal length from source camera to target camera.
    
    Args:
        source_camera_obj: Source camera object to copy from
        target_camera_obj: Target camera object to copy to
    """
    if not source_camera_obj or not target_camera_obj:
        return
    
    if source_camera_obj.type != 'CAMERA' or target_camera_obj.type != 'CAMERA':
        print("Warning: Both objects must be cameras to copy focal length")
        return
    
    source_cam_data = source_camera_obj.data
    target_cam_data = target_camera_obj.data
    
    if source_cam_data and target_cam_data:
        target_cam_data.lens = source_cam_data.lens
        print(f"Copied focal length: {source_cam_data.lens}mm from '{source_camera_obj.name}' to '{target_camera_obj.name}'")


def create_camera_with_constraint(camera_name, curve_obj, source_camera_obj=None, track_to_target=None):
    """
    Create a camera with Follow Path constraint targeting a curve.
    
    Args:
        camera_name: Name for the camera object
        curve_obj: Curve object to follow
        source_camera_obj: Optional source camera object to copy focal length from
        track_to_target: Optional empty object to use as Track To constraint target
        
    Returns:
        tuple: (camera_object, follow_path_constraint)
    """
    # Remove existing camera if it exists
    existing_cam = bpy.data.objects.get(camera_name)
    if existing_cam:
        bpy.data.objects.remove(existing_cam)
        print(f"Removed existing '{camera_name}'")
    
    # Create new camera
    cam_data = bpy.data.cameras.new(name=camera_name)
    motion_curve_cam = bpy.data.objects.new(camera_name, cam_data)
    bpy.context.collection.objects.link(motion_curve_cam)
    print(f"Created camera '{camera_name}'")
    
    # Copy focal length from source camera if provided
    if source_camera_obj:
        copy_camera_focal_length(source_camera_obj, motion_curve_cam)
    
    # Remove existing Follow Path constraints
    for constraint in list(motion_curve_cam.constraints):
        if constraint.type == 'FOLLOW_PATH':
            motion_curve_cam.constraints.remove(constraint)
    
    # Remove existing Track To constraints
    for constraint in list(motion_curve_cam.constraints):
        if constraint.type == 'TRACK_TO':
            motion_curve_cam.constraints.remove(constraint)
    
    # Add Follow Path constraint
    follow_path_constraint = motion_curve_cam.constraints.new(type='FOLLOW_PATH')
    follow_path_constraint.name = "Follow Path"
    # Type ignore: Blender API dynamic attributes
    follow_path_constraint.target = curve_obj  # type: ignore
    follow_path_constraint.forward_axis = 'FORWARD_X'  # type: ignore
    follow_path_constraint.up_axis = 'UP_Z'  # type: ignore
    follow_path_constraint.use_fixed_location = True  # type: ignore
    follow_path_constraint.use_curve_follow = True  # type: ignore
    
    print("Configured Follow Path constraint")
    
    # Add Track To constraint if target provided
    if track_to_target:
        track_to_constraint = motion_curve_cam.constraints.new(type='TRACK_TO')
        track_to_constraint.name = "Track To"
        # Type ignore: Blender API dynamic attributes
        track_to_constraint.target = track_to_target  # type: ignore
        track_to_constraint.track_axis = 'TRACK_NEGATIVE_Z'  # type: ignore
        track_to_constraint.up_axis = 'UP_Y'  # type: ignore
        print(f"Configured Track To constraint targeting '{track_to_target.name}'")
    
    # Create animation data
    if not motion_curve_cam.animation_data:
        motion_curve_cam.animation_data_create()
    
    action_name = f"{camera_name}_Action"
    if motion_curve_cam.animation_data.action:
        existing_action = motion_curve_cam.animation_data.action
        if existing_action.name != action_name:
            bpy.data.actions.remove(existing_action)
    
    action = bpy.data.actions.get(action_name)
    if action is None:
        action = bpy.data.actions.new(name=action_name)
    
    motion_curve_cam.animation_data.action = action
    
    return motion_curve_cam, follow_path_constraint


def create_offset_factor_keyframes(camera_obj, constraint, keyframe_frames, 
                                   cumulative_distances, total_distance, 
                                   motion_path_info, keyframe_positions=None):
    """
    Create offset_factor keyframes for Follow Path constraint based on cumulative distances.
    
    This preserves speed variations by mapping based on distance traveled rather than
    frame numbers.
    
    Args:
        camera_obj: Camera object with constraint
        constraint: Follow Path constraint
        keyframe_frames: List of frame numbers to create keyframes at
        cumulative_distances: Dict mapping frame -> cumulative distance
        total_distance: Total distance along motion path
        motion_path_info: Dict with 'frame_start', 'frame_end', 'total_frames', 'num_points'
        keyframe_positions: Optional dict mapping frame -> position for verification
    """
    motion_path_frame_start = motion_path_info['frame_start']
    motion_path_frame_end = motion_path_info['frame_end']
    motion_path_total_frames = motion_path_info['total_frames']
    num_motion_path_points = motion_path_info['num_points']
    
    print(f"\nCreating offset_factor keyframes:")
    print(f"  Motion path: frames {motion_path_frame_start} to {motion_path_frame_end} ({motion_path_total_frames} frames)")
    print(f"  Motion path points: {num_motion_path_points}")
    print(f"  Keyframes: frames {min(keyframe_frames)} to {max(keyframe_frames)} ({len(keyframe_frames)} keyframes)")
    
    # Analyze keyframe spacing
    if len(keyframe_frames) > 1:
        keyframe_intervals = [keyframe_frames[i+1] - keyframe_frames[i] 
                             for i in range(len(keyframe_frames)-1)]
        avg_interval = sum(keyframe_intervals) / len(keyframe_intervals)
        min_interval = min(keyframe_intervals)
        max_interval = max(keyframe_intervals)
        print(f"  Keyframe spacing: min={min_interval}, max={max_interval}, avg={avg_interval:.2f}")
        if min_interval != max_interval:
            print(f"  WARNING: Keyframes are NOT evenly spaced! This affects timing.")
            print(f"  First few intervals: {keyframe_intervals[:10]}")
    
    # Store context
    scene = bpy.context.scene
    original_frame = scene.frame_current
    original_active = bpy.context.view_layer.objects.active
    
    bpy.context.view_layer.objects.active = camera_obj
    
    # Store offset_factor values for analysis
    offset_factors = []
    
    for frame in keyframe_frames:
        # Map based on cumulative distance, not frame number
        # This ensures motion_curve_cam moves at the same speed as source camera
        # Find the closest frame in cumulative_distances
        frame_distance = None
        if frame in cumulative_distances:
            frame_distance = cumulative_distances[frame]
        else:
            # Interpolate between nearest frames
            sorted_frames = sorted(cumulative_distances.keys())
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
        offset_factors.append((frame, offset_factor))
        
        # Calculate point index for verification/debugging
        if num_motion_path_points > 1:
            point_index = int(
                (frame - motion_path_frame_start) / (motion_path_total_frames - 1) * 
                (num_motion_path_points - 1)
            )
            point_index = max(0, min(num_motion_path_points - 1, point_index))
        else:
            point_index = 0
        
        # Set frame and insert keyframe
        scene.frame_set(frame)
        constraint.offset_factor = offset_factor
        
        # Insert keyframe using the full data path
        camera_obj.keyframe_insert(
            data_path=f'constraints["{constraint.name}"].offset_factor',
            frame=frame
        )
        
        # Verify position match if positions provided
        if keyframe_positions:
            target_position = keyframe_positions.get(frame)
            if target_position:
                bpy.context.view_layer.update()
                cam_pos = camera_obj.location.copy()
                distance = (target_position - cam_pos).length
                print(f"  Frame {frame}: offset_factor = {offset_factor:.4f} (point {point_index}/{num_motion_path_points-1}, distance: {distance:.4f})")
            else:
                print(f"  Frame {frame}: offset_factor = {offset_factor:.4f} (point {point_index}/{num_motion_path_points-1})")
        else:
            print(f"  Frame {frame}: offset_factor = {offset_factor:.4f} (point {point_index}/{num_motion_path_points-1})")
    
    # Analyze offset_factor spacing
    if len(offset_factors) > 1:
        offset_intervals = [offset_factors[i+1][1] - offset_factors[i][1] 
                           for i in range(len(offset_factors)-1)]
        frame_intervals = [offset_factors[i+1][0] - offset_factors[i][0] 
                          for i in range(len(offset_factors)-1)]
        print(f"\n  Offset factor analysis:")
        print(f"    First few: frame={offset_factors[0][0]}, offset={offset_factors[0][1]:.4f}")
        print(f"    Last few: frame={offset_factors[-1][0]}, offset={offset_factors[-1][1]:.4f}")
        print(f"    Offset intervals: min={min(offset_intervals):.4f}, max={max(offset_intervals):.4f}, avg={sum(offset_intervals)/len(offset_intervals):.4f}")
        if min(offset_intervals) != max(offset_intervals):
            print(f"    WARNING: Offset factors are NOT evenly spaced!")
            print(f"    First few offset intervals: {[f'{x:.4f}' for x in offset_intervals[:10]]}")
            print(f"    Corresponding frame intervals: {frame_intervals[:10]}")
            print(f"    This means keyframes preserve non-uniform timing - GOOD!")
    
    # Restore context
    scene.frame_set(original_frame)
    bpy.context.view_layer.objects.active = original_active
    if camera_obj:
        camera_obj.select_set(False)
    bpy.context.view_layer.update()
    
    print(f"\nSuccessfully created {len(keyframe_frames)} offset_factor keyframes")
    
    return offset_factors


def activate_constraint_animation(camera_obj, constraint):
    """
    Activate Follow Path constraint animation using Blender operator.
    
    This is equivalent to pressing "Animate Path" button in Blender UI.
    Without this, the constraint won't use the animated offset_factor.
    
    Args:
        camera_obj: Camera object with constraint
        constraint: Follow Path constraint to activate
    """
    # Ensure constraint is enabled and properly configured
    constraint.mute = False
    
    # Set camera as active and selected (required for operator)
    bpy.context.view_layer.objects.active = camera_obj
    camera_obj.select_set(True)
    
    # Call the operator to activate path animation
    # This makes the constraint use the animated offset_factor keyframes
    try:
        result = bpy.ops.constraint.followpath_path_animate(
            constraint=constraint.name,
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
    if camera_obj.animation_data and camera_obj.animation_data.action:
        action = camera_obj.animation_data.action
        # Ensure action is not fake user (so it persists)
        action.use_fake_user = False
        print("  Constraint animation setup complete")
    
    # Restore selection
    camera_obj.select_set(False)
    bpy.context.view_layer.update()


def main(tgt_camera="cam_0-96", curve_name="curve_path", camera_name="motion_curve_cam"):
    """
    Main function: Create curve from motion path and camera with Follow Path constraint.
    
    Args:
        tgt_camera: Name of source object with animation
        curve_name: Name for the created curve
        camera_name: Name for the created camera
    """
    # Get the source object
    motion_obj = bpy.data.objects.get(tgt_camera)
    
    if not motion_obj:
        print(f"Error: Object '{tgt_camera}' not found")
        return
    
    print(f"Processing object: {tgt_camera}")
    
    # Part 1: Create motion path and curve
    if not motion_obj.animation_data:
        print(f"Warning: Object {tgt_camera} has no animation data")
        return
    
    # Calculate motion path if needed
    motion_path = calculate_motion_path(motion_obj)
    
    if motion_path is None:
        print("Error: Could not calculate motion path")
        return
    
    # Create curve from motion path
    curve_obj = create_curve_from_motion_path(motion_path, curve_name)
    
    if curve_obj is None:
        print("Error: Could not create curve")
        return
    
    # Part 2: Create camera with Follow Path constraint
    # Extract keyframes
    keyframe_frames, keyframe_positions = extract_keyframes(motion_obj)
    
    if not keyframe_frames:
        print("Warning: No keyframes found")
        return
    
    # Calculate cumulative distances
    cumulative_distances, total_distance = calculate_cumulative_distances(motion_path)
    
    # Create empty object for Track To constraint target
    trackto_tgt = create_trackto_target("trackto_tgt")
    
    # Create camera with constraint
    motion_curve_cam, follow_path_constraint = create_camera_with_constraint(
        camera_name, curve_obj, source_camera_obj=motion_obj, track_to_target=trackto_tgt
    )
    
    # Prepare motion path info
    motion_path_info = {
        'frame_start': motion_path.frame_start,
        'frame_end': motion_path.frame_end,
        'total_frames': motion_path.frame_end - motion_path.frame_start + 1,
        'num_points': len(motion_path.points)
    }
    
    # Create offset_factor keyframes
    create_offset_factor_keyframes(
        motion_curve_cam,
        follow_path_constraint,
        keyframe_frames,
        cumulative_distances,
        total_distance,
        motion_path_info,
        keyframe_positions
    )
    
    # Activate constraint animation
    activate_constraint_animation(motion_curve_cam, follow_path_constraint)
    
    print(f"\nCamera '{camera_name}' is ready with Follow Path constraint")
    print(f"Animation should be active - scrub timeline to verify")


# Script execution
if __name__ == "__main__":
    # Configuration variables
    tgt_camera = "cam_0-96"
    followpath_tgt = "curve_path"
    camera_name = "motion_curve_cam"
    
    main(tgt_camera=tgt_camera, curve_name=followpath_tgt, camera_name=camera_name)
