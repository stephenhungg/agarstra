from pathlib import Path
import json,hashlib
ROOT=Path('/Users/stephenhung/Documents/GitHub/agarstra'); source=json.loads((ROOT/'outputs/pokemon-remake/source/source-maps.json').read_text())
features={
'PalletTown_PlayersHouse_1F':[
 ('sink','kitchen-sink',[1,1,2,2]),('cupboard','kitchen-cupboard',[3,1,4,2]),('tv','television',[6,1,6,2]),('window','north-window',[7,0,8,1]),('stairsUp','stairs-up',[10,1,12,3]),('rug','dining-rug',[4,3,9,6]),('table','dining-table',[6,4,7,5]),('chair','chair-nw',[5,4,5,4]),('chair','chair-sw',[5,5,5,5]),('chair','chair-ne',[8,4,8,4]),('chair','chair-se',[8,5,8,5]),('plant','plant-west',[1,6,1,7]),('plant','plant-east',[12,6,12,7])],
'PalletTown_PlayersHouse_2F':[
 ('desk','pc-desk',[1,1,2,2]),('pc','players-pc',[1,0,1,1]),('chair','desk-chair',[1,2,1,2]),('bookshelf','bookshelf',[4,0,5,2]),('stairsDown','stairs-down',[8,1,10,3]),('bed','bed',[1,4,3,6]),('rug','bedroom-rug',[4,4,8,7]),('tv','television',[6,3,6,4]),('console','game-console',[6,5,6,6]),('poster','notice',[11,0,11,1])],
'PalletTown_ProfessorOaksLab':[
 ('machine','north-machine',[0,0,0,2]),('desk','computer-bench',[1,1,5,2]),('pc','lab-computer',[2,0,3,1]),('poster','notice-west',[6,0,6,1]),('poster','notice-east',[7,0,7,1]),('window','north-window',[8,0,8,1]),('bookshelf','north-shelf-a',[9,0,10,2]),('bookshelf','north-shelf-b',[11,0,12,2]),('bookshelf','west-partition-a',[0,7,2,9]),('bookshelf','west-partition-b',[3,7,4,9]),('bookshelf','east-partition-a',[8,7,10,9]),('bookshelf','east-partition-b',[11,7,12,9]),('healer','healing-machine',[1,3,2,5]),('table','starter-table',[8,4,10,5]),('rack','brochure-rack',[0,3,0,4]),('plant','plant-west',[0,11,0,12]),('plant','plant-east',[12,11,12,12])]
}
out={'sourceCommit':source['commit'],'romSHA1':'41cb23d8dccc8ebd7c649cd8fbb58eeace6e2fdc','status':'candidate-3d-interiors-not-photoreal-approved','coordinateConvention':'+Y up; x=source x, z=source y; tile centers are integer coordinates','interpretation':'Layout IDs, raw metatiles, collisions and warp coordinates are exact source. Furniture names/vertical profiles are visual interpretations of assembled source metatile imagery, except the PC named in source constants.','maps':{}}
for name,items in features.items():
 s=source['maps'][name];w=s['layout']['width'];f=[]
 for kind,id,b in items:
  cells=[{'x':x,'y':y,'metatileId':s['metatileIds'][y*w+x],'collision':s['collision'][y*w+x]}for y in range(b[1],b[3]+1)for x in range(b[0],b[2]+1)]
  f.append({'id':id,'kind':kind,'bounds':b,'sourceCells':cells,'sourceLabel':'METATILE_GenericBuilding1_PlayersPCOff' if name.endswith('2F') and kind=='pc' else None})
 out['maps'][name]={'width':w,'height':s['layout']['height'],'tilesets':[s['layout']['primary_tileset'],s['layout']['secondary_tileset']],'mapDataSHA256':s['mapDataSHA256'],'metatileIds':s['metatileIds'],'collision':s['collision'],'warps':s['events']['warp_events'],'features':f,'sourcePaths':s['sourcePaths']}
(ROOT/'outputs/pokemon-remake/source/interiors.json').write_text(json.dumps(out,indent=2))
print('3 maps,',sum(len(m['features'])for m in out['maps'].values()),'source-linked furniture features')
