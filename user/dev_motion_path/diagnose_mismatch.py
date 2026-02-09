import bpy

"""
Diagnostic script to identify mismatches between cam_0-96 and motion_curve_cam
Run this AFTER create_curve_and_camera_from_motion_path.py
"""

print("=" * 80)
print("CAMERA MISMATCH DIAGNOSTIC")
print("=" * 80)

cam_source = bpy.data.objects.get("cam_0-96")
cam_curve = bpy.data.objects.get("motion_curve_cam")
curve_path = bpy.data.objects.get("curve_path")

if not cam_source:
    print("ERROR: cam_0-96 not found")
    exit()
if not cam_curve:
    print("ERROR: motion_curve_cam not found")
    exit()
if not curve_path:
    print("ERROR: curve_path not found")
    exit()

# Get motion path info
motion_path = cam_source.motion_path
if motion_path:
    print(f"\nMotion Path Info:")
    print(f"  Frame range: {motion_path.frame_start} to {motion_path.frame_end}")
    print(f"  Points: {len(motion_path.points)}")
else:
    print("\nWARNING: No motion path found on cam_0-96")

# Get keyframes
keyframe_frames = []
if cam_source.animation_data and cam_source.animation_data.action:
    action = cam_source.animation_data.action
    for fcurve in action.fcurves:
        if fcurve.data_path == "location":
            for kf in fcurve.keyframe_points:
                frame = int(kf.co[0])
                if frame not in keyframe_frames:
                    keyframe_frames.append(frame)
    keyframe_frames = sorted(keyframe_frames)

print(f"\nKeyframes: {len(keyframe_frames)} frames from {min(keyframe_frames)} to {max(keyframe_frames)}")

# Get Follow Path constraint
follow_path_constraint = None
for constraint in cam_curve.constraints:
    if constraint.type == 'FOLLOW_PATH':
        follow_path_constraint = constraint
        break

if not follow_path_constraint:
    print("\nERROR: No Follow Path constraint found!")
    exit()

print(f"\nFollow Path Constraint:")
print(f"  Target: {follow_path_constraint.target.name if follow_path_constraint.target else 'None'}")
print(f"  Muted: {follow_path_constraint.mute}")
print(f"  Use Fixed Location: {follow_path_constraint.use_fixed_location}")
print(f"  Use Curve Follow: {follow_path_constraint.use_curve_follow}")
print(f"  Forward Axis: {follow_path_constraint.forward_axis}")
print(f"  Up Axis: {follow_path_constraint.up_axis}")
print(f"  Offset Factor (current): {follow_path_constraint.offset_factor}")
print(f"  Influence: {follow_path_constraint.influence}")

# Check if constraint target is valid
if follow_path_constraint.target:
    target_obj = follow_path_constraint.target
    print(f"\nConstraint Target Info:")
    print(f"  Name: {target_obj.name}")
    print(f"  Type: {target_obj.type}")
    if target_obj.type == 'CURVE':
        curve_data = target_obj.data
        print(f"  Dimensions: {curve_data.dimensions}")
        if curve_data.splines:
            spline = curve_data.splines[0]
            print(f"  Spline Type: {spline.type}")
            print(f"  Points: {len(spline.points)}")
            if len(spline.points) > 0:
                print(f"  First point: {spline.points[0].co[:3]}")
                print(f"  Last point: {spline.points[-1].co[:3]}")
else:
    print("\nERROR: Constraint has no target!")

# Get offset_factor animation
offset_fcurve = None
if cam_curve.animation_data and cam_curve.animation_data.action:
    action = cam_curve.animation_data.action
    for fcurve in action.fcurves:
        if 'offset_factor' in fcurve.data_path:
            offset_fcurve = fcurve
            break

if not offset_fcurve:
    print("\nERROR: No offset_factor animation found!")
    exit()

print(f"\nOffset Factor Animation:")
print(f"  Keyframes: {len(offset_fcurve.keyframe_points)}")
if len(offset_fcurve.keyframe_points) > 0:
    first_kf = offset_fcurve.keyframe_points[0]
    last_kf = offset_fcurve.keyframe_points[-1]
    print(f"  First: Frame {int(first_kf.co[0])}, offset={first_kf.co[1]:.4f}")
    print(f"  Last: Frame {int(last_kf.co[0])}, offset={last_kf.co[1]:.4f}")

# Test positions
scene = bpy.context.scene
original_frame = scene.frame_current

