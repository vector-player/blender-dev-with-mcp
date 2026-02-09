"""
Fix earbud clipping issue by moving bones along global -Y axis starting from frame 769.

This script:
1. Finds the armature containing bone_Earbud_Left and bone_Earbud_Right
2. Gets the size of the earbuds to determine the offset (one unit = their size)
3. Modifies keyframes from frame 769 onwards to add offset along global -Y axis
4. Preserves all other animations and bone transformations
"""

import bpy
import mathutils


def get_earbud_size(earbud_obj):
    """
    Get the approximate size of an earbud object.
    Returns the largest dimension as the "size".
    """
    if earbud_obj is None:
        return 1.0
    
    # Get bounding box dimensions
    bbox_corners = [earbud_obj.matrix_world @ mathutils.Vector(corner) 
                    for corner in earbud_obj.bound_box]
    
    if not bbox_corners:
        return 1.0
    
    # Calculate dimensions
    min_x = min(corner.x for corner in bbox_corners)
    max_x = max(corner.x for corner in bbox_corners)
    min_y = min(corner.y for corner in bbox_corners)
    max_y = max(corner.y for corner in bbox_corners)
    min_z = min(corner.z for corner in bbox_corners)
    max_z = max(corner.z for corner in bbox_corners)
    
    dim_x = max_x - min_x
    dim_y = max_y - min_y
    dim_z = max_z - min_z
    
    # Return largest dimension
    return max(dim_x, dim_y, dim_z)


def find_armature_with_bones(bone_names):
    """
    Find the armature object that contains the specified bones.
    
    Args:
        bone_names: List of bone names to find
        
    Returns:
        tuple: (armature_obj, bones_dict) or (None, {}) if not found
    """
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            armature = obj.data
            bones_dict = {}
            all_found = True
            
            for bone_name in bone_names:
                bone = armature.bones.get(bone_name)
                if bone:
                    bones_dict[bone_name] = bone
                else:
                    all_found = False
                    break
            
            if all_found:
                return obj, bones_dict
    
    return None, {}


def get_bone_keyframes(armature_obj, bone_name, start_frame=769):
    """
    Get all keyframes for a bone's location, rotation, and scale from start_frame onwards.
    
    Args:
        armature_obj: The armature object
        bone_name: Name of the bone
        start_frame: Starting frame to consider (default 769)
        
    Returns:
        dict: {
            'location': {frame: (x, y, z), ...},
            'rotation': {frame: (x, y, z, w), ...},
            'scale': {frame: (x, y, z), ...},
            'all_frames': sorted list of all frame numbers
        }
    """
    keyframes = {
        'location': {},
        'rotation': {},
        'scale': {},
        'all_frames': []
    }
    
    if not armature_obj.animation_data or not armature_obj.animation_data.action:
        return keyframes
    
    action = armature_obj.animation_data.action
    
    # Check all fcurves for this bone
    for fcurve in action.fcurves:
        # Parse data path: pose.bones["bone_name"].location/rotation_quaternion/scale
        if f'["{bone_name}"]' in fcurve.data_path:
            if '.location' in fcurve.data_path:
                axis = ['x', 'y', 'z'][fcurve.array_index]
                for kf in fcurve.keyframe_points:
                    frame = int(kf.co[0])
                    if frame >= start_frame:
                        if frame not in keyframes['location']:
                            keyframes['location'][frame] = [0.0, 0.0, 0.0]
                        keyframes['location'][frame][fcurve.array_index] = kf.co[1]
                        if frame not in keyframes['all_frames']:
                            keyframes['all_frames'].append(frame)
            
            elif '.rotation_quaternion' in fcurve.data_path:
                for kf in fcurve.keyframe_points:
                    frame = int(kf.co[0])
                    if frame >= start_frame:
                        if frame not in keyframes['rotation']:
                            keyframes['rotation'][frame] = [0.0, 0.0, 0.0, 1.0]
                        keyframes['rotation'][frame][fcurve.array_index] = kf.co[1]
                        if frame not in keyframes['all_frames']:
                            keyframes['all_frames'].append(frame)
            
            elif '.rotation_euler' in fcurve.data_path:
                for kf in fcurve.keyframe_points:
                    frame = int(kf.co[0])
                    if frame >= start_frame:
                        if frame not in keyframes['rotation']:
                            keyframes['rotation'][frame] = [0.0, 0.0, 0.0]
                        keyframes['rotation'][frame][fcurve.array_index] = kf.co[1]
                        if frame not in keyframes['all_frames']:
                            keyframes['all_frames'].append(frame)
            
            elif '.scale' in fcurve.data_path:
                for kf in fcurve.keyframe_points:
                    frame = int(kf.co[0])
                    if frame >= start_frame:
                        if frame not in keyframes['scale']:
                            keyframes['scale'][frame] = [1.0, 1.0, 1.0]
                        keyframes['scale'][frame][fcurve.array_index] = kf.co[1]
                        if frame not in keyframes['all_frames']:
                            keyframes['all_frames'].append(frame)
    
    keyframes['all_frames'] = sorted(set(keyframes['all_frames']))
    return keyframes


