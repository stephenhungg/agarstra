# Starter battle candidates

These are editable Blender assets for a source-timed battle prototype. The original ROM owns damage, targeting, turn order, movement and move selection. Runtime placement and scale belong on an outer actor group. All exported characters face glTF +Z with +Y up.

## Bulbasaur

`author_bulbasaur.py` builds a continuous head, torso and four legs from tailored loft surfaces, joined into one organic skin. A custom quadruped skeleton deforms the skin. The bulb has geometric lobe grooves, and eyes, claws and eyelids follow their appropriate bones. Dark source-inspired markings are embedded vertex colors. Skin pores and roughness are baked into embedded 1024-pixel maps so they survive GLB import.

The reference is `environment/starter-battle/bulbasaur-source-front.png`. No generated reference image was available. This is direct source-based Blender modeling, with a stylized PBR result. It is not a photoreal reconstruction.

Clips: `idle` (3 seconds), `attack` (1.1 seconds, Tackle preparation and follow-through), `growl` (1.2 seconds, head/body display), `hit` (0.6 seconds), and `faint` (1.4 seconds, clamped lowered pose). The foot transforms are baked after body and leg articulation to preserve contact. Growl has no jaw-open morph.

## Charmander

`author_charmander.py` retains the existing creator mesh, materials and 60-bone rig, then adds articulated Scratch, Growl, hit and faint reactions. The original idle is preserved. Scratch uses shoulder, elbow and wrist movement with spine rotation and tail counterbalance. Growl opens the jaw and moves the head and chest. Faint is an exhausted slump, not a full collapse.

The adjacent `models/charmander-battle-v3.license.txt` retains the original creator attribution and CC BY-NC 4.0 terms. The source models are unchanged.

## Squirtle

`author_squirtle.py` builds a connected blue skin with a 19-bone rig, segmented cream belly, brown shell and curled tail from the original FireRed source sprite. The corrected export is `squirtle-battle-v1.glb`, SHA256 `6cc80b3cb84aeec0e4f077b907ba324be38f2dec8ddbdb83244572214522114b`. All textures are embedded. No generated creature reference was available.

Clips: `idle`, `attack` (Tackle), `tailWhip`, `hit`, and `faint`. `squirtle_verify.py` samples the reimported GLB and the adjacent review JSON records exact bounds, motion and renders. This is a stylized candidate; shell rim junctions and material refinement remain.

## Verification

`verify_starter.py` imports the exact GLB into a fresh Blender scene, checks all animation frames, records skin bounds and foot travel, and renders front/back and sampled action views. `render_clip.py` renders a continuous MP4 from the imported inspection scene. Evidence and inspection `.blend` files are on Vault under `/Volumes/Vault/dev/agarstra-model-work/starter-battle-models/`.

Use the JSON review beside this README for exact hashes and measured results. Image inspection and technical checks allow candidate runtime review; they do not grant whole-scene or photoreal acceptance.

Example verification:

```sh
TMPDIR=/Volumes/Vault/Blender/Temp /Volumes/Vault/Applications/Blender.app/Contents/MacOS/Blender --background --python outputs/pokemon-remake/verification/starter-battle-models/verify_starter.py -- outputs/pokemon-remake/models/bulbasaur-battle-v1.glb /Volumes/Vault/dev/agarstra-model-work/starter-battle-models/bulbasaur
```
