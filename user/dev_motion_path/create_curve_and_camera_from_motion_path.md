# Create Curve and Camera from Motion Path

## Overview

This script creates a NURBS curve from an animated object's motion path and sets up a camera that follows the curve synchronously, preserving the original animation's speed variations.

**Script:** `create_curve_and_camera_from_motion_path.py`

## Theoretical Foundation

### 1. Motion Paths in Blender

A **motion path** is Blender's visualization of an object's movement over time. It consists of:
- **Points**: 3D positions sampled at regular frame intervals
- **Frame Range**: The start and end frames of the animation
- **Point-to-Frame Mapping**: Each point corresponds to a specific frame

```
Motion Path Point 0  → Frame 1
Motion Path Point 1  → Frame 2
Motion Path Point N  → Frame N+1
```

### 2. Follow Path Constraint

The **Follow Path** constraint makes an object follow a curve path. The key parameter is:

- **`offset_factor`**: A value from 0.0 to 1.0 that determines position along the curve
  - `0.0` = Start of curve
  - `1.0` = End of curve
  - `0.5` = Middle of curve

When `offset_factor` is animated, the object moves along the curve over time.

### 3. The Core Problem: Frame-Based vs Distance-Based Mapping

#### ❌ Frame-Based Mapping (Incorrect)

**Initial Approach:**
```python
offset_factor = (frame - frame_start) / (frame_end - frame_start)
```

**Why This Fails:**
- Maps frames **linearly** to `offset_factor`
- Assumes **constant speed** along the curve
- Example: Frame 10 → 0.08, Frame 11 → 0.09, Frame 12 → 0.10
- If the original camera moves fast between frames 10-11 and slow between 11-12, the curve camera will move evenly, causing a mismatch

**Visual Representation:**
```
Original Camera:     [fast]  [slow]  [fast]
                     └─10─┘ └─11─┘ └─12─┘
                     
Curve Camera:        [even]  [even]  [even]
                     └─10─┘ └─11─┘ └─12─┘
                     ❌ Speed mismatch!
```

#### ✅ Distance-Based Mapping (Correct)

**Current Approach:**
```python
# Calculate cumulative distance along motion path
cumulative_distance = sum of segment distances up to frame

# Map based on distance ratio
offset_factor = cumulative_distance / total_distance
```

**Why This Works:**
- Maps based on **actual distance traveled**
- Preserves **speed variations** from the original animation
- Example: 
  - Frame 10: distance = 5.0 units → offset_factor = 0.08
  - Frame 11: distance = 8.0 units (large jump!) → offset_factor = 0.13
  - Frame 12: distance = 8.5 units (small jump) → offset_factor = 0.14
- The large distance jump between frames 10-11 causes a large `offset_factor` change, making the camera move fast, matching the original

**Visual Representation:**
```
Original Camera:     [fast]  [slow]  [fast]
                     └─10─┘ └─11─┘ └─12─┘
                     
Curve Camera:        [fast]  [slow]  [fast]
                     └─10─┘ └─11─┘ └─12─┘
                     ✅ Speed matches!
```

### 4. Mathematical Foundation

#### Cumulative Distance Calculation

For each motion path point:
```python
segment_distance = ||point[i] - point[i-1]||  # Euclidean distance
cumulative_distance[i] = cumulative_distance[i-1] + segment_distance
```

#### Offset Factor Mapping

For each keyframe at frame `F`:
```python
# Find cumulative distance at frame F
distance_F = cumulative_distances[F]

# Map to offset_factor
offset_factor = distance_F / total_distance
```

#### Speed Preservation

The **speed** of movement is proportional to the **change in distance**:
- **Fast movement** → Large distance change → Large `offset_factor` change
- **Slow movement** → Small distance change → Small `offset_factor` change

This ensures the curve camera matches the original camera's speed profile.

### 5. Why This Matters

**Real-World Scenario:**
- A camera might move slowly during a pan, then quickly during a dolly shot
- Frame-based mapping would make both movements uniform
- Distance-based mapping preserves these speed variations, creating a more natural and synchronized animation

## Architecture

The script is organized into modular functions, each handling a specific aspect of the process:

### Core Functions

