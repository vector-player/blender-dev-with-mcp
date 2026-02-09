"""
Move earbud bones UP along global +Y axis starting from frame 769.
This fixes clipping with the ground by moving bones upward by one unit of their size.
"""

import bpy
import mathutils


def move_earbuds_up():
    """
    Main function to move earbud bones up along global +Y axis.
    """
    print("=" * 60)
    print("Moving Earbud Bones UP along global +Y axis")
    print("=" * 60)
    
    # Find earbud objects to determine size
    earbud_left_obj = bpy.data.objects.get("Earbud_Left")
    earbud_right_obj = bpy.data.objects.get("Earbud_Right")
    
    if not earbud_left_obj and not earbud_right_obj:
        print("Warning: Earbud objects not found. Using default offset of 0.0816")
        earbud_size = 0.0816
    else:
        # Get size from left earbud if available, otherwise right
        earbud_obj = earbud_left_obj if earbud_left_obj else earbud_right_obj
        
        # Get bounding box dimensions
        bbox_corners = [earbud_obj.matrix_world @ mathutils.Vector(corner) 
                        for corner in earbud_obj.bound_box]
        
        min_x = min(corner.x for corner in bbox_corners)
        max_x = max(corner.x for corner in bbox_corners)
        min_y = min(corner.y for corner in bbox_corners)
        max_y = max(corner.y for corner in bbox_corners)
        min_z = min(corner.z for corner in bbox_corners)
        max_z = max(corner.z for corner in bbox_corners)
        
        dim_x = max_x - min_x
        dim_y = max_y - min_y
        dim_z = max_z - min_z
        
        earbud_size = max(dim_x, dim_y, dim_z)
    
    # Offset is positive for moving UP along global +Y
    offset_y = earbud_size
    print(f"Earbud size: {earbud_size:.4f}")
    print(f"Offset along global +Y axis (upward): +{offset_y:.4f}")
    
    # Find armature
    armature_obj = None
    bone_names = ["bone_Earbud_Left", "bone_Earbud_Right"]
    
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            armature = obj.data
            all_found = True
            for bone_name in bone_names:
                if not armature.bones.get(bone_name):
                    all_found = False
                    break
            if all_found:
                armature_obj = obj
                break
    
    if not armature_obj:
        print("Error: Could not find armature containing bones:")
        for bone_name in bone_names:
            print(f"  - {bone_name}")
        return
    
    print(f"\nFound armature: '{armature_obj.name}'")
    for bone_name in bone_names:
        print(f"  Found bone: '{bone_name}'")
    
    # Convert global +Y offset to armature local space
    global_offset_vector = mathutils.Vector((0, offset_y, 0))  # Positive for +Y
    armature_world_matrix = armature_obj.matrix_world
    armature_local_offset = armature_world_matrix.inverted().to_3x3() @ global_offset_vector
    
    print(f"\nGlobal offset: +{offset_y:.4f} along global +Y (upward)")
    print(f"Local offset (armature space): ({armature_local_offset.x:.4f}, {armature_local_offset.y:.4f}, {armature_local_offset.z:.4f})")
    
    # Get all NLA strips active from frame 769 onwards
    start_frame = 769
    strips_info = []
    
    if armature_obj.animation_data:
        for track in armature_obj.animation_data.nla_tracks:
            for strip in track.strips:
                if strip.frame_end >= start_frame and not track.mute:
                    if strip.action:
                        has_location = False
                        for fcurve in strip.action.fcurves:
                            for bone_name in bone_names:
                                if bone_name in fcurve.data_path and '.location' in fcurve.data_path:
                                    has_location = True
                                    break
                            if has_location:
                                break
                        
                        if has_location:
                            strips_info.append({
                                'strip': strip,
                                'action': strip.action
                            })
    
    print(f"\nFound {len(strips_info)} actions to modify\n")
    
    total_modified = 0
    
    # Modify each action
    for info in strips_info:
        strip = info['strip']
        action = info['action']
        
        print(f"Processing action: {action.name}")
        print(f"  Strip timeline: {strip.frame_start} to {strip.frame_end}")
        
        # Find all keyframes that map to timeline >= 769
        frames_to_modify = {}
        
        for fcurve in action.fcurves:
            for bone_name in bone_names:
                if bone_name in fcurve.data_path and '.location' in fcurve.data_path:
                    axis = fcurve.array_index
                    for kf in fcurve.keyframe_points:
                        action_frame = int(kf.co[0])
                        timeline_frame = strip.frame_start + action_frame
                        
                        if timeline_frame >= start_frame:
                            if action_frame not in frames_to_modify:
                                frames_to_modify[action_frame] = {}
                            if bone_name not in frames_to_modify[action_frame]:
                                frames_to_modify[action_frame][bone_name] = [None, None, None]
                            frames_to_modify[action_frame][bone_name][axis] = kf
        
        if not frames_to_modify:
            print("  No keyframes to modify")
            continue
        
        print(f"  Modifying {len(frames_to_modify)} action frames")
        
        # Modify keyframes
        for action_frame in sorted(frames_to_modify.keys()):
            timeline_frame = strip.frame_start + action_frame
            
            for bone_name in frames_to_modify[action_frame]:
                # Get current location values from keyframes
                current_location = [0.0, 0.0, 0.0]
                for axis in range(3):
                    kf = frames_to_modify[action_frame][bone_name][axis]
                    if kf is not None:
                        current_location[axis] = kf.co[1]
                
                # Add offset (moving UP)
                current_vec = mathutils.Vector(current_location)
                new_location = current_vec + armature_local_offset
                
                # Update keyframes
                for axis in range(3):
                    kf = frames_to_modify[action_frame][bone_name][axis]
                    if kf is not None:
                        kf.co[1] = new_location[axis]
                        total_modified += 1
        
        # Update fcurves
        for fcurve in action.fcurves:
            fcurve.update()
        
        print(f"  Modified {len(frames_to_modify)} frames")
    
    # Update scene
    bpy.context.view_layer.update()
    
    print(f"\n" + "=" * 60)
    print(f"Complete! Modified {total_modified} keyframe points")
    print("=" * 60)
    print("\nThe earbud bones have been moved UP along global +Y axis starting from frame 769.")
    print("All other animations (rotation, scale, other bones) remain unchanged.")
    print("\nPlease scrub through the timeline to verify the fix.")


# Execute
if __name__ == "__main__":
    move_earbuds_up()
