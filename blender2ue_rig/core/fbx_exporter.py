"""
FBX Export with UE-optimized settings
"""

from pickle import TRUE
import bpy
from mathutils import Matrix
import math


def get_ue_fbx_export_settings() -> dict:
    """
    Returns FBX export settings optimized for UE import
    
    Based on UE documentation and Epic's recommended settings:
    - Correct bone orientation (Y-forward, X-right, Z-up)
    - No leaf bones (UE doesn't use them)
    - Proper animation baking
    - Tangent space for normal maps
    - Materials and textures preserved
    
    Returns:
        Dictionary of FBX export settings
    """
    return {
        # Selection
        'use_selection': False,
        'use_active_collection': False,
        
        # Transform
        'global_scale': 1.0,  # Scale handled separately in conversion
        'apply_unit_scale': False,  # Don't apply Blender's unit scale (causes conflicts)
        'apply_scale_options': 'FBX_SCALE_NONE',  # Use only global_scale
        'bake_space_transform': False,  # We handle coordinate conversion
        
        # Object types
        'object_types': {'ARMATURE', 'MESH', 'OTHER'},  # Include cameras, lights if needed
        'use_mesh_modifiers': True,
        'use_mesh_modifiers_render': True,
        
        # Mesh
        'mesh_smooth_type': 'FACE',
        'use_subsurf': False,
        'use_mesh_edges': False,
        'use_tspace': True,  # Important for normal maps in UE
        'colors_type': 'SRGB',  # Preserve vertex colors
        
        # Materials & Textures
        'path_mode': 'AUTO',  # Use relative paths when possible
        'embed_textures': False,  # Don't embed - use separate texture files for UE
        
        # Armature
        'use_armature_deform_only': True,
        'add_leaf_bones': False,  # UE doesn't need leaf bones
        'primary_bone_axis': 'Y',  # UE bone orientation
        'secondary_bone_axis': 'X',
        'armature_nodetype': 'NULL',
        
        # Animation
        'bake_anim': True,
        'bake_anim_use_all_bones': True,
        'bake_anim_use_nla_strips': False,
        'bake_anim_use_all_actions': False,
        'bake_anim_force_startend_keying': True,
        'bake_anim_step': 1.0,
        'bake_anim_simplify_factor': 0.0,
        
        # Other
        'batch_mode': 'OFF',
        'use_custom_props': False,
    }


def convert_textures_to_png(
    mesh_objects: list[bpy.types.Object],
    output_dir: str
) -> dict:
    """
    Convert all textures in mesh materials to PNG format
    
    This function processes all image textures used in the materials of the given
    mesh objects and converts them to PNG format. It handles both packed images
    (embedded in .blend file) and external image files.
    
    Args:
        mesh_objects: List of mesh objects to process
        output_dir: Directory where converted PNG textures will be saved
    
    Returns:
        Dictionary mapping original image names to converted PNG file paths
    """
    import os
    
    converted_textures = {}
    
    # Collect all unique images from materials
    images_to_convert = set()
    
    for mesh_obj in mesh_objects:
        if not mesh_obj.data.materials:
            continue
            
        for mat_slot in mesh_obj.data.materials:
            if not mat_slot or not mat_slot.use_nodes:
                continue
            
            # Find all image texture nodes
            for node in mat_slot.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image:
                    images_to_convert.add(node.image)
    
    # Convert each image to PNG
    for img in images_to_convert:
        if not img or not img.name:
            continue
            
        try:
            # Generate PNG filename
            if img.name:
                # Use image name, remove any existing extension
                img_name = img.name
                for ext in ['.webp', '.png', '.jpg', '.jpeg', '.tga', '.bmp', '.tif', '.tiff', '.exr', '.hdr']:
                    if img_name.lower().endswith(ext):
                        img_name = img_name[:-len(ext)]
                        break
                img_name += '.png'
            else:
                img_name = f"texture_{len(converted_textures)}.png"
            
            dest_path = os.path.join(output_dir, img_name)
            
            # Check if image needs conversion
            needs_conversion = True
            
            if img.packed_file:
                # Packed image - always save as PNG
                print(f"Converting packed texture '{img.name}' to PNG...")
            elif img.filepath:
                # External image - check if it's already PNG
                original_path = bpy.path.abspath(img.filepath)
                if original_path.lower().endswith('.png') and os.path.exists(original_path):
                    # Already PNG, but we still save it to ensure it's in the output directory
                    print(f"Copying PNG texture '{img.name}'...")
                else:
                    print(f"Converting texture '{img.name}' from {os.path.splitext(original_path)[1]} to PNG...")
            else:
                print(f"Skipping texture '{img.name}' - no source data")
                continue
            
            # Save as PNG (this automatically converts from any format Blender supports)
            original_filepath = img.filepath_raw
            original_format = img.file_format
            
            img.filepath_raw = dest_path
            img.file_format = 'PNG'
            img.save()
            
            # Set the absolute filepath so FBX export can find it
            # Since textures are in the same directory as FBX, UE will auto-detect them
            img.filepath = dest_path
            img.reload()
            
            converted_textures[img.name] = dest_path
            print(f"  → Saved as: {img_name}")
            
        except Exception as e:
            print(f"Failed to convert texture '{img.name}': {e}")
            # Restore original settings on failure
            if 'original_filepath' in locals():
                img.filepath_raw = original_filepath
            if 'original_format' in locals():
                img.file_format = original_format
    
    if converted_textures:
        print(f"\nConverted {len(converted_textures)} texture(s) to PNG format")
    
    return converted_textures