1. **`get_animation_frame_range(obj)`**
   - Extracts frame range from object's animation data
   - Falls back to scene frame range if animation data unavailable

2. **`calculate_motion_path(obj)`**
   - Calculates motion path if it doesn't exist
   - Handles context management (selection, frame range)
   - Returns MotionPath object or None

3. **`create_curve_from_motion_path(motion_path, curve_name)`**
   - Creates NURBS curve from motion path points
   - Removes existing curve if present
   - Returns curve object or None

4. **`extract_keyframes(obj)`**
   - Extracts location keyframe frames and positions
   - Returns tuple: (keyframe_frames list, keyframe_positions dict)

5. **`calculate_cumulative_distances(motion_path)`**
   - Calculates cumulative distance along motion path for each frame
   - Preserves speed variations through distance-based mapping
   - Returns tuple: (cumulative_distances dict, total_distance float)

6. **`copy_camera_focal_length(source_camera_obj, target_camera_obj)`**
   - Copies focal length from source camera to target camera
   - Validates that both objects are cameras
   - Preserves camera settings for consistent field of view

7. **`create_trackto_target(target_name="trackto_tgt")`**
   - Creates an empty object to serve as Track To constraint target
   - Removes existing object if present
   - Returns empty object or None

8. **`create_camera_with_constraint(camera_name, curve_obj, source_camera_obj=None, track_to_target=None)`**
   - Creates camera object
   - Copies focal length from source camera if provided
   - Adds and configures Follow Path constraint
   - Adds and configures Track To constraint if target provided
   - Sets up animation data and action
   - Returns tuple: (camera_object, follow_path_constraint)

9. **`create_offset_factor_keyframes(...)`**
   - Creates offset_factor keyframes based on cumulative distances
   - Maps keyframes to offset_factor preserving speed variations
   - Includes verification and analysis output
   - Returns list of (frame, offset_factor) tuples

10. **`activate_constraint_animation(camera_obj, constraint)`**
    - Activates Follow Path constraint animation using Blender operator
    - Equivalent to pressing "Animate Path" button in UI
    - Ensures constraint uses animated offset_factor

11. **`main(tgt_camera, curve_name, camera_name)`**
    - Main orchestration function
    - Coordinates all steps in sequence
    - Handles error checking and validation

### Function Flow

```
main()
├── calculate_motion_path()
│   └── get_animation_frame_range()
├── create_curve_from_motion_path()
├── extract_keyframes()
├── calculate_cumulative_distances()
├── create_trackto_target()
├── create_camera_with_constraint()
│   ├── copy_camera_focal_length()
│   └── (adds Track To constraint)
├── create_offset_factor_keyframes()
└── activate_constraint_animation()
```

## Usage

### Prerequisites

1. An animated object (camera, mesh, etc.) with location keyframes
2. The object must have animation data (`animation_data.action`)
3. Blender Python API access

### Script Configuration

At the bottom of the script, configure these variables:

```python
tgt_camera = "cam_0-96"      # Source object name
followpath_tgt = "curve_path"       # Name for the created curve
camera_name = "motion_curve_cam"   # Name for the created camera
```

Or call `main()` directly with custom parameters:

```python
main(tgt_camera="my_camera", curve_name="my_curve", camera_name="my_cam")
```

### Step-by-Step Process

The `main()` function orchestrates the following steps:

#### Part 1: Create Motion Path and Curve

1. **Calculate Motion Path** (`calculate_motion_path()`)
   - Checks if motion path exists
   - If `None`, calculates it using `bpy.ops.object.paths_calculate()`
   - Uses animation frame range from `get_animation_frame_range()`
   - Manages Blender context (selection, frame range)

2. **Create NURBS Curve** (`create_curve_from_motion_path()`)
   - Extracts motion path points
   - Creates NURBS curve object
   - Converts motion path points to spline points
   - Links curve to scene

#### Part 2: Create Camera with Follow Path Constraint

1. **Extract Keyframes** (`extract_keyframes()`)
   - Finds all location keyframes from source object
   - Stores frame numbers and positions at each keyframe

2. **Calculate Cumulative Distances** (`calculate_cumulative_distances()`)
   - Iterates through motion path points
   - Calculates segment distances between consecutive points
   - Builds cumulative distance map for each frame
   - Preserves speed variations