def get_bone_location_at_frame(armature_obj, bone_name, frame):
    """
    Get the bone's location at a specific frame by evaluating the scene.
    """
    original_frame = bpy.context.scene.frame_current
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()
    
    pose_bone = armature_obj.pose.bones.get(bone_name)
    if pose_bone:
        # Get location in world space
        bone_matrix = armature_obj.matrix_world @ pose_bone.matrix
        location = bone_matrix.translation
    else:
        location = mathutils.Vector((0, 0, 0))
    
    bpy.context.scene.frame_set(original_frame)
    return location


def apply_y_offset_to_bone(armature_obj, bone_name, global_offset_y, start_frame=769):
    """
    Apply a global Y-axis offset to a bone's location keyframes starting from start_frame.
    This function converts the global -Y offset to the bone's local coordinate space.
    
    Args:
        armature_obj: The armature object
        bone_name: Name of the bone
        global_offset_y: Global Y-axis offset (negative for -Y direction)
        start_frame: Starting frame to apply offset (default 769)
    """
    if not armature_obj.animation_data or not armature_obj.animation_data.action:
        print(f"Warning: No animation data found for armature '{armature_obj.name}'")
        return
    
    pose_bone = armature_obj.pose.bones.get(bone_name)
    if not pose_bone:
        print(f"Error: Bone '{bone_name}' not found in armature")
        return
    
    # Store original frame
    original_frame = bpy.context.scene.frame_current
    
    # Convert global -Y offset to armature local space
    # Global -Y vector in world space
    global_offset_vector = mathutils.Vector((0, global_offset_y, 0))
    
    # Get armature's world matrix
    armature_world_matrix = armature_obj.matrix_world
    
    # Convert global offset to armature local space
    # We need to transform the global -Y vector to armature local space
    armature_local_offset = armature_world_matrix.inverted().to_3x3() @ global_offset_vector
    
    print(f"  Global offset: {global_offset_y:.4f} along global -Y")
    print(f"  Local offset (armature space): ({armature_local_offset.x:.4f}, {armature_local_offset.y:.4f}, {armature_local_offset.z:.4f})")
    
    action = armature_obj.animation_data.action
    modified_count = 0
    
    # Collect all frames that need modification
    frames_to_modify = set()
    for fcurve in action.fcurves:
        if f'["{bone_name}"]' in fcurve.data_path and '.location' in fcurve.data_path:
            for kf in fcurve.keyframe_points:
                frame = int(kf.co[0])
                if frame >= start_frame:
                    frames_to_modify.add(frame)
    
    frames_to_modify = sorted(frames_to_modify)
    
    if not frames_to_modify:
        print(f"  Warning: No keyframes found for bone '{bone_name}' at frame {start_frame} or later")
        bpy.context.scene.frame_set(original_frame)
        return
    
    # For each frame, get current location, add offset, and update keyframes
    for frame in frames_to_modify:
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        
        # Get current bone location in armature local space
        current_location = pose_bone.location.copy()
        
        # Add the offset
        new_location = current_location + armature_local_offset
        
        # Update keyframes for all three axes
        for axis_idx in range(3):
            for fcurve in action.fcurves:
                if f'["{bone_name}"]' in fcurve.data_path and '.location' in fcurve.data_path:
                    if fcurve.array_index == axis_idx:
                        # Find the keyframe at this frame
                        for kf in fcurve.keyframe_points:
                            if int(kf.co[0]) == frame:
                                kf.co[1] = new_location[axis_idx]
                                modified_count += 1
                                break
        
        if frame == frames_to_modify[0] or frame == frames_to_modify[-1] or len(frames_to_modify) <= 5:
            print(f"    Frame {frame}: location = ({new_location.x:.4f}, {new_location.y:.4f}, {new_location.z:.4f})")
    
    # Restore original frame
    bpy.context.scene.frame_set(original_frame)
    
    # Update all fcurves
    for fcurve in action.fcurves:
        fcurve.update()
    
    print(f"  Successfully modified {len(frames_to_modify)} frames ({modified_count} keyframe points) for bone '{bone_name}'")


