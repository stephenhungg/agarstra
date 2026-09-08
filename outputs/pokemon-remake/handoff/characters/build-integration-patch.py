"""Emit a reviewable patch against the integration checkout; never edit it."""
import argparse
import difflib
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('reference', type=Path, help='repository root to read, without changing it')
args = parser.parse_args()
out = Path(__file__).resolve().parent
prefix = 'outputs/pokemon-remake/app/'
patches = []

def edit(name, replacements):
    before = (args.reference / prefix / name).read_text()
    after = before
    for old, new in replacements:
        assert after.count(old) == 1, f'{name}: expected unique integration anchor: {old}'
        after = after.replace(old, new)
    patches.extend(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                   fromfile='a/' + prefix + name, tofile='b/' + prefix + name, n=1))

edit('town.js', [
    ('playerModelVisible=false;', 'playerModelVisible=false,sourceCharactersVisible=false;'),
    ('actor.visible=!(obj.isPlayer&&playerModelVisible);', 'actor.visible=!sourceCharactersVisible&&!(obj.isPlayer&&playerModelVisible);'),
    ('return {group,update,setPlayerModelVisible', 'return {group,update,setSourceCharactersVisible(value){sourceCharactersVisible=value;for(const a of actors.values())a.visible=false;},setPlayerModelVisible'),
    ("'trainer and NPCs use temporary markers'", "'source actors are supplied by the scene-level character renderer'"),
])
edit('route1.js', [
    ('showPlayerMarker=true;', 'showPlayerMarker=true,sourceCharactersVisible=false;'),
    ('a.visible=!obj.isPlayer||showPlayerMarker;', 'a.visible=!sourceCharactersVisible&&(!obj.isPlayer||showPlayerMarker);'),
    ('visible=showPlayerMarker&&group.visible;', 'visible=!sourceCharactersVisible&&showPlayerMarker&&group.visible;'),
    ('return{group,camera,update,resize,setPlayerModelVisible,', 'return{group,camera,update,resize,setSourceCharactersVisible(value){sourceCharactersVisible=value;for(const a of actors.values())a.visible=false;},setPlayerModelVisible,'),
    ('markers are interim trainer/NPC visuals.', 'source actor sprites are supplied by the scene-level character renderer.'),
])
edit('interiors.js', [
    ('playerModelVisible=false;', 'playerModelVisible=false,sourceCharactersVisible=false;'),
    ('a.visible=!(obj.isPlayer&&playerModelVisible);', 'a.visible=!sourceCharactersVisible&&!(obj.isPlayer&&playerModelVisible);'),
    ('return{group,camera,update,setPlayerModelVisible', 'return{group,camera,update,setSourceCharactersVisible(value){sourceCharactersVisible=value;for(const r of rooms.values())for(const a of r.actors.values())a.visible=false;},setPlayerModelVisible'),
    ("'trainer and NPC actors remain temporary markers'", "'source actors are supplied by the scene-level character renderer'"),
])
edit('main.js', [
    ("import {createAvatar} from './avatar.js';", "import {createAvatar} from './avatar.js';\nimport {createCharacters} from './characters.js';"),
    ('let route1=null,avatar=null;', 'let route1=null,avatar=null;\nconst characters=createCharacters();scene.add(characters.group);characters.group.visible=false;'),
    ("avatar?.update(state,{visible:!native&&!inBattle&&viewMode==='town',groundHeight:inInterior?0:-.005});",
     "avatar?.update(state,{visible:!native&&!inBattle&&viewMode==='town'&&state.player?.graphicsId===0,groundHeight:inInterior?0:-.005});\n  town?.setSourceCharactersVisible(true);route1?.setSourceCharactersVisible(true);interiors?.setSourceCharactersVisible(true);\n  characters.update(core,state,{visible:!native&&!inBattle&&viewMode==='town',playerModelVisible:Boolean(avatar?.group.visible),groundHeight:o=>inInterior?(o.graphicsId===92?.82:o.graphicsId===94?.78:0):-.005});"),
    ('avatar:avatar?.report,', 'characters:characters.report,avatar:avatar?.report,'),
    ('town.actorPositions.some(a=>a.id===o.id&&a.visible)', 'characters.report.actors.some(a=>a.id===o.id&&a.visible)'),
    ('renderedActors:town.actorPositions.filter(a=>a.visible).length', 'renderedActors:characters.report.actors.filter(a=>a.visible).length'),
])
(out / 'integration.patch').write_text(''.join(patches))
print(out / 'integration.patch')
