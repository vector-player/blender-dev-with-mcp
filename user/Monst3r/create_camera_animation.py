"""
Create Camera Animation from GLB Camera Sequence

This script extracts camera positions from a camera sequence in a GLB model
and creates a new camera with keyframes representing each camera position.

The script looks for cameras in the "world" outline and sorts them by name
to create a sequential animation.
"""

import bpy
import re
from mathutils import Vector, Euler


def find_camera_sequence(world_outline_name="world"):
    """
    Find camera objects in the world outline and sort them by name.
    
    This function searches for cameras in multiple ways:
    1. Direct camera objects in the scene
    2. Cameras as children of the world object
    3. Cameras in collections matching the world name
    4. Recursive search through nested hierarchies
    
    Args:
        world_outline_name: Name of the world outline object/collection
        
    Returns:
        list: Sorted list of camera objects
    """
    cameras = []
    found_names = set()  # Track found cameras to avoid duplicates
    
    # Method 1: Look for camera objects directly in scene
    all_cameras = [obj for obj in bpy.data.objects if obj.type == 'CAMERA']
    for cam in all_cameras:
        if cam.name not in found_names:
            cameras.append(cam)
            found_names.add(cam.name)
    
    # Method 2: Check if world is an object with children
    world_obj = bpy.data.objects.get(world_outline_name)
    if world_obj:
        # Recursive function to get all children
        def get_all_children(obj):
            children = []
            for child in obj.children:
                children.append(child)
                children.extend(get_all_children(child))
            return children
        
        all_children = get_all_children(world_obj)
        for child in all_children:
            if child.type == 'CAMERA' and child.name not in found_names:
                cameras.append(child)
                found_names.add(child.name)
    
    # Method 3: Check collections
    for collection in bpy.data.collections:
        if world_outline_name.lower() in collection.name.lower():
            for obj in collection.objects:
                if obj.type == 'CAMERA' and obj.name not in found_names:
                    cameras.append(obj)
                    found_names.add(obj.name)
    
    # Method 4: Check all collections recursively
    def get_all_collection_objects(collection):
        """Recursively get all objects from a collection and its children."""
        objects = list(collection.objects)
        for child_collection in collection.children:
            objects.extend(get_all_collection_objects(child_collection))
        return objects
    
    for collection in bpy.data.collections:
        all_collection_objects = get_all_collection_objects(collection)
        for obj in all_collection_objects:
            if obj.type == 'CAMERA' and obj.name not in found_names:
                cameras.append(obj)
                found_names.add(obj.name)
    
    # Sort cameras by name (extract numbers if present)
    def extract_number(name):
        """Extract number from camera name for sorting."""
        # Try to find numbers in the name
        numbers = re.findall(r'\d+', name)
        if numbers:
            return int(numbers[-1])  # Use last number found
        return 0
    
    # Sort by extracted number, then by name as fallback
    cameras.sort(key=lambda x: (extract_number(x.name), x.name))
    
    return cameras


def extract_camera_data(camera_obj):
    """
    Extract position and rotation data from a camera object.
    
    Args:
        camera_obj: Camera object to extract data from
        
    Returns:
        dict: Dictionary with location, rotation_euler, and rotation_quaternion
    """
    data = {
        'location': Vector(camera_obj.location),
        'rotation_euler': Euler(camera_obj.rotation_euler),
        'rotation_quaternion': None,
    }
    
    # Check if camera uses quaternion rotation
    if camera_obj.rotation_mode == 'QUATERNION':
        data['rotation_quaternion'] = camera_obj.rotation_quaternion.copy()
    
    # Also get camera properties if available
    if camera_obj.type == 'CAMERA' and camera_obj.data:
        data['lens'] = camera_obj.data.lens
        data['sensor_width'] = camera_obj.data.sensor_width
    
    return data


