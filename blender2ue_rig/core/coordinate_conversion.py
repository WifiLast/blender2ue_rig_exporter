"""
Coordinate system conversion between Blender and Unreal Engine
"""

from mathutils import Matrix, Vector, Quaternion, Euler
import math


def blender_to_ue_transform(blender_matrix: Matrix) -> Matrix:
    """
    Convert Blender Z-up right-handed to UE Z-up left-handed
    
    Conversion: Flip Y axis to convert handedness
    
    Args:
        blender_matrix: 4x4 transform matrix in Blender space
    
    Returns:
        4x4 transform matrix in UE space
    """
    # Conversion matrix to flip Y axis
    conversion = Matrix((
        (1,  0, 0, 0),
        (0, -1, 0, 0),  # Flip Y
        (0,  0, 1, 0),
        (0,  0, 0, 1)
    ))
    
    return conversion @ blender_matrix @ conversion.inverted()


def ue_to_blender_transform(ue_matrix: Matrix) -> Matrix:
    """
    Convert UE Z-up left-handed to Blender Z-up right-handed
    (Inverse of blender_to_ue_transform)
    """
    # Same conversion matrix (symmetric operation)
    conversion = Matrix((
        (1,  0, 0, 0),
        (0, -1, 0, 0),
        (0,  0, 1, 0),
        (0,  0, 0, 1)
    ))
    
    return conversion @ ue_matrix @ conversion.inverted()


def apply_ue_scale(value: float, scale_factor: float = 100.0) -> float:
    """
    Apply UE scale factor
    
    UE typically uses centimeters (scale 100) vs Blender's meters
    
    Args:
        value: Value in Blender units (meters)
        scale_factor: Scale factor (default 100 for cm)
    
    Returns:
        Value in UE units
    """
    return value * scale_factor


def apply_ue_scale_to_vector(vec: Vector, scale_factor: float = 100.0) -> Vector:
    """Apply UE scale to a vector"""
    return Vector((
        vec.x * scale_factor,
        vec.y * scale_factor,
        vec.z * scale_factor
    ))


def apply_ue_scale_to_matrix(mat: Matrix, scale_factor: float = 100.0) -> Matrix:
    """
    Apply UE scale to a transformation matrix
    Only scales the translation component, not rotation
    """
    result = mat.copy()
    # Scale translation component
    result[0][3] *= scale_factor
    result[1][3] *= scale_factor
    result[2][3] *= scale_factor
    return result


def convert_bone_transform_to_ue(
    blender_matrix: Matrix,
    scale_factor: float = 100.0,
    convert_coordinates: bool = True
) -> Matrix:
    """
    Complete conversion of bone transform from Blender to UE
    
    Args:
        blender_matrix: Bone transform in Blender space
        scale_factor: Scale factor for UE
        convert_coordinates: Apply coordinate system conversion
    
    Returns:
        Bone transform ready for UE
    """
    result = blender_matrix.copy()
    
    # Apply coordinate conversion
    if convert_coordinates:
        result = blender_to_ue_transform(result)
    
    # Apply scale
    result = apply_ue_scale_to_matrix(result, scale_factor)
    
    return result


def get_fbx_to_ue_conversion_matrix() -> Matrix:
    """
    Get the conversion matrix for FBX export that will result in correct UE import
    
    FBX uses Y-up right-handed by default
    UE expects Z-up left-handed
    
    Returns:
        Conversion matrix to apply during FBX export
    """
    # Rotate 90 degrees around X to convert Y-up to Z-up
    # Then flip Y to convert right-handed to left-handed
    rotation_x_90 = Matrix.Rotation(math.radians(90), 4, 'X')
    flip_y = Matrix((
        (1,  0, 0, 0),
        (0, -1, 0, 0),
        (0,  0, 1, 0),
        (0,  0, 0, 1)
    ))
    
    return flip_y @ rotation_x_90


def decompose_transform(matrix: Matrix) -> tuple[Vector, Quaternion, Vector]:
    """
    Decompose a 4x4 matrix into translation, rotation, scale
    
    Returns:
        (translation, rotation_quaternion, scale)
    """
    translation = matrix.to_translation()
    rotation = matrix.to_quaternion()
    scale = matrix.to_scale()
    
    return translation, rotation, scale


def compose_transform(
    translation: Vector,
    rotation: Quaternion,
    scale: Vector
) -> Matrix:
    """
    Compose a 4x4 matrix from translation, rotation, scale
    """
    mat_loc = Matrix.Translation(translation)
    mat_rot = rotation.to_matrix().to_4x4()
    mat_scale = Matrix.Diagonal(scale).to_4x4()
    
    return mat_loc @ mat_rot @ mat_scale
