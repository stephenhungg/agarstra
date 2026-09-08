# Character Animation Library

These are real named glTF animation clips and matching editable Blender NLA tracks.
The authored source meshes, UVs, and embedded material maps are retained; rigid parts
are grouped by material under transform pivots. The original family models are unchanged.

Clips are in-place. Runtime position, collision, facing, state selection and timing must
come from the ROM. Loop idle/walk/run/bite; clamp one-shot pose clips at their final frame.
The manifest records durations, source hashes, bounds, and channel counts.

Open `animated-library.blend` and press Play: walking and biting tracks are enabled
and repeated over the inspection timeline. To inspect another clip, mute the current
track and unmute the same new track name on each of that character's pivots.

This is rigid part animation, not skinning, mocap, or a facial animation rig.
The Piranha bite compresses the existing continuous head; it has no separate jaw mesh.
`pose-contact-sheet.png` shows evaluated authored poses for visual inspection.

Rebuild from the project root:

```sh
/Volumes/Blender/Blender.app/Contents/MacOS/Blender -b -t 4 --python-exit-code 1 --python outputs/smb3-photoreal/tools/animate_characters.py -- --root "$PWD"
```