3. **Create Track To Target** (`create_trackto_target()`)
   - Creates empty object named "trackto_tgt"
   - Serves as target for Track To constraint
   - Removes existing object if present

4. **Create Camera and Constraints** (`create_camera_with_constraint()`)
   - Creates camera object
   - Copies focal length from source camera (`copy_camera_focal_length()`)
     - Ensures consistent field of view between source and new camera
   - Adds Follow Path constraint targeting curve
   - Configures Follow Path constraint settings:
     - Forward Axis: X
     - Up Axis: Z
     - Fixed Position: True
     - Follow Curve: True
   - Adds Track To constraint targeting "trackto_tgt"
   - Configures Track To constraint settings:
     - Track Axis: -Z (negative Z)
     - Up Axis: Y
   - Sets up animation data and action

5. **Create Offset Factor Keyframes** (`create_offset_factor_keyframes()`)
   - For each keyframe frame:
     - Finds cumulative distance (with interpolation if needed)
     - Maps to `offset_factor` using: `distance / total_distance`
     - Creates keyframe on constraint's offset_factor
   - Includes verification and analysis output

6. **Activate Constraint Animation** (`activate_constraint_animation()`)
   - Calls `bpy.ops.constraint.followpath_path_animate()`
   - Ensures constraint uses animated offset_factor keyframes
   - Verifies animation setup

### Expected Output

After running the script, you should see:

1. **Console Output:**
   ```
   Processing object: cam_0-96
   Motion path info:
     Frame range: 1 to 125
     Points: 124
   Created curve object 'curve_path' with 124 points
   Found 124 keyframe frames
   Created empty object 'trackto_tgt'
   Created camera 'motion_curve_cam'
   Copied focal length: 50.0mm from 'cam_0-96' to 'motion_curve_cam'
   Configured Follow Path constraint
   Configured Track To constraint targeting 'trackto_tgt'
   Successfully activated Follow Path constraint animation
   ```

2. **Created Objects:**
   - `curve_path`: NURBS curve following the motion path
   - `trackto_tgt`: Empty object serving as Track To constraint target
   - `motion_curve_cam`: Camera with Follow Path and Track To constraints

3. **Animation:**
   - `motion_curve_cam` moves along `curve_path`
   - Camera always points toward `trackto_tgt` empty object
   - Speed variations match the original camera
   - Synchronized timing with `cam_0-96`

### Verification

To verify the script worked correctly:

1. **Check Camera Movement:**
   - Scrub through the timeline
   - `motion_curve_cam` should move along `curve_path`
   - Camera should always face `trackto_tgt` empty object
   - Speed should match `cam_0-96` (fast when original is fast, slow when original is slow)

2. **Check Keyframes:**
   - Select `motion_curve_cam`
   - Open Graph Editor or Dope Sheet
   - Look for `offset_factor` keyframes matching source keyframe frames

3. **Check Constraints:**
   - Select `motion_curve_cam`
   - Check Constraints panel
   - Follow Path constraint should be active and targeting `curve_path`
   - Track To constraint should be active and targeting `trackto_tgt`

## Troubleshooting

### Issue: Camera Stuck at Origin (0,0,0)

**Symptoms:**
- Camera doesn't move along curve
- Position remains at (0, 0, 0)

**Solution:**
- Ensure `bpy.ops.constraint.followpath_path_animate()` is called
- Check that constraint is not muted
- Verify curve exists and is valid

### Issue: Speed Mismatch

**Symptoms:**
- Camera moves but at wrong speed
- Original camera moves fast, curve camera moves slow (or vice versa)

**Solution:**
- Verify distance-based mapping is being used (not frame-based)
- Check that cumulative distances are calculated correctly
- Ensure motion path points are accurate

### Issue: Position Mismatch

**Symptoms:**
- Camera follows curve but doesn't align with original camera positions

**Possible Causes:**
1. **NURBS Interpolation**: NURBS curves interpolate between points, so positions may not match exactly
2. **Offset Factor Range**: Last keyframe might not reach 1.0
3. **Curve Creation**: Motion path points might not match curve points exactly

**Solutions:**
- Check if offset_factor reaches 1.0 at the last frame
- Verify curve points match motion path points
- Consider using a different curve type (Bezier instead of NURBS)