def fix_earbud_clipping():
    """
    Main function to fix earbud clipping issue.
    """
    print("=" * 60)
    print("Fixing Earbud Clipping Issue")
    print("=" * 60)
    
    # Find earbud objects to determine size
    earbud_left_obj = bpy.data.objects.get("Earbud_Left")
    earbud_right_obj = bpy.data.objects.get("Earbud_Right")
    
    if not earbud_left_obj and not earbud_right_obj:
        print("Warning: Earbud objects not found. Using default offset of 1.0")
        offset_y = -1.0
    else:
        # Get size from left earbud if available, otherwise right
        earbud_obj = earbud_left_obj if earbud_left_obj else earbud_right_obj
        earbud_size = get_earbud_size(earbud_obj)
        offset_y = -earbud_size  # Negative for -Y direction
        print(f"Earbud size: {earbud_size:.4f}")
        print(f"Offset along global -Y axis: {offset_y:.4f}")
    
    # Find armature with the bones
    bone_names = ["bone_Earbud_Left", "bone_Earbud_Right"]
    armature_obj, bones_dict = find_armature_with_bones(bone_names)
    
    if not armature_obj:
        print("Error: Could not find armature containing bones:")
        for bone_name in bone_names:
            print(f"  - {bone_name}")
        return
    
    print(f"\nFound armature: '{armature_obj.name}'")
    for bone_name in bone_names:
        print(f"  Found bone: '{bone_name}'")
    
    # Check keyframes before modification
    start_frame = 769
    print(f"\nAnalyzing keyframes from frame {start_frame} onwards...")
    
    for bone_name in bone_names:
        keyframes = get_bone_keyframes(armature_obj, bone_name, start_frame)
        print(f"\nBone '{bone_name}' keyframes:")
        print(f"  Location keyframes: {len(keyframes['location'])} frames")
        print(f"  Rotation keyframes: {len(keyframes['rotation'])} frames")
        print(f"  Scale keyframes: {len(keyframes['scale'])} frames")
        print(f"  Total unique frames: {len(keyframes['all_frames'])}")
        
        if keyframes['all_frames']:
            print(f"  Frame range: {min(keyframes['all_frames'])} to {max(keyframes['all_frames'])}")
    
    # Apply offset to both bones
    print(f"\nApplying offset of {offset_y:.4f} along global -Y axis...")
    
    for bone_name in bone_names:
        print(f"\nProcessing bone: '{bone_name}'")
        apply_y_offset_to_bone(armature_obj, bone_name, offset_y, start_frame)
    
    # Update scene
    bpy.context.view_layer.update()
    
    print("\n" + "=" * 60)
    print("Clipping fix complete!")
    print("=" * 60)
    print("\nNote: The offset has been applied to location keyframes starting from frame 769.")
    print("All other animations (rotation, scale, other bones) remain unchanged.")
    print("\nPlease scrub through the timeline to verify the fix.")


# Execute the fix
if __name__ == "__main__":
    fix_earbud_clipping()
