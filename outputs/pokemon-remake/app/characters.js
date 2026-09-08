import * as THREE from 'three';
import {CHARACTER_SOURCE, readCharacterMemory, decodeCharacterSprite} from './character-source.mjs';

// One scene-level owner for source actors across maps. No simulation or timing.
// Use playerModelVisible only when a model actually renders this source form.
export function createCharacters({pixelsPerUnit = 16} = {}) {
  if (!Number.isFinite(pixelsPerUnit) || pixelsPerUnit <= 0) throw Error('Invalid character pixel scale');
  const group = new THREE.Group(); group.name = 'Source object actors';
  const actors = new Map();
  const report = {status: 'source-sprite-fallback', source: CHARACTER_SOURCE,
    frame: null, map: null, actors: [], unsupported: [],
    limitations: ['2D source actors in a 3D scene; no photoreal acceptance',
      'Only active source ObjectEvents exist; no off-map actor simulation',
      'Affine/8bpp actors, source mosaic and OBJ blending are not reconstructed']};
  function release(actor) {
    actor.sprite.material.map.dispose(); actor.sprite.material.dispose(); actor.sprite.removeFromParent();
  }
  function update(core, state, {visible = true, playerModelVisible = false, modelGraphicsIds = [], groundHeight = 0} = {}) {
    group.visible = Boolean(visible && state?.phase === 'overworld' && !state?.battle?.active);
    report.frame = state?.frame; report.map = state?.map?.name ?? null;
    report.actors = []; report.unsupported = [];
    const present = new Set(), memory = group.visible ? readCharacterMemory(core) : null;
    for (const object of memory ? state.objectEvents ?? [] : []) {
      // `visible`, `spriteInvisible` and `offScreen` include the native viewport
      // cull. Only source script-hidden is authoritative for this wider view.
      if (object.hidden || modelGraphicsIds.includes(object.graphicsId) || (object.isPlayer && playerModelVisible)) continue;
      const decoded = decodeCharacterSprite(memory, object.spriteId);
      if (!decoded || decoded.unsupported) {
        report.unsupported.push({id: object.id, graphicsId: object.graphicsId, reason: decoded?.unsupported ?? 'inactive or invalid sprite'});
        continue;
      }
      const map = state.map, key = `${map?.group}:${map?.number}:${object.id}:${object.localId}:${object.graphicsId}`;
      present.add(key);
      let actor = actors.get(key);
      if (actor && (actor.width !== decoded.width || actor.height !== decoded.height)) {
        release(actor); actors.delete(key); actor = null;
      }
      if (!actor) {
        const texture = new THREE.DataTexture(decoded.rgba, decoded.width, decoded.height, THREE.RGBAFormat);
        texture.colorSpace = THREE.SRGBColorSpace; texture.magFilter = THREE.NearestFilter;
        texture.minFilter = THREE.NearestFilter; texture.generateMipmaps = false;
        texture.flipY = true; texture.needsUpdate = true;
        const material = new THREE.SpriteMaterial({map: texture, alphaTest: .5, transparent: false, depthWrite: true, toneMapped: false});
        const sprite = new THREE.Sprite(material); sprite.name = `Source actor ${key}`;
        sprite.center.set(.5, 0); sprite.scale.set(decoded.width / pixelsPerUnit, decoded.height / pixelsPerUnit, 1);
        group.add(sprite); actor = {sprite, width: decoded.width, height: decoded.height, hash: decoded.pixelHash}; actors.set(key, actor);
      } else if (actor.hash !== decoded.pixelHash) {
        actor.sprite.material.map.image.data.set(decoded.rgba); actor.sprite.material.map.needsUpdate = true;
        actor.hash = decoded.pixelHash;
      }
      // ObjectEvent world coordinates are the ground anchor. Both source visual
      // offsets remain presentation-only; negative vertical offsets are jumps.
      const ground = typeof groundHeight === 'function' ? groundHeight(object, state) : groundHeight;
      actor.sprite.position.set(object.worldX + (object.visualOffsetX || 0),
        ground + .025 - (object.visualOffsetY || 0), object.worldY);
      actor.sprite.visible = decoded.opaquePixels > 0;
      const {rgba, ...source} = decoded;
      report.actors.push({key, id: object.id, localId: object.localId, graphicsId: object.graphicsId,
        isPlayer: object.isPlayer, facing: object.facing, moving: object.moving,
        offScreen: object.offScreen, visible: actor.sprite.visible, position: actor.sprite.position.toArray(), ...source});
    }
    // Destroy retired lifetimes, including map changes and script disappearance.
    // This also bounds GPU resources while navigating/reloading checkpoints.
    for (const [key, actor] of actors) if (!present.has(key)) {release(actor); actors.delete(key);}
    return report;
  }
  return {group, update, report, dispose() {for (const actor of actors.values()) release(actor); actors.clear(); group.removeFromParent();}};
}