def export_material_definitions(
    mesh_objects: list[bpy.types.Object],
    output_dir: str,
    fbx_basename: str
) -> dict:
    """
    Export material definitions as JSON files for Unreal Engine
    
    This function extracts material information from mesh objects and creates
    JSON files that describe material properties and texture assignments.
    This makes it easier to recreate materials in Unreal Engine.
    
    Args:
        mesh_objects: List of mesh objects to process
        output_dir: Directory where JSON files will be saved
        fbx_basename: Base name of the FBX file (without extension)
    
    Returns:
        Dictionary mapping material names to their definition file paths
    """
    import json
    import os
    
    print(f"\n=== DEBUG: export_material_definitions called ===")
    print(f"  Output dir: {output_dir}")
    print(f"  FBX basename: {fbx_basename}")
    print(f"  Mesh objects count: {len(mesh_objects)}")
    
    material_files = {}
    materials_data = {}
    
    # Collect all unique materials from mesh objects
    unique_materials = set()
    for mesh_obj in mesh_objects:
        print(f"  Checking mesh: {mesh_obj.name}")
        if mesh_obj.data.materials:
            print(f"    Has {len(mesh_obj.data.materials)} material slot(s)")
            for mat_slot in mesh_obj.data.materials:
                if mat_slot:
                    unique_materials.add(mat_slot)
                    print(f"      Material: {mat_slot.name}")
                else:
                    print(f"      Empty material slot")
        else:
            print(f"    No materials")
    
    print(f"  Total unique materials found: {len(unique_materials)}")
    
    if not unique_materials:
        print("  WARNING: No materials found to export")
        # Still create an empty JSON file for consistency
        json_filename = f"{fbx_basename}_materials.json"
        json_path = os.path.join(output_dir, json_filename)
        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump({}, f, indent=2)
            material_files['all_materials'] = json_path
            print(f"  Created empty material file: {json_filename}")
        except Exception as e:
            print(f"  ERROR: Failed to create empty material file: {e}")
        return material_files
    
    print(f"\n=== Exporting {len(unique_materials)} material definition(s) ===")
    
    # Process each material
    for mat in unique_materials:
        mat_data = {
            "material_name": mat.name,
            "textures": {},
            "properties": {}
        }
        
        # Extract base color
        if hasattr(mat, 'diffuse_color'):
            mat_data["properties"]["base_color"] = list(mat.diffuse_color)
        
        # Extract metallic and roughness if available
        if hasattr(mat, 'metallic'):
            mat_data["properties"]["metallic"] = mat.metallic
        if hasattr(mat, 'roughness'):
            mat_data["properties"]["roughness"] = mat.roughness
        
        # Extract textures from node tree
        if mat.use_nodes and mat.node_tree:
            # Common texture slot mappings for UE
            texture_mapping = {
                'Base Color': 'BaseColor',
                'BaseColor': 'BaseColor',
                'Diffuse': 'BaseColor',
                'Color': 'BaseColor',
                'Normal': 'Normal',
                'Normal Map': 'Normal',
                'Roughness': 'Roughness',
                'Metallic': 'Metallic',
                'Metalness': 'Metallic',
                'Emissive': 'Emissive',
                'Emission': 'Emissive',
                'Opacity': 'Opacity',
                'Alpha': 'Opacity',
                'Ambient Occlusion': 'AmbientOcclusion',
                'AO': 'AmbientOcclusion',
            }
            
            # Find the Principled BSDF node (most common)
            principled_node = None
            for node in mat.node_tree.nodes:
                if node.type == 'BSDF_PRINCIPLED':
                    principled_node = node
                    break
            
            # Extract textures connected to Principled BSDF
            if principled_node:
                for input_socket in principled_node.inputs:
                    if input_socket.is_linked:
                        # Trace back to find image texture node
                        for link in input_socket.links:
                            from_node = link.from_node
                            if from_node.type == 'TEX_IMAGE' and from_node.image:
                                # Map socket name to UE texture slot
                                socket_name = input_socket.name
                                ue_slot = texture_mapping.get(socket_name, socket_name)
                                
                                # Get texture filename (should be PNG after conversion)
                                img_name = from_node.image.name
                                # Ensure .png extension
                                for ext in ['.webp', '.png', '.jpg', '.jpeg', '.tga', '.bmp', '.tif', '.tiff']:
                                    if img_name.lower().endswith(ext):
                                        img_name = img_name[:-len(ext)]
                                        break
                                img_name += '.png'
                                
                                mat_data["textures"][ue_slot] = img_name
            
            # Also check for standalone image texture nodes not connected to Principled BSDF
            for node in mat.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image:
                    # Try to infer texture type from node label or name
                    node_label = node.label.lower() if node.label else node.name.lower()
                    
                    # Check if we haven't already captured this texture
                    img_name = node.image.name
                    for ext in ['.webp', '.png', '.jpg', '.jpeg', '.tga', '.bmp', '.tif', '.tiff']:
                        if img_name.lower().endswith(ext):
                            img_name = img_name[:-len(ext)]
                            break
                    img_name += '.png'
                    
                    # Try to infer slot from label/name
                    for key, ue_slot in texture_mapping.items():
                        if key.lower() in node_label and ue_slot not in mat_data["textures"]:
                            mat_data["textures"][ue_slot] = img_name
                            break
        
        materials_data[mat.name] = mat_data
        print(f"  Material: {mat.name}")
        if mat_data["textures"]:
            for slot, texture in mat_data["textures"].items():
                print(f"    - {slot}: {texture}")
    
    # Export as a single JSON file with all materials
    json_filename = f"{fbx_basename}_materials.json"
    json_path = os.path.join(output_dir, json_filename)
    
    print(f"\n  Attempting to write JSON to: {json_path}")
    print(f"  Materials data contains {len(materials_data)} material(s)")
    
    try:
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(materials_data, f, indent=2)
        
        # Verify file was created
        if os.path.exists(json_path):
            file_size = os.path.getsize(json_path)
            material_files['all_materials'] = json_path
            print(f"  ✓ Successfully created: {json_filename} ({file_size} bytes)")
        else:
            print(f"  ✗ ERROR: File was not created: {json_path}")
            
    except Exception as e:
        print(f"  ✗ ERROR: Failed to export material definitions: {e}")
        import traceback
        traceback.print_exc()
    
    print("=== Material export complete ===\n")
    
    return material_files


