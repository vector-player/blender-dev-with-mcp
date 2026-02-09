import bpy

# Test script to find mismatches between cam_0-96 and motion_curve_cam
# Run this after create_curve_and_camera_from_motion_path.py

cam_source = bpy.data.objects.get("cam_0-96")
cam_curve = bpy.data.objects.get("motion_curve_cam")

if not cam_source:
    print("ERROR: cam_0-96 not found")
elif not cam_curve:
    print("ERROR: motion_curve_cam not found")
else:
    print("=" * 80)
    print("CAMERA POSITION COMPARISON TEST")
    print("=" * 80)
    
    # Get keyframes from source camera
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
    
    print(f"\nFound {len(keyframe_frames)} keyframes")
    print(f"Frame range: {min(keyframe_frames)} to {max(keyframe_frames)}")
    
    # Check constraint setup
    follow_path_constraint = None
    for constraint in cam_curve.constraints:
        if constraint.type == 'FOLLOW_PATH':
            follow_path_constraint = constraint
            break
    
    if not follow_path_constraint:
        print("\nERROR: motion_curve_cam has no Follow Path constraint!")
    else:
        print(f"\nFollow Path constraint found:")
        print(f"  Target: {follow_path_constraint.target.name if follow_path_constraint.target else 'None'}")
        print(f"  Muted: {follow_path_constraint.mute}")
        print(f"  Use Fixed Location: {follow_path_constraint.use_fixed_location}")
        print(f"  Use Curve Follow: {follow_path_constraint.use_curve_follow}")
        
        # Check animation data
        if cam_curve.animation_data and cam_curve.animation_data.action:
            action = cam_curve.animation_data.action
            print(f"\nAnimation action: {action.name}")
            print(f"  FCurves: {len(action.fcurves)}")
            
            # Find offset_factor fcurve
            offset_fcurve = None
            for fcurve in action.fcurves:
                if 'offset_factor' in fcurve.data_path:
                    offset_fcurve = fcurve
                    print(f"  Found offset_factor fcurve: {len(fcurve.keyframe_points)} keyframes")
                    break
            
            if not offset_fcurve:
                print("  ERROR: No offset_factor fcurve found!")
            else:
                print(f"  Offset factor keyframes:")
                for kf in offset_fcurve.keyframe_points[:10]:
                    print(f"    Frame {int(kf.co[0])}: offset_factor = {kf.co[1]:.4f}")
                if len(offset_fcurve.keyframe_points) > 10:
                    print(f"    ... ({len(offset_fcurve.keyframe_points) - 10} more)")
        
        # Test positions at various frames
        print("\n" + "=" * 80)
        print("POSITION COMPARISON AT KEYFRAMES")
        print("=" * 80)
        
        scene = bpy.context.scene
        original_frame = scene.frame_current
        
        max_distance = 0.0
        max_distance_frame = 0
        distances = []
        
        # Test at keyframes
        test_frames = keyframe_frames[::max(1, len(keyframe_frames)//20)]  # Sample ~20 frames
        if len(test_frames) == 0:
            test_frames = keyframe_frames
        
        print(f"\nTesting {len(test_frames)} frames:")
        print(f"{'Frame':<8} {'Source X':<12} {'Source Y':<12} {'Source Z':<12} {'Curve X':<12} {'Curve Y':<12} {'Curve Z':<12} {'Distance':<12} {'Offset':<10}")
        print("-" * 120)
        
        for frame in test_frames:
            scene.frame_set(frame)
            bpy.context.view_layer.update()
            
            source_pos = cam_source.location.copy()
            
            # Get offset_factor at this frame
            offset_factor = follow_path_constraint.offset_factor
            if cam_curve.animation_data and cam_curve.animation_data.action:
                # Evaluate offset_factor from animation
                action = cam_curve.animation_data.action
                for fcurve in action.fcurves:
                    if 'offset_factor' in fcurve.data_path:
                        offset_factor = fcurve.evaluate(frame)
                        break
            
            curve_pos = cam_curve.location.copy()
            distance = (source_pos - curve_pos).length
            distances.append(distance)
            
            if distance > max_distance:
                max_distance = distance
                max_distance_frame = frame
            
            print(f"{frame:<8} {source_pos.x:<12.4f} {source_pos.y:<12.4f} {source_pos.z:<12.4f} "
                  f"{curve_pos.x:<12.4f} {curve_pos.y:<12.4f} {curve_pos.z:<12.4f} "
                  f"{distance:<12.4f} {offset_factor:<10.4f}")
        
        print("-" * 120)
        avg_distance = sum(distances) / len(distances) if distances else 0
        print(f"\nStatistics:")
        print(f"  Average distance: {avg_distance:.4f}")
        print(f"  Maximum distance: {max_distance:.4f} at frame {max_distance_frame}")
        print(f"  Minimum distance: {min(distances):.4f}" if distances else "  Minimum distance: N/A")
        
        # Check motion path info
        if cam_source.motion_path:
            motion_path = cam_source.motion_path
            print(f"\nMotion Path Info:")
            print(f"  Frame range: {motion_path.frame_start} to {motion_path.frame_end}")
            print(f"  Points: {len(motion_path.points)}")
        
        # Check curve info
        curve_obj = follow_path_constraint.target
        if curve_obj and curve_obj.type == 'CURVE':
            curve_data = curve_obj.data
            if curve_data.splines:
                spline = curve_data.splines[0]
                print(f"\nCurve Info:")
                print(f"  Type: {spline.type}")
                print(f"  Points: {len(spline.points)}")
        
        # Analyze timing mismatch
        print("\n" + "=" * 80)
        print("TIMING ANALYSIS")
        print("=" * 80)
        
        if cam_curve.animation_data and cam_curve.animation_data.action:
            action = cam_curve.animation_data.action
            offset_fcurve = None
            for fcurve in action.fcurves:
                if 'offset_factor' in fcurve.data_path:
                    offset_fcurve = fcurve
                    break
            
            if offset_fcurve and len(offset_fcurve.keyframe_points) > 1:
                # Get offset_factor at first and last keyframes
                first_kf = offset_fcurve.keyframe_points[0]
                last_kf = offset_fcurve.keyframe_points[-1]
                first_frame = int(first_kf.co[0])
                last_frame = int(last_kf.co[0])
                first_offset = first_kf.co[1]
                last_offset = last_kf.co[1]
                
                print(f"\nOffset Factor Keyframes:")
                print(f"  First: Frame {first_frame}, offset_factor = {first_offset:.4f}")
                print(f"  Last: Frame {last_frame}, offset_factor = {last_offset:.4f}")
                
                # Check if offset_factor goes from 0 to 1
                if abs(first_offset) > 0.01:
                    print(f"  WARNING: First offset_factor is {first_offset:.4f}, expected ~0.0")
                if abs(last_offset - 1.0) > 0.01:
                    print(f"  WARNING: Last offset_factor is {last_offset:.4f}, expected ~1.0")
                
                # Check keyframe spacing
                kf_frames = [int(kf.co[0]) for kf in offset_fcurve.keyframe_points]
                kf_offsets = [kf.co[1] for kf in offset_fcurve.keyframe_points]
                
                if len(kf_frames) > 1:
                    frame_intervals = [kf_frames[i+1] - kf_frames[i] for i in range(len(kf_frames)-1)]
                    offset_intervals = [kf_offsets[i+1] - kf_offsets[i] for i in range(len(kf_offsets)-1)]
                    
                    print(f"\nKeyframe Spacing Analysis:")
                    print(f"  Frame intervals: min={min(frame_intervals)}, max={max(frame_intervals)}, avg={sum(frame_intervals)/len(frame_intervals):.2f}")
                    print(f"  Offset intervals: min={min(offset_intervals):.4f}, max={max(offset_intervals):.4f}, avg={sum(offset_intervals)/len(offset_intervals):.4f}")
                    
                    # Check if offset intervals are proportional to frame intervals
                    ratios = []
                    for i in range(min(len(frame_intervals), len(offset_intervals))):
                        if frame_intervals[i] > 0:
                            ratio = offset_intervals[i] / frame_intervals[i]
                            ratios.append(ratio)
                    
                    if ratios:
                        avg_ratio = sum(ratios) / len(ratios)
                        print(f"  Offset/Frame ratio: avg={avg_ratio:.6f}")
                        if len(set([round(r, 4) for r in ratios])) > 1:
                            print(f"  WARNING: Offset/Frame ratios vary - timing may not be uniform!")
                            print(f"    First few ratios: {[f'{r:.6f}' for r in ratios[:10]]}")
        
        scene.frame_set(original_frame)
        bpy.context.view_layer.update()
        
        print("\n" + "=" * 80)
        print("TEST COMPLETE")
        print("=" * 80)