def create_animated_camera(camera_sequence, new_camera_name="AnimatedCamera", start_frame=1):
    """
    Create a new camera with keyframes from camera sequence.
    
    Args:
        camera_sequence: List of camera objects in order
        new_camera_name: Name for the new camera
        start_frame: Starting frame number for keyframes
        
    Returns:
        bpy.types.Object: The created camera object
    """
    if not camera_sequence:
        print("Error: No cameras found in sequence")
        return None
    
    print(f"Found {len(camera_sequence)} cameras in sequence")
    print(f"Camera names: {[cam.name for cam in camera_sequence]}")
    
    # Remove existing camera if it exists
    existing_cam = bpy.data.objects.get(new_camera_name)
    if existing_cam:
        bpy.data.objects.remove(existing_cam)
        print(f"Removed existing '{new_camera_name}'")
    
    # Create new camera
    cam_data = bpy.data.cameras.new(name=new_camera_name)
    new_camera = bpy.data.objects.new(new_camera_name, cam_data)
    bpy.context.collection.objects.link(new_camera)
    
    # Copy camera properties from first camera in sequence
    if camera_sequence[0].type == 'CAMERA' and camera_sequence[0].data:
        source_cam_data = camera_sequence[0].data
        cam_data.lens = source_cam_data.lens
        cam_data.sensor_width = source_cam_data.sensor_width
        print(f"Copied camera properties: lens={cam_data.lens}mm")
    
    # Create animation data
    if not new_camera.animation_data:
        new_camera.animation_data_create()
    
    action_name = f"{new_camera_name}_Action"
    action = bpy.data.actions.get(action_name)
    if action is None:
        action = bpy.data.actions.new(name=action_name)
    
    new_camera.animation_data.action = action
    
    # Store original context
    scene = bpy.context.scene
    original_frame = scene.frame_current
    
    # Determine rotation mode from first camera (assume all use same mode)
    first_cam_data = extract_camera_data(camera_sequence[0])
    if first_cam_data['rotation_quaternion'] is not None:
        new_camera.rotation_mode = 'QUATERNION'
        print(f"Using QUATERNION rotation mode")
    else:
        new_camera.rotation_mode = 'XYZ'
        print(f"Using XYZ rotation mode")
    
    # Extract and set keyframes
    print(f"\nCreating keyframes starting at frame {start_frame}:")
    
    for i, source_camera in enumerate(camera_sequence):
        frame = start_frame + i
        
        # Set frame
        scene.frame_set(frame)
        
        # Get camera data
        cam_data_dict = extract_camera_data(source_camera)
        
        # Set location (use world location if camera has parent transform)
        if source_camera.parent:
            # Use world matrix translation for cameras with parents
            new_camera.location = source_camera.matrix_world.translation
        else:
            new_camera.location = cam_data_dict['location']
        new_camera.keyframe_insert(data_path="location", frame=frame)
        
        # Set rotation based on rotation mode
        if new_camera.rotation_mode == 'QUATERNION':
            if source_camera.parent:
                # Use world matrix rotation for cameras with parents
                new_camera.rotation_quaternion = source_camera.matrix_world.to_quaternion()
            else:
                new_camera.rotation_quaternion = cam_data_dict['rotation_quaternion']
            new_camera.keyframe_insert(data_path="rotation_quaternion", frame=frame)
        else:
            if source_camera.parent:
                # Use world matrix rotation for cameras with parents
                new_camera.rotation_euler = source_camera.matrix_world.to_euler()
            else:
                new_camera.rotation_euler = cam_data_dict['rotation_euler']
            new_camera.keyframe_insert(data_path="rotation_euler", frame=frame)
        
        # Copy camera lens if available
        if 'lens' in cam_data_dict and cam_data_dict['lens']:
            cam_data.lens = cam_data_dict['lens']
            cam_data.keyframe_insert(data_path="lens", frame=frame)
        
        print(f"  Frame {frame}: {source_camera.name} -> location={new_camera.location}")
    
    # Restore original frame
    scene.frame_set(original_frame)
    
    # Set scene frame range to cover all keyframes
    end_frame = start_frame + len(camera_sequence) - 1
    if scene.frame_start > start_frame:
        scene.frame_start = start_frame
    if scene.frame_end < end_frame:
        scene.frame_end = end_frame
    
    print(f"\nCreated camera '{new_camera_name}' with {len(camera_sequence)} keyframes")
    print(f"Frame range: {start_frame} to {end_frame}")
    
    return new_camera


def main(world_outline_name="world", new_camera_name="AnimatedCamera", start_frame=1):
    """
    Main function to create camera animation from GLB camera sequence.
    
    Args:
        world_outline_name: Name of the world outline containing cameras
        new_camera_name: Name for the new animated camera
        start_frame: Starting frame number for keyframes
    """
    print("=" * 60)
    print("Camera Animation Creator from GLB Camera Sequence")
    print("=" * 60)
    
    # Find camera sequence
    print(f"\nSearching for cameras in '{world_outline_name}'...")
    camera_sequence = find_camera_sequence(world_outline_name)
    
    if not camera_sequence:
        print(f"\nError: No cameras found in '{world_outline_name}'")
        print("\nTroubleshooting:")
        print("  1. Make sure the GLB file is imported")
        print("  2. Check if cameras are named with sequential numbers")
        print("  3. Verify cameras are children of the 'world' object/collection")
        print("  4. Check if cameras exist in the scene:")
        
        # List all cameras in scene for debugging
        all_cameras = [obj for obj in bpy.data.objects if obj.type == 'CAMERA']
        if all_cameras:
            print(f"     Found {len(all_cameras)} camera(s) in scene:")
            for cam in all_cameras:
                print(f"       - {cam.name}")
        else:
            print("     No camera objects found in the entire scene")
        
        return None
    
    # Create animated camera
    print(f"\nCreating animated camera '{new_camera_name}'...")
    animated_camera = create_animated_camera(
        camera_sequence, 
        new_camera_name=new_camera_name,
        start_frame=start_frame
    )
    
    if animated_camera:
        print("\n" + "=" * 60)
        print("Success! Camera animation created.")
        print("=" * 60)
        print(f"\nTo use the camera:")
        print(f"  1. Select '{new_camera_name}' in the scene")
        print(f"  2. Press N to open properties panel")
        print(f"  3. Scrub the timeline to see the animation")
        print(f"  4. Set it as active camera: View > Cameras > Set Active Object as Camera")
    
    return animated_camera


# Script execution
if __name__ == "__main__":
    # Configuration variables
    WORLD_OUTLINE_NAME = "world"  # Name of the world outline/collection
    NEW_CAMERA_NAME = "AnimatedCamera"  # Name for the new camera
    START_FRAME = 1  # Starting frame number for keyframes
    
    # Run main function
    main(
        world_outline_name=WORLD_OUTLINE_NAME,
        new_camera_name=NEW_CAMERA_NAME,
        start_frame=START_FRAME
    )