def export_fbx_for_ue(
    filepath: str,
    armature_obj: bpy.types.Object,
    mesh_objects: list[bpy.types.Object],
    scale_factor: float = 100.0,
    export_animations: bool = True
) -> bool:
    """
    Export armature and meshes to FBX with UE-compatible settings
    
    Args:
        filepath: Output FBX file path
        armature_obj: Armature object
        mesh_objects: List of mesh objects to export
        scale_factor: Scale factor for UE (default 100 for cm)
        export_animations: Include animations
    
    Returns:
        True if export succeeded
    """
    import os
    import shutil
    
    # Select objects for export
    bpy.ops.object.select_all(action='DESELECT')
    
    if armature_obj:
        armature_obj.select_set(True)
    
    for mesh_obj in mesh_objects:
        mesh_obj.select_set(True)
    
    if armature_obj:
        bpy.context.view_layer.objects.active = armature_obj
    elif mesh_objects:
        bpy.context.view_layer.objects.active = mesh_objects[0]
    
    # Get export settings
    settings = get_ue_fbx_export_settings()
    # Apply scale factor directly (100 = 100x scale for UE's cm units)
    settings['global_scale'] = scale_factor
    
    if not export_animations:
        settings['bake_anim'] = False
    
    # Create texture folder in the SAME directory as FBX (not subfolder)
    # Unreal Engine expects textures to be in the same folder as the FBX for auto-import
    fbx_dir = os.path.dirname(filepath)
    texture_dir = fbx_dir  # Same directory as FBX file
    
    print(f"Texture output directory: {texture_dir}")
    
    # Convert all textures to PNG BEFORE exporting FBX
    # This ensures the FBX references PNG files
    converted_count = 0
    if mesh_objects:
        print("\n=== Converting textures to PNG ===")
        converted_textures = convert_textures_to_png(mesh_objects, texture_dir)
        converted_count = len(converted_textures)
        print("=== Texture conversion complete ===\n")
    
    # Export material definitions as JSON
    model_name = os.path.splitext(os.path.basename(filepath))[0]
    if mesh_objects:
        material_files = export_material_definitions(mesh_objects, texture_dir, model_name)
    
    # Apply default bone limits if missing
    if armature_obj:
        print("\n=== Checking/Applying Bone Limits & Structure ===")
        # Enforce Root Bone (Critical for UE)
        ensure_root_bone(armature_obj)
        # Generate IK Bones (Standard for UE)
        generate_ik_bones(armature_obj)
        # Apply limits
        apply_default_bone_limits(armature_obj)
    
    # Export FBX
    try:
        bpy.ops.export_scene.fbx(
            filepath=filepath,
            **settings
        )
        
        # Textures have already been converted to PNG before export
        if converted_count > 0:
            print(f"\nFBX export complete with {converted_count} PNG texture(s) in {texture_dir}")
        
        return True
    except Exception as e:
        print(f"FBX Export failed: {e}")
        return False
    except Exception as e:
        print(f"FBX Export failed: {e}")
        return False