print("\n" + "=" * 80)
print("POSITION COMPARISON")
print("=" * 80)
print(f"{'Frame':<8} {'Source Pos':<40} {'Curve Pos':<40} {'Distance':<12} {'Offset':<10} {'Expected Offset':<15}")
print("-" * 130)

mismatches = []
test_frames = keyframe_frames[::max(1, len(keyframe_frames)//10)]  # Sample frames
if len(test_frames) == 0:
    test_frames = keyframe_frames[:10]

for frame in test_frames:
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    
    # Force dependency graph update to ensure constraint evaluates
    depsgraph = bpy.context.evaluated_depsgraph_get()
    cam_eval = cam_curve.evaluated_get(depsgraph)
    
    source_pos = cam_source.location.copy()
    curve_pos = cam_curve.location.copy()
    
    # Also get evaluated position
    curve_pos_eval = cam_eval.location.copy()
    
    distance = (source_pos - curve_pos).length
    distance_eval = (source_pos - curve_pos_eval).length
    
    # Get actual offset_factor
    actual_offset = offset_fcurve.evaluate(frame)
    
    # Also get constraint's current offset_factor
    constraint_offset = follow_path_constraint.offset_factor
    
    # Calculate expected offset_factor based on motion path
    if motion_path:
        motion_start = motion_path.frame_start
        motion_end = motion_path.frame_end
        motion_total = motion_end - motion_start + 1
        expected_offset = (frame - motion_start) / (motion_total - 1) if motion_total > 1 else 0.0
    else:
        expected_offset = None
    
    if distance > 0.1:  # Threshold for mismatch
        mismatches.append((frame, distance, actual_offset, expected_offset))
    
    if expected_offset is not None:
        expected_str = f"{expected_offset:.4f}"
    else:
        expected_str = "N/A"
    
    # Check if camera is stuck at origin
    origin_stuck = curve_pos.length < 0.001
    
    print(f"{frame:<8} ({source_pos.x:7.2f},{source_pos.y:7.2f},{source_pos.z:7.2f}) "
          f"({curve_pos.x:7.2f},{curve_pos.y:7.2f},{curve_pos.z:7.2f}) "
          f"{distance:<12.4f} {actual_offset:<10.4f} {expected_str:<15}", end="")
    
    if origin_stuck:
        print(" [STUCK AT ORIGIN!]")
    elif abs(actual_offset - constraint_offset) > 0.001:
        print(f" [Constraint offset={constraint_offset:.4f} differs from anim={actual_offset:.4f}]")
    else:
        print()

print("-" * 130)

if mismatches:
    print(f"\nFound {len(mismatches)} frames with distance > 0.1:")
    for frame, dist, actual, expected in mismatches[:5]:
        print(f"  Frame {frame}: distance={dist:.4f}, offset={actual:.4f}, expected={expected:.4f if expected else 'N/A'}")

# Analyze timing
print("\n" + "=" * 80)
print("TIMING ANALYSIS")
print("=" * 80)

if motion_path and len(keyframe_frames) > 1:
    motion_start = motion_path.frame_start
    motion_end = motion_path.frame_end
    key_start = min(keyframe_frames)
    key_end = max(keyframe_frames)
    
    print(f"Motion path range: {motion_start} to {motion_end}")
    print(f"Keyframe range: {key_start} to {key_end}")
    
    if key_start != motion_start or key_end != motion_end:
        print(f"\nMISMATCH DETECTED:")
        print(f"  Keyframes span {key_end - key_start + 1} frames")
        print(f"  Motion path spans {motion_end - motion_start + 1} frames")
        print(f"  Ratio: {(key_end - key_start + 1) / (motion_end - motion_start + 1):.4f}")
        print(f"\n  This means:")
        print(f"    - If offset_factor maps 0.0-1.0 over keyframe range:")
        print(f"      Last keyframe maps to offset_factor = 1.0")
        print(f"      But this corresponds to motion path point {(key_end - motion_start) / (motion_end - motion_start):.4f}")
        print(f"    - If offset_factor maps 0.0-1.0 over motion path range:")
        print(f"      Last keyframe maps to offset_factor = {(key_end - motion_start) / (motion_end - motion_start):.4f}")
        print(f"      This ensures correct position but may affect speed perception")

scene.frame_set(original_frame)
bpy.context.view_layer.update()

print("\n" + "=" * 80)
print("DIAGNOSIS COMPLETE")
print("=" * 80)
