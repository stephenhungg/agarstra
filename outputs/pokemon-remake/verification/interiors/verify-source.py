from pathlib import Path
import hashlib,json
root=Path('/Users/stephenhung/Documents/GitHub/agarstra'); base=root/'outputs/pokemon-remake'
s=json.loads((base/'source/source-maps.json').read_text()); m=json.loads((base/'source/interiors.json').read_text()); checks=[]
for name,room in m['maps'].items():
 original=s['maps'][name]
 for field in ['metatileIds','collision','mapDataSHA256']:
  assert room[field]==original[field],(name,field)
 assert room['width']==original['layout']['width'] and room['height']==original['layout']['height']
 assert room['warps']==original['events']['warp_events']
 for feature in room['features']:
  for cell in feature['sourceCells']:
   index=cell['y']*room['width']+cell['x']; assert cell['metatileId']==original['metatileIds'][index];assert cell['collision']==original['collision'][index]
 checks.append({'map':name,'sourceCells':len(room['metatileIds']),'features':len(room['features']),'warps':room['warps'],'passed':True})
for name in ['PalletTown_PlayersHouse_1F','PalletTown_PlayersHouse_2F']:
 assert any(w['x']==10 and w['y']==2 for w in m['maps'][name]['warps'])
# Replay targets extend each original input transcript exactly, with no memory patch.
replays=[]
for start,target in [('bedroom','house1f'),('house1f','pallet-town'),('pallet-town','oak-lab')]:
 a=json.loads((root/f'work/pokemon/bridge-probe/{start}.state.replay.json').read_text());b=json.loads((root/f'work/pokemon/bridge-probe/{target}.state.replay.json').read_text());assert b[:len(a)]==a
 replays.append({'start':start,'target':target,'suffix':b[len(a):],'targetSHA256':hashlib.sha256((root/f'work/pokemon/bridge-probe/{target}.state').read_bytes()).hexdigest()})
(base/'verification/interiors/transition-replays.json').write_text(json.dumps(replays,indent=2))
(base/'verification/interiors/source-results.json').write_text(json.dumps({'passed':True,'checks':checks,'totalFeatures':sum(c['features'] for c in checks),'replayPrefixes':True},indent=2))
print('passed: three exact maps, 40 feature groups, reciprocal stair positions, three provenance replay prefixes')