def prepare_armature_for_export(
    armature_obj: bpy.types.Object,
    use_ue_naming: bool = True
) -> None:
    """
    Prepare armature for UE export
    - Rename bones to UE conventions
    - Fix bone orientations
    - Apply transforms
    
    Args:
        armature_obj: Armature object to prepare
        use_ue_naming: Apply UE bone naming conventions
    """
    if armature_obj.type != 'ARMATURE':
        return
    
    # Apply transforms
    bpy.ops.object.select_all(action='DESELECT')
    armature_obj.select_set(True)
    bpy.context.view_layer.objects.active = armature_obj
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    
    
    if use_ue_naming:
        # Import here to avoid circular dependency
        from .ue_skeleton import apply_ue_bone_naming
        
        # 1. Ensure Root Bone exists (UE Requirement)
        ensure_root_bone(armature_obj)
        
        # 2. Rename bones
        bpy.ops.object.mode_set(mode='EDIT')
        for bone in armature_obj.data.edit_bones:
            new_name = apply_ue_bone_naming(bone.name)
            if new_name != bone.name:
                bone.name = new_name
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # 3. Generate Virtual IK Bones (UE Standard)
        generate_ik_bones(armature_obj)


def prepare_mesh_for_export(mesh_obj: bpy.types.Object) -> None:
    """
    Prepare mesh for UE export
    - Apply transforms
    - Triangulate
    - Calculate normals
    
    Args:
        mesh_obj: Mesh object to prepare
    """
    if mesh_obj.type != 'MESH':
        return
    
    # Apply transforms
    bpy.ops.object.select_all(action='DESELECT')
    mesh_obj.select_set(True)
    bpy.context.view_layer.objects.active = mesh_obj
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    
    # Triangulate (UE requires triangles)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.quads_convert_to_tris()
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # Calculate normals
    mesh_obj.data.calc_normals_split()


