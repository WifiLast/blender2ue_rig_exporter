"""
Properties for UE Rig Converter addon
"""

import bpy
from bpy.props import StringProperty, BoolProperty, FloatProperty
from bpy.types import PropertyGroup


class UERigConverterProperties(PropertyGroup):
    """Properties for the UE Rig Converter"""
    
    output_fbx_path: StringProperty(
        name="Output FBX",
        description="Path to output FBX file for UE import",
        subtype='FILE_PATH',
        default="",
    )
    
    # Conversion settings
    use_ue_naming: BoolProperty(
        name="Use UE Naming Conventions",
        description="Rename bones to match UE naming conventions (e.g., pelvis, spine_01)",
        default=True,
    )
    
    fix_bone_orientation: BoolProperty(
        name="Fix Bone Orientation",
        description="Adjust bone orientations for UE coordinate system",
        default=True,
    )
    
    add_root_bone: BoolProperty(
        name="Add Root Bone",
        description="Add a root bone if not present (required by UE)",
        default=True,
    )
    
    scale_factor: FloatProperty(
        name="Scale Factor",
        description="Scale factor for UE (increase if model is too small in UE)",
        default=1.0,
        min=0.01,
        max=100000.0,
    )
    
    # Advanced settings
    preserve_custom_properties: BoolProperty(
        name="Preserve Custom Properties",
        description="Keep custom bone properties from source",
        default=False,
    )
    
    export_animations: BoolProperty(
        name="Export Animations",
        description="Include animations in export",
        default=True,
    )
    
    split_by_material: BoolProperty(
        name="Split by Material",
        description="Split mesh into sections by material (UE requirement)",
        default=True,
    )
    
    encode_skin_weights: BoolProperty(
        name="Encode Skin Weights (8-bit)",
        description="Encode skin weights to UE's 8-bit format",
        default=True,
    )


def register():
    """Register property classes"""
    bpy.utils.register_class(UERigConverterProperties)


def unregister():
    """Unregister property classes"""
    bpy.utils.unregister_class(UERigConverterProperties)
