"""
UE Skeleton data structures and conversion utilities
Based on UE's FReferenceSkeleton
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from mathutils import Matrix, Vector, Quaternion
import bpy


@dataclass
class UEBone:
    """Represents a bone in UE's FReferenceSkeleton format"""
    name: str
    parent_index: int  # -1 for root bone
    local_transform: Matrix  # 4x4 transform relative to parent
    
    def __post_init__(self):
        """Ensure local_transform is a Matrix"""
        if not isinstance(self.local_transform, Matrix):
            self.local_transform = Matrix(self.local_transform)


@dataclass
class UESkeleton:
    """
    Represents UE's FReferenceSkeleton structure
    Stores the bind pose (T-pose) as local transforms
    """
    bones: List[UEBone] = field(default_factory=list)
    bone_name_to_index: Dict[str, int] = field(default_factory=dict)
    
    def add_bone(self, name: str, parent_index: int, local_transform: Matrix) -> int:
        """Add a bone and return its index"""
        bone_index = len(self.bones)
        bone = UEBone(name, parent_index, local_transform)
        self.bones.append(bone)
        self.bone_name_to_index[name] = bone_index
        return bone_index
    
    def get_bone_index(self, name: str) -> Optional[int]:
        """Get bone index by name"""
        return self.bone_name_to_index.get(name)
    
    def get_bone_global_transform(self, bone_index: int) -> Matrix:
        """
        Compute global transform by walking up parent chain
        Mirrors UE's get_ref_pose_single_bone_comp_space()
        """
        if bone_index < 0 or bone_index >= len(self.bones):
            return Matrix.Identity(4)
        
        result = self.bones[bone_index].local_transform.copy()
        current_index = bone_index
        
        while self.bones[current_index].parent_index >= 0:
            parent_index = self.bones[current_index].parent_index
            result = self.bones[parent_index].local_transform @ result
            current_index = parent_index
        
        return result
    
    def validate(self) -> tuple[bool, str]:
        """Validate skeleton structure"""
        if not self.bones:
            return False, "Skeleton has no bones"
        
        # Check for root bone
        root_count = sum(1 for bone in self.bones if bone.parent_index == -1)
        if root_count == 0:
            return False, "No root bone found"
        if root_count > 1:
            return False, f"Multiple root bones found ({root_count})"
        
        # Check parent indices
        for i, bone in enumerate(self.bones):
            if bone.parent_index >= i:
                return False, f"Bone '{bone.name}' has invalid parent index"
        
        return True, "Skeleton is valid"


# UE Bone naming conventions based on UE Mannequin
UE_BONE_NAME_MAPPINGS = {
    # Spine
    "hips": "pelvis",
    "spine": "spine_01",
    "spine.001": "spine_02",
    "spine.002": "spine_03",
    "spine1": "spine_02",
    "spine2": "spine_03",
    "neck": "neck_01",
    "head": "head",
    
    # Left Arm
    "shoulder.l": "clavicle_l",
    "shoulder.L": "clavicle_l",
    "upper_arm.l": "upperarm_l",
    "upper_arm.L": "upperarm_l",
    "forearm.l": "lowerarm_l",
    "forearm.L": "lowerarm_l",
    "hand.l": "hand_l",
    "hand.L": "hand_l",
    
    # Right Arm
    "shoulder.r": "clavicle_r",
    "shoulder.R": "clavicle_r",
    "upper_arm.r": "upperarm_r",
    "upper_arm.R": "upperarm_r",
    "forearm.r": "lowerarm_r",
    "forearm.R": "lowerarm_r",
    "hand.r": "hand_r",
    "hand.R": "hand_r",
    
    # Left Leg
    "thigh.l": "thigh_l",
    "thigh.L": "thigh_l",
    "shin.l": "calf_l",
    "shin.L": "calf_l",
    "foot.l": "foot_l",
    "foot.L": "foot_l",
    "toe.l": "ball_l",
    "toe.L": "ball_l",
    
    # Right Leg
    "thigh.r": "thigh_r",
    "thigh.R": "thigh_r",
    "shin.r": "calf_r",
    "shin.R": "calf_r",
    "foot.r": "foot_r",
    "foot.R": "foot_r",
    "toe.r": "ball_r",
    "toe.R": "ball_r",
}


def apply_ue_bone_naming(bone_name: str) -> str:
    """
    Convert bone name to UE convention
    Returns mapped name or sanitized original name
    """
    # Try direct mapping
    if bone_name in UE_BONE_NAME_MAPPINGS:
        return UE_BONE_NAME_MAPPINGS[bone_name]
    
    # Try lowercase mapping
    lower_name = bone_name.lower()
    if lower_name in UE_BONE_NAME_MAPPINGS:
        return UE_BONE_NAME_MAPPINGS[lower_name]
    
    # Sanitize name (UE doesn't allow spaces, special chars)
    sanitized = bone_name.replace(" ", "_")
    sanitized = sanitized.replace(".", "_")
    sanitized = ''.join(c for c in sanitized if c.isalnum() or c == '_')
    
    return sanitized


def convert_blender_armature_to_ue_skeleton(
    armature_obj: bpy.types.Object,
    use_ue_naming: bool = True
) -> UESkeleton:
    """
    Convert Blender armature to UE skeleton structure
    
    Args:
        armature_obj: Blender armature object
        use_ue_naming: Apply UE bone naming conventions
    
    Returns:
        UESkeleton with bones in bind pose
    """
    if armature_obj.type != 'ARMATURE':
        raise ValueError(f"Object '{armature_obj.name}' is not an armature")
    
    armature = armature_obj.data
    skeleton = UESkeleton()
    
    # Build bone hierarchy (breadth-first to ensure parents come first)
    bone_queue = [(bone, -1) for bone in armature.bones if bone.parent is None]
    processed = set()
    
    while bone_queue:
        bone, parent_idx = bone_queue.pop(0)
        
        if bone.name in processed:
            continue
        processed.add(bone.name)
        
        # Get bone name
        bone_name = apply_ue_bone_naming(bone.name) if use_ue_naming else bone.name
        
        # Get local transform (relative to parent)
        if bone.parent:
            local_transform = bone.parent.matrix_local.inverted() @ bone.matrix_local
        else:
            local_transform = bone.matrix_local.copy()
        
        # Add bone to skeleton
        bone_idx = skeleton.add_bone(bone_name, parent_idx, local_transform)
        
        # Add children to queue
        for child in bone.children:
            bone_queue.append((child, bone_idx))
    
    return skeleton


def validate_bone_hierarchy(skeleton: UESkeleton) -> tuple[bool, list[str]]:
    """
    Validate bone hierarchy for UE compatibility
    
    Returns:
        (is_valid, list of warnings/errors)
    """
    issues = []
    
    # Basic validation
    is_valid, msg = skeleton.validate()
    if not is_valid:
        issues.append(f"ERROR: {msg}")
        return False, issues
    
    # Check bone names
    for bone in skeleton.bones:
        if not bone.name:
            issues.append(f"ERROR: Bone at index {skeleton.bones.index(bone)} has no name")
            return False, issues
        
        # Check for invalid characters
        if any(c in bone.name for c in [' ', '.', '-']):
            issues.append(f"WARNING: Bone '{bone.name}' contains special characters")
    
    # Check for common required bones (for humanoid rigs)
    required_bones = ['pelvis', 'spine_01', 'head']
    missing_required = []
    for req_bone in required_bones:
        if req_bone not in skeleton.bone_name_to_index:
            missing_required.append(req_bone)
    
    if missing_required:
        issues.append(f"WARNING: Missing common bones: {', '.join(missing_required)}")
    
    return True, issues