# Default bone limits in degrees (converted to radians at runtime)
# Used as fallback when no constraints exist
# Default bone limits in degrees (X, Y, Z)
# X: Main Bend axis (usually)
# Y: Twist axis (along bone length)
# Z: Side/Secondary Bend axis
BONE_LIMITS = {
    # Torso (Ball/Universal)
    'head': (60.0, 70.0, 60.0),
    'neck': (60.0, 70.0, 60.0),
    'spine': (45.0, 45.0, 45.0),
    'pelvis': (180.0, 180.0, 180.0), # Hips free
    
    # Shoulders (Ball-like but restricted)
    'clavicle': (20.0, 20.0, 20.0),
    'shoulder': (20.0, 20.0, 20.0),
    
    # Upper Limbs (Ball joints)
    'upperarm': (130.0, 90.0, 130.0), # High mobility
    'upper_arm': (130.0, 90.0, 130.0),
    
    # Hinge Joints (Elbows - Restrict Y/Twist and Z/Side)
    'lowerarm': (0.0, 135.0, 0.0) if False else (135.0, 30.0, 15.0), # Assuming X is bend. Y twist allowed slightly. Z strict.
    'forearm': (135.0, 30.0, 15.0),
    'hand': (90.0, 45.0, 90.0), # Wrist flexible
    
    # Lower Limbs (Ball joints)
    'thigh': (130.0, 45.0, 130.0),
    
    # Hinge Joints (Knees - Very strict on twist/side)
    'calf': (135.0, 10.0, 5.0),
    'shin': (135.0, 10.0, 5.0),
    'foot': (90.0, 30.0, 45.0), # Ankle
    'ball': (45.0, 5.0, 5.0),   # Toes hinge
    'toe': (45.0, 5.0, 5.0),
    
    # Fingers (Hinge-like)
    # Usually bend on X or Z depending on orientation, but often strict on Twist (Y)
    'thumb': (90.0, 45.0, 90.0), # Thumb is flexible
    'index': (90.0, 10.0, 15.0),
    'middle': (90.0, 10.0, 15.0),
    'ring': (90.0, 10.0, 15.0),
    'pinky': (90.0, 10.0, 15.0),
}


