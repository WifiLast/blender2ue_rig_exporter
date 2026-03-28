import unreal

# ==============================================================================
# Bone Limits Configuration (Mirrored from blender2ue_rig)
# ==============================================================================
# Format: 'bone_name_part': (Swing1, Twist, Swing2) in degrees
# Note: Unreal uses Swing1 (Z), Swing2 (Y), Twist (X) usually, but mapping varies.
# We will assume:
#   X in Blender (Main Bend) -> Swing 1 (Z in UE PhAT default text, but often Swing 2 depending on orientation)
#   Y in Blender (Twist)     -> Twist (X in UE)
#   Z in Blender (Side)      -> Swing 2 (Y in UE)
#
# However, UE Physics constraints are:
#   Swing 1
#   Swing 2
#   Twist
#
# We'll map Blender (X, Y, Z) -> UE (Swing1, Twist, Swing2) roughly.
# Adjust mapping as needed for your specific skeleton orientation.

BONE_LIMITS = {
    # Torso (Ball/Universal)
    'head': (60.0, 60.0, 70.0),      # Swing1, Twist, Swing2
    'neck': (60.0, 60.0, 70.0),
    'spine': (45.0, 45.0, 45.0),
    'pelvis': (180.0, 180.0, 180.0), # Free

    # Shoulders
    'clavicle': (20.0, 20.0, 20.0),
    'shoulder': (20.0, 20.0, 20.0),

    # Upper Limbs
    'upperarm': (130.0, 90.0, 130.0),
    'upper_arm': (130.0, 90.0, 130.0),

    # Hinge Joints (Elbows) -> Restrict Twist and Side
    # Blender: X=Bend, Y=Twist, Z=Side
    # UE: Swing1=Bend, Twist, Swing2=Side
    'lowerarm': (135.0, 30.0, 15.0),
    'forearm': (135.0, 30.0, 15.0),
    'hand': (90.0, 45.0, 90.0),

    # Lower Limbs
    'thigh': (130.0, 45.0, 130.0),

    # Knees (Hinge)
    'calf': (135.0, 10.0, 5.0),
    'shin': (135.0, 10.0, 5.0),
    'foot': (90.0, 30.0, 45.0),
    'ball': (45.0, 5.0, 5.0),
    'toe': (45.0, 5.0, 5.0),

    # Fingers
    'thumb': (90.0, 45.0, 90.0),
    'index': (90.0, 10.0, 15.0),
    'middle': (90.0, 10.0, 15.0),
    'ring': (90.0, 10.0, 15.0),
    'pinky': (90.0, 10.0, 15.0),
}

def get_limit_for_bone(bone_name):
    """Find matching limit rule for a bone name."""
    bone_name_lower = bone_name.lower()
    for key, limits in BONE_LIMITS.items():
        if key in bone_name_lower:
            return limits
    return (45.0, 45.0, 45.0) # Default fallback

def apply_limits_to_constraint(constraint_setup, limits):
    """Apply angular limits to a ConstraintInstance."""
    
    # limits = (Swing1, Twist, Swing2)
    swing1_deg, twist_deg, swing2_deg = limits
    
    # Access the default instance (the runtime instance profile)
    # Note: Structure might vary slightly by UE version.
    # We access 'default_instance' or use accessor functions.
    
    # In Python API, we often modify properties directly on the object wrapper
    
    # 1. Set Motion Types (Free vs Limited vs Locked)
    # We assume 'Limited' if > 5 degrees, 'Locked' if very small (practically 0), 'Free' if > 170
    
    def get_motion_type(deg):
        if deg < 5.0:
            return unreal.AngularConstraintMotion.ACM_LOCKED
        elif deg >= 170.0:
            return unreal.AngularConstraintMotion.ACM_FREE
        else:
            return unreal.AngularConstraintMotion.ACM_LIMITED

    # Setup Profile (Default profile)
    profile = constraint_setup.get_editor_property("default_instance").get_editor_property("profile_instance")
    cone_limit = profile.get_editor_property("cone_limit")
    twist_limit = profile.get_editor_property("twist_limit")
    
    # --- Angular Swing 1 (Cone 1) ---
    motion_s1 = get_motion_type(swing1_deg)
    cone_limit.set_editor_property("swing1_motion", motion_s1)
    if motion_s1 == unreal.AngularConstraintMotion.ACM_LIMITED:
        cone_limit.set_editor_property("swing1_limit_degrees", swing1_deg)
        
    # --- Angular Swing 2 (Cone 2) ---
    motion_s2 = get_motion_type(swing2_deg)
    cone_limit.set_editor_property("swing2_motion", motion_s2)
    if motion_s2 == unreal.AngularConstraintMotion.ACM_LIMITED:
        cone_limit.set_editor_property("swing2_limit_degrees", swing2_deg)
        
    # --- Angular Twist ---
    motion_t = get_motion_type(twist_deg)
    twist_limit.set_editor_property("twist_motion", motion_t)
    if motion_t == unreal.AngularConstraintMotion.ACM_LIMITED:
        twist_limit.set_editor_property("twist_limit_degrees", twist_deg)

    # Note: Typically we lock Linear Motion for skeletal joints
    linear_limit = profile.get_editor_property("linear_limit")
    linear_limit.set_editor_property("x_motion", unreal.LinearConstraintMotion.LCM_LOCKED)
    linear_limit.set_editor_property("y_motion", unreal.LinearConstraintMotion.LCM_LOCKED)
    linear_limit.set_editor_property("z_motion", unreal.LinearConstraintMotion.LCM_LOCKED)

    unreal.log(f"Applied limits to constraint: Swing1={swing1_deg}, Twist={twist_deg}, Swing2={swing2_deg}")


def main():
    # Get selected assets
    selected_assets = unreal.EditorUtilityLibrary.get_selected_assets()
    physics_assets = [a for a in selected_assets if isinstance(a, unreal.PhysicsAsset)]
    
    if not physics_assets:
        unreal.log_warning("No Physics Asset selected. Please select a Physics Asset.")
        return

    for phat in physics_assets:
        unreal.log(f"Processing Physics Asset: {phat.get_name()}")
        
        # Get all constraints
        # Note: Accessing internal arrays in Python can be tricky.
        # This relies on the 'constraint_setup' property being exposed.
        constraints = phat.get_editor_property("constraint_setup")
        
        if not constraints:
            unreal.log_warning("No constraints found in asset.")
            continue
            
        count = 0
        for constraint in constraints:
            # joint_name tells us which bone this constraint controls
            # Note: joint_name might be a 'Name' or property 'default_instance.joint_name'
            
            # ConstraintSetup -> DefaultInstance -> JointName
            default_instance = constraint.get_editor_property("default_instance")
            joint_name = default_instance.get_editor_property("joint_name_in_model") # or just "joint_name"
            
            # If joint_name is None/Invalid, try to derive from BoneName (Constraint Bone 1)
            if not joint_name or joint_name == "None":
                 joint_name = constraint.get_editor_property("default_instance").get_editor_property("constraint_bone1")

            bone_name = str(joint_name)
            unreal.log(f"  Constraint for Bone: {bone_name}")
            
            limits = get_limit_for_bone(bone_name)
            apply_limits_to_constraint(constraint, limits)
            count += 1
            
        unreal.log(f"Updated {count} constraints for {phat.get_name()}")

if __name__ == "__main__":
    main()
