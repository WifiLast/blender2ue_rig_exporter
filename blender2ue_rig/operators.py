"""
Operators for UE Rig Converter
"""

import bpy
from bpy.types import Operator
from bpy.props import StringProperty
from bpy_extras.io_utils import ExportHelper
import os

from .core.ue_skeleton import (
    convert_blender_armature_to_ue_skeleton,
    validate_bone_hierarchy
)
from .core.fbx_exporter import (
    export_fbx_for_ue,
    prepare_armature_for_export,
    prepare_mesh_for_export
)


class UERIG_OT_validate_rig(Operator):
    """Validate rig for UE compatibility"""
    bl_idname = "uerig.validate_rig"
    bl_label = "Validate Rig"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        """Validate selected armature"""
        armature_obj = context.active_object
        
        if not armature_obj or armature_obj.type != 'ARMATURE':
            self.report({'ERROR'}, "No armature selected")
            return {'CANCELLED'}
        
        props = context.scene.ue_rig_converter
        
        try:
            # Convert to UE skeleton
            skeleton = convert_blender_armature_to_ue_skeleton(
                armature_obj,
                use_ue_naming=props.use_ue_naming
            )
            
            # Validate
            is_valid, issues = validate_bone_hierarchy(skeleton)
            
            if is_valid:
                self.report({'INFO'}, f"Rig is valid! {len(skeleton.bones)} bones")
                if issues:
                    for issue in issues:
                        self.report({'WARNING'}, issue)
            else:
                for issue in issues:
                    self.report({'ERROR'}, issue)
                return {'CANCELLED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Validation failed: {str(e)}")
            return {'CANCELLED'}
        
        return {'FINISHED'}


class UERIG_OT_convert_rig(Operator):
    """Convert rig to UE format"""
    bl_idname = "uerig.convert_rig"
    bl_label = "Convert to UE Format"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        """Convert selected armature and meshes"""
        armature_obj = None
        mesh_objects = []
        
        # Find armature and meshes
        for obj in context.selected_objects:
            if obj.type == 'ARMATURE':
                armature_obj = obj
            elif obj.type == 'MESH':
                mesh_objects.append(obj)
        
        # Auto-detect child meshes if only armature is selected
        if armature_obj:
            for child in armature_obj.children:
                if child.type == 'MESH' and child not in mesh_objects:
                    mesh_objects.append(child)
        
        if not armature_obj:
            self.report({'ERROR'}, "No armature selected")
            return {'CANCELLED'}
        
        props = context.scene.ue_rig_converter
        
        try:
            # Prepare armature
            prepare_armature_for_export(
                armature_obj,
                use_ue_naming=props.use_ue_naming
            )
            
            # Prepare meshes
            for mesh_obj in mesh_objects:
                prepare_mesh_for_export(mesh_obj)
            
            self.report({'INFO'}, f"Converted {len(mesh_objects)} meshes with armature")
            
        except Exception as e:
            self.report({'ERROR'}, f"Conversion failed: {str(e)}")
            return {'CANCELLED'}
        
        return {'FINISHED'}


class UERIG_OT_export_fbx(Operator, ExportHelper):
    """Export to FBX for UE import"""
    bl_idname = "uerig.export_fbx"
    bl_label = "Export FBX for UE"
    bl_options = {'REGISTER'}
    
    filename_ext = ".fbx"
    filter_glob: StringProperty(
        default="*.fbx",
        options={'HIDDEN'},
    )
    
    def execute(self, context):
        """Export to FBX"""
        props = context.scene.ue_rig_converter
        props.output_fbx_path = self.filepath
        
        armature_obj = None
        mesh_objects = []
        
        # Find armature and meshes
        for obj in context.selected_objects:
            if obj.type == 'ARMATURE':
                armature_obj = obj
            elif obj.type == 'MESH':
                mesh_objects.append(obj)
        
        # Auto-detect child meshes if only armature is selected
        if armature_obj:
            for child in armature_obj.children:
                if child.type == 'MESH' and child not in mesh_objects:
                    mesh_objects.append(child)
        
        if not armature_obj and not mesh_objects:
            self.report({'ERROR'}, "No objects selected")
            return {'CANCELLED'}
        
        try:
            # Count textures before export
            texture_count = 0
            for obj in mesh_objects:
                if obj.data.materials:
                    for mat_slot in obj.data.materials:
                        if mat_slot and mat_slot.use_nodes:
                            for node in mat_slot.node_tree.nodes:
                                if node.type == 'TEX_IMAGE' and node.image and node.image.filepath:
                                    texture_count += 1
            
            success = export_fbx_for_ue(
                self.filepath,
                armature_obj,
                mesh_objects,
                scale_factor=props.scale_factor,
                export_animations=props.export_animations
            )
            
            if success:
                msg = f"Exported: {os.path.basename(self.filepath)}"
                if texture_count > 0:
                    msg += f" ({texture_count} texture(s) copied)"
                self.report({'INFO'}, msg)
                return {'FINISHED'}
            else:
                self.report({'ERROR'}, "Export failed")
                return {'CANCELLED'}
                
        except Exception as e:
            self.report({'ERROR'}, f"Export failed: {str(e)}")
            return {'CANCELLED'}


# List of operator classes
classes = (
    UERIG_OT_validate_rig,
    UERIG_OT_convert_rig,
    UERIG_OT_export_fbx,
)


def register():
    """Register operator classes"""
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    """Unregister operator classes"""
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