def apply_default_bone_limits(armature_obj: bpy.types.Object) -> None:
    """
    Apply default rotation limits to bones that don't have them.
    
    Args:
        armature_obj: Armature object to process
    """
    if armature_obj.type != 'ARMATURE':
        return
        
    import math
    
    count_updated = 0
    # Edit mode to get geometry? No, we can access armature.data.bones for rest pose vectors equivalent to edit bones.
    # armature_obj.data.bones[name].vector is available in Object mode.
    
    straight_bones = {}
    hinge_axes = {} # Store recognized hinge axis ('X' or 'Z') per bone
    
    data_bones = armature_obj.data.bones
    
    for bone in data_bones:
        is_straight = False
        hinge_axis = None
        
        if bone.children:
            child = bone.children[0]
            
            # Vectors relative to armature origin (Global-ish)
            # We need them in Bone's Local space to see which axis aligns with the bend
            
            # Bone Matrix (Local to Armature)
            # We want the vector of the child relative to the bone's head
            # But bone.matrix is 4x4.
            
            # Simplified approach using vectors:
            v_bone = bone.vector.normalized()
            v_child = child.vector.normalized()
            
            try:
                angle = v_bone.angle(v_child)
                # STRAIGHT CHAIN (< 10 deg)
                if angle < math.radians(10):
                    is_straight = True
                
                # BENT CHAIN (Assume Hinge/Arm)
                else:
                    # The axis of rotation is perpendicular to both vectors
                    # Cross product gives the world-space hinge axis
                    v_hinge_world = v_bone.cross(v_child).normalized()
                    
                    # Transform this world vector into the Bone's Local Space
                    # If Bone Matrix is M, then: M_inv @ v_world = v_local
                    # We use the 3x3 rotational part of the matrix
                    mat_inv = bone.matrix_local.to_3x3().inverted()
                    v_hinge_local = mat_inv @ v_hinge_world
                    
                    # Find which local axis (X, Y, Z) strictly matches this vector
                    # Since Y is length, the hinge usually is X or Z.
                    ax, ay, az = abs(v_hinge_local.x), abs(v_hinge_local.y), abs(v_hinge_local.z)
                    
                    if ax > az and ax > ay:
                        hinge_axis = 'X'
                    elif az > ax and az > ay:
                        hinge_axis = 'Z'
                    # If Y is dominant, something is weird (twisting chain), ignore or default to X
                    
            except ValueError:
                pass
        
        straight_bones[bone.name] = is_straight
        hinge_axes[bone.name] = hinge_axis

    bpy.ops.object.mode_set(mode='POSE')
    
    for bone in armature_obj.pose.bones:
        # Check if LIMIT_ROTATION constraint exists
        has_limit = False
        for constraint in bone.constraints:
            if constraint.type == 'LIMIT_ROTATION':
                has_limit = True
                break
        
        if not has_limit:
            # 1. Geometric Heuristics
            is_straight = straight_bones.get(bone.name, False)
            detected_hinge = hinge_axes.get(bone.name, None)
            
            reason = "Default/Bent"
            limits = (90.0, 90.0, 90.0) # Default fallback
            
            if is_straight:
                # Straight: 90 degree cone
                limits = (90.0, 90.0, 90.0)
                reason = "Straight Chain"
            elif detected_hinge:
                # Arm/Hinge Rule identified!
                # Twist (Y) is typically restricted on hinges
                TWIST_LIMIT = 45.0  # Allow some twist for lowerarm/calf
                # Bend (Hinge) is free
                BEND_LIMIT = 135.0
                # Off-Axis is STRICT
                SIDE_LIMIT = 5.0
                
                if detected_hinge == 'X':
                    limits = (BEND_LIMIT, TWIST_LIMIT, SIDE_LIMIT) # X is bend
                else: # Z
                    limits = (SIDE_LIMIT, TWIST_LIMIT, BEND_LIMIT) # Z is bend
                
                reason = f"Hinge Detected ({detected_hinge})"
            else:
                # Bent but no clear hinge (or twist dominated), fallback to loose
                limits = (135.0, 135.0, 135.0)

            # 2. Keywork matching overrides (Prioritized)
            bone_name_lower = bone.name.lower()
            for key, val in BONE_LIMITS.items():
                if key in bone_name_lower:
                    if isinstance(val, tuple):
                        limits = val
                    else:
                        limits = (val, val, val)
                    reason = f"Match '{key}'"
                    break
            
            # Apply constraint
            constraint = bone.constraints.new('LIMIT_ROTATION')
            constraint.name = "Auto Limit Rotation"
            constraint.owner_space = 'LOCAL'
            
            # Limits in degrees from tuple (X, Y, Z)
            lim_x, lim_y, lim_z = limits
            
            # Convert to radians
            # Enable limits for all axes
            constraint.use_limit_x = True
            constraint.min_x = math.radians(-lim_x)
            constraint.max_x = math.radians(lim_x)
            
            constraint.use_limit_y = True
            constraint.min_y = math.radians(-lim_y)
            constraint.max_y = math.radians(lim_y)
            
            constraint.use_limit_z = True
            constraint.min_z = math.radians(-lim_z)
            constraint.max_z = math.radians(lim_z)
            
            count_updated += 1
            print(f"  Added limit to '{bone.name}': X={lim_x} Y={lim_y} Z={lim_z} ({reason})")
            
    bpy.ops.object.mode_set(mode='OBJECT')
    
    if count_updated > 0:
        print(f"Applied default limits to {count_updated} bones")
    else:
        print("No missing bone limits found")


