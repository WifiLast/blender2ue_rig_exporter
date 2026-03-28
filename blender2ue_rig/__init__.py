"""
Blender to UE Rig Converter
Converts GLB rigged models to Unreal Engine compatible format
"""

bl_info = {
    "name": "Blender to UE Rig Converter",
    "author": "Generated",
    "version": (1, 0, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > UE Rig",
    "description": "Convert GLB rigged models to UE-compatible skeletal meshes",
    "category": "Import-Export",
    "doc_url": "",
    "tracker_url": "",
}

import bpy
from . import operators, properties, ui

def register():
    """Register addon classes"""
    properties.register()
    operators.register()
    ui.register()
    
    # Add properties to scene
    bpy.types.Scene.ue_rig_converter = bpy.props.PointerProperty(
        type=properties.UERigConverterProperties
    )

def unregister():
    """Unregister addon classes"""
    ui.unregister()
    operators.unregister()
    properties.unregister()
    
    # Remove properties from scene
    del bpy.types.Scene.ue_rig_converter

if __name__ == "__main__":
    register()
