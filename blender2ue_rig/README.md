# Blender to UE Rig Converter

Converts GLB rigged models to Unreal Engine compatible skeletal meshes.

## Features

- **Built-in GLB/GLTF Import**: Use Blender's native importer for rigged models
- **UE Bone Naming**: Automatic conversion to UE naming conventions
- **Coordinate Conversion**: Handles Blender Z-up RH to UE Z-up LH
- **FBX Export**: Export with UE-optimized settings
- **Validation**: Check rig compatibility before export

## Installation

1. Copy the `blender2ue_rig` folder to your Blender addons directory:
   - Windows: `%APPDATA%\Blender Foundation\Blender\<version>\scripts\addons\`
   - macOS: `~/Library/Application Support/Blender/<version>/scripts/addons/`
   - Linux: `~/.config/blender/<version>/scripts/addons/`

2. Open Blender
3. Go to Edit → Preferences → Add-ons
4. Search for "UE Rig Converter"
5. Enable the addon

## Usage

1. **Import GLB**:
   - Use Blender's built-in importer: File -> Import -> glTF 2.0 (.glb/.gltf)
   - Import your rigged GLB/GLTF file before using the add-on

2. **Configure Settings**:
   - Enable "Use UE Naming Conventions" to rename bones
   - Set scale factor (default 100 for cm)
   - Choose whether to export animations

3. **Validate**:
   - Select the armature
   - Click "Validate" to check UE compatibility

4. **Convert**:
   - Select armature and meshes
   - Click "Convert" to prepare for export

5. **Export**:
   - Click "Export FBX" and choose output location
   - Import the FBX into Unreal Engine

## Bone Naming Conventions

The addon automatically maps common bone names to UE conventions:

- `hips` → `pelvis`
- `spine` → `spine_01`
- `shoulder.L` → `clavicle_l`
- `upper_arm.L` → `upperarm_l`
- And many more...

## Requirements

- Blender 3.0 or higher
- GLB/GLTF files with armature and mesh

## Troubleshooting

**"No armature selected"**: Make sure you have an armature object selected in the 3D viewport.

**"Validation failed"**: Check the console for specific errors. Common issues:
- Missing root bone
- Invalid bone hierarchy
- Special characters in bone names

**FBX import issues in UE**: Ensure you're using the correct import settings in UE:
- Skeletal Mesh selected
- Import Animations enabled (if needed)
- Convert Scene enabled

## Future Features

- Skin weight profile support
- LOD generation
- Custom bone mapping editor