def ensure_root_bone(armature_obj: bpy.types.Object) -> None:
    """
    Ensure a 'root' bone exists at (0,0,0) and is the parent of all other root bones.
    This is critical for Unreal Engine root motion and animation retargeting.
    """
    if armature_obj.type != 'ARMATURE':
        return
        
    bpy.ops.object.mode_set(mode='EDIT')
    edit_bones = armature_obj.data.edit_bones
    
    # 1. Search for an EXISTING geometric root (Top-level bone at 0,0,0)
    geometric_root = None
    for bone in edit_bones:
        if bone.parent is None:
            # Check if head is at origin (tolerance 0.001 units)
            if bone.head.length < 0.001:
                geometric_root = bone
                break
    
    # 2. Handle existing geometric root
    if geometric_root:
        # If it's not named 'root', simple rename (unless 'root' is taken by another bone)
        if geometric_root.name.lower() != 'root':
            # Check if 'root' name is taken by a DIFFERENT bone
            existing_named_root = edit_bones.get('root') or edit_bones.get('Root')
            if existing_named_root and existing_named_root != geometric_root:
                print(f"Renaming non-zero existing 'root' bone '{existing_named_root.name}' to 'root_legacy' to avoid conflict")
                existing_named_root.name = "root_legacy"
            
            print(f"Renaming geometric root '{geometric_root.name}' to 'root'")
            geometric_root.name = 'root'
            
        print(f"Valid geometric root found: '{geometric_root.name}'")
        bpy.ops.object.mode_set(mode='OBJECT')
        return

    # 3. No geometric root found -> We must create one
    
    # Check if 'root' name is mistakenly used by a bone NOT at origin (e.g. Hips)
    existing_named_root = edit_bones.get('root') or edit_bones.get('Root')
    if existing_named_root:
        # It's named root, but we know it's not at 0,0,0 (otherwise found in step 1)
        # We must rename it to make space for the REAL root
        print(f"taking existing 'root' bone '{existing_named_root.name}' (not at origin) and renaming to 'pelvis_or_legacy'")
        # Try to rename intelligently? For now, suffix.
        existing_named_root.name = existing_named_root.name + "_original"

    print("Creating new 'root' bone at (0,0,0)")
    root_bone = edit_bones.new('root')
    root_bone.head = (0, 0, 0)
    root_bone.tail = (0, 0, 10)  # Upward Z
    root_bone.roll = 0
    
    # Parent all top-level bones to this new root
    for bone in edit_bones:
        if bone.parent is None and bone != root_bone:
            bone.parent = root_bone
            print(f"  Parented '{bone.name}' to 'root'")
            
    bpy.ops.object.mode_set(mode='OBJECT')


def generate_ik_bones(armature_obj: bpy.types.Object) -> None:
    """
    Generate standard Unreal Engine virtual IK bones.
    - ik_foot_root, ik_foot_l, ik_foot_r
    - ik_hand_root, ik_hand_l, ik_hand_r, ik_hand_gun
    """
    if armature_obj.type != 'ARMATURE':
        return
        
    # Standard UE5 Mannequin IK Bone names
    ik_definitions = [
        # (Bone Name, Parent Name, Target Bone Name (to copy transform from))
        ('ik_foot_root', 'root', None),
        ('ik_foot_l', 'ik_foot_root', 'foot_l'),
        ('ik_foot_r', 'ik_foot_root', 'foot_r'),
        ('ik_hand_root', 'root', None),
        ('ik_hand_gun', 'ik_hand_root', 'hand_r'),
        ('ik_hand_l', 'ik_hand_gun', 'hand_l'),
        ('ik_hand_r', 'ik_hand_gun', 'hand_r'),
    ]
    
    bpy.ops.object.mode_set(mode='EDIT')
    edit_bones = armature_obj.data.edit_bones
    
    # Verify root exists (it should, from ensure_root_bone)
    if 'root' not in edit_bones:
        print("Skipping IK generation: No 'root' bone found.")
        bpy.ops.object.mode_set(mode='OBJECT')
        return
        
    created_count = 0
    
    for ik_name, parent_name, target_name in ik_definitions:
        if ik_name in edit_bones:
            continue
            
        if parent_name not in edit_bones:
            print(f"Skipping '{ik_name}': Parent '{parent_name}' not found.")
            continue
            
        # Create IK bone
        ik_bone = edit_bones.new(ik_name)
        ik_bone.parent = edit_bones[parent_name]
        
        # Position the bone
        if target_name and target_name in edit_bones:
            # Copy transform from target
            target_bone = edit_bones[target_name]
            ik_bone.head = target_bone.head
            ik_bone.tail = target_bone.tail
            ik_bone.roll = target_bone.roll
        else:
            # Default to root location or parent location
            parent_bone = edit_bones[parent_name]
            ik_bone.head = parent_bone.head
            ik_bone.tail = parent_bone.tail
            ik_bone.roll = parent_bone.roll
            
        created_count += 1
        
    print(f"Generated {created_count} IK bones")
    bpy.ops.object.mode_set(mode='OBJECT')
