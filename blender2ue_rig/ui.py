"""
UI Panels for UE Rig Converter
"""

import bpy
from bpy.types import Panel


class UERIG_PT_main_panel(Panel):
    """Main panel for UE Rig Converter"""
    bl_label = "UE Rig Converter"
    bl_idname = "UERIG_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "UE Rig"
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.ue_rig_converter

        # Conversion Settings
        box = layout.box()
        box.label(text="Conversion Settings", icon='SETTINGS')
        box.prop(props, "use_ue_naming")
        box.prop(props, "fix_bone_orientation")
        box.prop(props, "scale_factor")
        box.prop(props, "export_animations")
        
        layout.separator()
        
        # Actions
        box = layout.box()
        box.label(text="Actions", icon='PLAY')
        
        row = box.row(align=True)
        row.operator("uerig.validate_rig", text="Validate", icon='CHECKMARK')
        row.operator("uerig.convert_rig", text="Convert", icon='MOD_ARMATURE')
        
        box.separator()
        
        # Export
        box.operator("uerig.export_fbx", text="Export FBX", icon='EXPORT')
        
        layout.separator()
        
        # Info
        box = layout.box()
        box.label(text="Selected Objects:", icon='OBJECT_DATA')
        
        armature_count = sum(1 for obj in context.selected_objects if obj.type == 'ARMATURE')
        mesh_count = sum(1 for obj in context.selected_objects if obj.type == 'MESH')
        
        box.label(text=f"Armatures: {armature_count}")
        box.label(text=f"Meshes: {mesh_count}")


class UERIG_PT_advanced_panel(Panel):
    """Advanced settings panel"""
    bl_label = "Advanced Settings"
    bl_idname = "UERIG_PT_advanced_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "UE Rig"
    bl_parent_id = "UERIG_PT_main_panel"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.ue_rig_converter
        
        layout.prop(props, "add_root_bone")
        layout.prop(props, "preserve_custom_properties")
        layout.prop(props, "split_by_material")
        layout.prop(props, "encode_skin_weights")


# List of panel classes
classes = (
    UERIG_PT_main_panel,
    UERIG_PT_advanced_panel,
)


def register():
    """Register panel classes"""
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    """Unregister panel classes"""
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