### Issue: Motion Path Not Calculated

**Symptoms:**
- Error: "Motion path is None"
- Script fails to create curve

**Solution:**
- Ensure source object has animation data
- Check that animation has location keyframes
- Verify frame range is correct
- Try manually calculating motion path in Blender UI first

## Technical Details

### Function Reference

#### `get_animation_frame_range(obj)`
Extracts frame range from animation data or scene settings.

**Returns:** `(frame_start, frame_end)` tuple

#### `calculate_motion_path(obj)`
Calculates motion path if missing. Manages Blender context (selection, frame range) to ensure proper calculation.

**Returns:** `MotionPath` object or `None`

**Key Operations:**
- Saves and restores context (active object, selection, frame range)
- Calls `bpy.ops.object.paths_calculate()`
- Handles errors gracefully

#### `create_curve_from_motion_path(motion_path, curve_name)`
Creates NURBS curve from motion path points.

**Parameters:**
- `motion_path`: MotionPath object with points
- `curve_name`: Name for the curve object

**Returns:** Curve object or `None`

**Key Operations:**
- Validates motion path has points
- Creates NURBS spline
- Removes existing curve if present

#### `extract_keyframes(obj)`
Extracts location keyframes and their positions.

**Returns:** `(keyframe_frames list, keyframe_positions dict)` tuple

**Key Operations:**
- Iterates through action fcurves
- Filters for location keyframes
- Evaluates positions at each keyframe

#### `calculate_cumulative_distances(motion_path)`
Calculates cumulative distances along motion path. This is the core algorithm for preserving speed variations.

**Returns:** `(cumulative_distances dict, total_distance float)` tuple

**Algorithm:**
```python
cumulative_distances = {}
total_distance = 0.0
prev_pos = None

for point in motion_path_points:
    current_pos = Vector(point.co)
    if prev_pos:
        segment_distance = (current_pos - prev_pos).length
        total_distance += segment_distance
    cumulative_distances[frame] = total_distance
    prev_pos = current_pos
```

**Key Operations:**
- Maps motion path point indices to frame numbers
- Calculates Euclidean distance between consecutive points
- Builds cumulative distance map

#### `copy_camera_focal_length(source_camera_obj, target_camera_obj)`
Copies focal length from source camera to target camera.

**Parameters:**
- `source_camera_obj`: Source camera object to copy from
- `target_camera_obj`: Target camera object to copy to

**Key Operations:**
- Validates both objects are cameras
- Copies `lens` property from source to target camera data
- Prints confirmation message with focal length value

**Example:**
```python
copy_camera_focal_length(source_cam, target_cam)
# Output: Copied focal length: 50.0mm from 'cam_0-96' to 'motion_curve_cam'
```

#### `create_trackto_target(target_name="trackto_tgt")`
Creates an empty object to serve as Track To constraint target.

**Parameters:**
- `target_name`: Name for the empty object (default: "trackto_tgt")

**Returns:** Empty object or `None`

**Key Operations:**
- Removes existing object if present
- Creates new empty object (no mesh data)
- Links object to current collection
- Prints confirmation message

**Example:**
```python
trackto_tgt = create_trackto_target("trackto_tgt")
# Output: Created empty object 'trackto_tgt'
```

#### `create_camera_with_constraint(camera_name, curve_obj, source_camera_obj=None, track_to_target=None)`
Creates camera and configures Follow Path and Track To constraints.

**Parameters:**
- `camera_name`: Name for the camera object
- `curve_obj`: Curve object to follow
- `source_camera_obj`: Optional source camera object to copy focal length from
- `track_to_target`: Optional empty object to use as Track To constraint target

**Returns:** `(camera_object, follow_path_constraint)` tuple

**Key Operations:**
- Creates camera data and object
- Copies focal length from source camera if provided
- Removes existing Follow Path and Track To constraints
- Configures Follow Path constraint settings:
  - Forward Axis: X
  - Up Axis: Z
  - Fixed Position: True
  - Follow Curve: True
- Configures Track To constraint settings (if target provided):
  - Track Axis: -Z (negative Z)
  - Up Axis: Y
- Sets up animation data and action

#### `create_offset_factor_keyframes(...)`
Creates offset_factor keyframes based on cumulative distances.

**Parameters:**
- `camera_obj`: Camera object
- `constraint`: Follow Path constraint
- `keyframe_frames`: List of frame numbers
- `cumulative_distances`: Dict mapping frame -> distance
- `total_distance`: Total distance along path
- `motion_path_info`: Dict with frame range and point count
- `keyframe_positions`: Optional dict for verification

**Returns:** List of `(frame, offset_factor)` tuples

**Algorithm:**
```python
for frame in keyframe_frames:
    # Find cumulative distance at this frame (with interpolation)
    frame_distance = cumulative_distances[frame]  # or interpolated
    
    # Map to offset_factor (0.0 to 1.0)
    offset_factor = frame_distance / total_distance
    
    # Ensure endpoints are exact
    if frame == frame_start:
        offset_factor = 0.0
    elif frame >= frame_end:
        offset_factor = 1.0
    
    # Create keyframe
    constraint.offset_factor = offset_factor
    camera_obj.keyframe_insert(
        data_path=f'constraints["{constraint.name}"].offset_factor',
        frame=frame
    )
```

**Key Operations:**
- Interpolates distances for frames not in cumulative_distances
- Ensures exact endpoints (0.0 and 1.0)
- Clamps values to [0.0, 1.0] range
- Includes verification and analysis output

#### `activate_constraint_animation(camera_obj, constraint)`
Activates Follow Path constraint animation using Blender operator.

**Key Operations:**
- Sets camera as active and selected
- Calls `bpy.ops.constraint.followpath_path_animate()`
- Verifies animation setup
- Restores selection state

### Performance Considerations

- **Motion Path Points**: Using motion path points directly is more efficient than evaluating at each frame
- **Distance Calculation**: O(n) where n = number of motion path points
- **Keyframe Creation**: O(k) where k = number of keyframes

### Limitations

1. **NURBS Interpolation**: Curve may not pass exactly through all motion path points
2. **Frame Alignment**: Requires motion path frame range to align with keyframe range
3. **Single Spline**: Currently creates only one spline (handles simple paths)

## Related Scripts

- `create_curve_from_motion_path.py`: Creates only the curve
- `create_motion_curve_camera.py`: Creates camera with constraint (requires existing curve)
- `diagnose_mismatch.py`: Diagnostic tool to identify issues

## References

- [Blender Motion Paths Documentation](https://docs.blender.org/manual/en/latest/animation/motion_paths.html)
- [Follow Path Constraint Documentation](https://docs.blender.org/manual/en/latest/animation/constraints/tracking/follow_path.html)
- [Blender Python API: MotionPath](https://docs.blender.org/api/current/bpy.types.MotionPath.html)
- [Blender Python API: FollowPathConstraint](https://docs.blender.org/api/current/bpy.types.FollowPathConstraint.html)

## Version History

- **v1.0**: Initial implementation with frame-based mapping
- **v2.0**: Fixed to use distance-based mapping for speed preservation
- **v2.1**: Added automatic motion path calculation
- **v2.2**: Added constraint animation activation
- **v3.0**: Refactored into modular functions for better maintainability and reusability
  - Separated key blocks into individual functions
  - Improved code organization and documentation
  - Enhanced error handling and context management
- **v3.1**: Added focal length copying from source camera
  - New function `copy_camera_focal_length()` to preserve camera settings
  - Ensures consistent field of view between source and new camera
  - Integrated into camera creation workflow
- **v3.2**: Added Track To constraint support
  - New function `create_trackto_target()` to create empty object for tracking
  - Camera now includes Track To constraint targeting "trackto_tgt"
  - Allows camera to maintain orientation toward target while following path
  - Track Axis: -Z, Up Axis: Y

## Author Notes

This script solves a common problem in Blender animation: creating a camera that follows a curve path while preserving the original animation's speed variations. The key insight is that **distance-based mapping** preserves speed, while **frame-based mapping** creates uniform movement.

The theoretical foundation is based on the relationship between:
- **Distance traveled** (physical movement)
- **Time** (frame numbers)
- **Speed** (distance / time)

By mapping `offset_factor` based on cumulative distance rather than frame numbers, we preserve the speed profile of the original animation.
