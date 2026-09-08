from pathlib import Path
import re,json,hashlib,subprocess,ast,operator
base=Path(__file__).resolve().parent;src=base/'smb3';rom=(base.parent/'rom-experiment/smb3.nes').read_bytes();assembled=(src/'smb3.nes').read_bytes();assert rom==assembled
symbols={m[1]:int(m[2],16) for m in re.finditer(r'^(\w+)\s*=\s*\$([0-9A-Fa-f]+)',(src/'smb3.fns').read_text(),re.M)}
records={};bankOrigins={}
def walk(path,bank=None,origin=None):
 for lineNum,line in enumerate(path.read_text().splitlines(),1):
  code=line.split(';')[0]
  m=re.match(r'\s*\.bank\s+(\d+)',code)
  if m:bank=int(m[1]);origin=None
  m=re.match(r'\s*\.org\s+\$([0-9a-fA-F]+)',code)
  if m and bank is not None and origin is None:origin=int(m[1],16);bankOrigins[bank]=origin
  m=re.search(r'\.include\s+"([^"]+)"',code)
  if m:
   p=src/m[1]
   if not p.exists():p=p.with_suffix('.asm')
   if p.exists():walk(p,bank,origin)
  m=re.match(r'^(\w+)(?::|\s+\.byte)',code)
  if m and m[1] in symbols and bank is not None and bank<32:
   cpu=symbols[m[1]];offset=16+bank*8192+cpu-origin
   if 16+bank*8192<=offset<16+(bank+1)*8192:records[m[1]]={'name':m[1],'bank':bank,'cpuAddress':cpu,'romOffset':offset,'source':str(path.relative_to(src)),'line':lineNum}
walk(src/'smb3.asm')
def block(name,n):
 r=records[name];return {**r,'length':n,'bytes':list(rom[r['romOffset']:r['romOffset']+n])}
main=(src/'smb3.asm').read_text(); constants={}
for m in re.finditer(r'^(\w+)\s*=\s*\$([0-9A-Fa-f]+)\s*(?:;\s*(.*))?$',main,re.M):constants[m[1]]={'value':int(m[2],16),'description':m[3] or ''}
# Evaluate assembler constants using a deliberately limited expression evaluator.
ops={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.Div:operator.floordiv,ast.BitOr:operator.or_,ast.BitAnd:operator.and_,ast.LShift:operator.lshift,ast.RShift:operator.rshift}
def val(node):
 if isinstance(node,ast.Constant) and isinstance(node.value,int):return node.value
 if isinstance(node,ast.Name):return constants[node.id]['value']
 if isinstance(node,ast.BinOp) and type(node.op) in ops:return ops[type(node.op)](val(node.left),val(node.right))
 if isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.USub,ast.Invert)):return -val(node.operand) if isinstance(node.op,ast.USub) else ~val(node.operand)
 raise ValueError('Unsupported')
for repeat in range(5):
 for ln in main.splitlines():
  m=re.match(r'^(\w+)\s*=\s*([^;]+)(?:;\s*(.*))?$',ln)
  if not m:continue
  expr=re.sub(r'\$([0-9A-Fa-f]+)',r'0x\1',m[2]);expr=re.sub(r'%([01]+)',r'0b\1',expr)
  try:constants[m[1]]={'value':val(ast.parse(expr.strip(),mode='eval').body),'description':m[3] or ''}
  except (SyntaxError,ValueError,KeyError,TypeError):pass
metatiles=[]
for name in records:
 if not name.startswith('Tile_Layout_TS'):continue
 b=block(name,1024);b['tilesets']=[int(x) for x in re.findall(r'TS(\d+)',name)];b['entries']=[]
 for i in range(256):
  names=[{'name':k,'description':v['description']} for k,v in constants.items() if v['value']==i and any(k.startswith(f'TILE{ts}_') for ts in b['tilesets'])]
  b['entries'].append({'id':i,'paletteIndex':i>>6,'patternsUL_LL_UR_LR':[b['bytes'][i+q*256] for q in range(4)],'sourceNames':names})
 metatiles.append(b)
player={'frameTable':block('SPPF_Table',81*6),'offsetTable':block('SPPF_Offsets',81),'pageOffsets':block('Player_FramePageOff',81),'suitRootPages':block('Player_PUpRootPage',7),'suits':['Small','Big','Fire','Leaf','Frog','Tanooki','Hammer'],'frames':[],'notes':['81 shared templates, not 81 valid animations for each suit. Suit/frame validity is decided by game action tables.','Each template has six 8x16 sprites: upper row x0,8,16 y0, then lower row x0,8,16 y16. $F1 means hidden.','If lower first two sprite patterns match, game mirrors right column. Normal facing flip additionally swaps columns and moves third column left.','For odd pattern < $40, both 8x8 halves resolve to CHR indices (suitRootPage+framePageOffset)*64+(pattern&0xFE) and +1. Patterns >=$40 require other live MMC3 sprite banks; do not assume player bank.']}
for i in range(81):
 r=records.get(f'PF{i:02X}');off=player['frameTable']['romOffset']+i*6;assert r and r['romOffset']==off
 pats=list(rom[off:off+6]);player['frames'].append({'id':i,'label':f'PF{i:02X}','romOffset':off,'patterns':pats,'chrPageOffset':player['pageOffsets']['bytes'][i],'sprites':[{'x':(j%3)*8,'y':(j//3)*16,'pattern':p,'hidden':p==241} for j,p in enumerate(pats)]})
objects=[]
for group in range(5):
 prefix=f'ObjectGroup{group:02X}_';entry={'group':group,'firstObjectId':group*36,'tables':{},'objects':[]}
 for suffix in ['Attributes','Attributes2','Attributes3','PatTableSel','KillAction','PatternStarts']:
  name=prefix+suffix
  if name in records:entry['tables'][suffix]=block(name,36)
 patbase=records[prefix+'PatternSets']['romOffset'];entry['patternSetsBase']=records[prefix+'PatternSets']
 for i in range(36):
  ident=group*36+i;offset=entry['tables']['PatternStarts']['bytes'][i];start=patbase+offset
  label=f'ObjP{ident:02X}';names=[k for k,v in constants.items() if k.startswith('OBJ_') and v['value']==ident]
  # Explicit alias labels may differ from the default table-selected start. Record both.
  candidates=[v['romOffset'] for k,v in records.items() if v['bank']==group+1 and v['romOffset']>start]
  end=min(candidates) if candidates else start
  entry['objects'].append({'id':ident,'names':names,'patternStartOffset':offset,'romOffset':start,'bytesToNextSymbol':list(rom[start:end]),'sourceLabel':records.get(label),'attributes':[entry['tables'][k]['bytes'][i] for k in ['Attributes','Attributes2','Attributes3']],'chrBankSelector':entry['tables']['PatTableSel']['bytes'][i],'note':'Default compositor descriptor only. Giant and object-specific rendering routines can replace or augment this data.'})
 objects.append(entry)
paletteSets=[block(name,192) for name in records if name.startswith('PalSet_')]
bgBankTables=[block('Level_BG_Pages1',23),block('Level_BG_Pages2',23)]
# All byte-data labels expose the rest of the ROM-specific composite catalog without guessing semantics.
byteLabels=[]
for r in records.values():
 lines=(src/r['source']).read_text().splitlines();tail=lines[r['line']-1:];count=0
 for j,line in enumerate(tail):
  code=line.split(';')[0]
  if j>0 and count and re.match(r'^\w+',code):break
  if j==0:code=re.sub(r'^\w+:?','',code)
  if not code.strip():continue
  if re.match(r'^\w+:\s*$',code):continue
  m=re.search(r'\.byte\s+(.+)',code)
  if not m:break
  count+=len(m[1].split(','))
 if count:byteLabels.append({**r,'length':count,'bytes':list(rom[r['romOffset']:r['romOffset']+count])})
levels=[]
for r in records.values():
 if r['source'].startswith('PRG/levels/') and '/'+Path(r['source']).stem not in '':
  # Labels belong to include parent; level labels found below from include directives.
  pass
for path in (src/'PRG/levels').glob('*.asm'):
 for line in path.read_text().splitlines():
  m=re.match(r'(\w+):\s*\.include\s+"([^"]+)"',line)
  if not m or m[1] not in records:continue
  r=records[m[1]];p=src/m[2]
  if not p.exists():p=p.with_suffix('.asm')
  if not p.exists():continue
  count=0
  for ln in p.read_text().splitlines():
   ln=ln.split(';')[0]
   x=re.search(r'\.(byte|word)\s+(.+)',ln)
   if x:count+=len(x[2].split(','))*(2 if x[1]=='word' else 1)
  levels.append({**r,'layoutSource':str(p.relative_to(src)),'length':count,'headerBytes':list(rom[r['romOffset']:r['romOffset']+9]),'bytes':list(rom[r['romOffset']:r['romOffset']+count])})
manifest={'romSha256':hashlib.sha256(rom).hexdigest(),'rebuiltIdentical':True,'romBytes':len(rom),'prgBytes':rom[4]*16384,'chrBytes':rom[5]*8192,'sourceCommit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=src,text=True).strip(),'assemblerCommit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=base/'nesasm',text=True).strip(),'metatileTables':metatiles,'player':player,'objectGroups':objects,'levelLayouts':levels,'paletteSets':paletteSets,'backgroundBankTables':bgBankTables,'objectConstants':[{"name":k,**v} for k,v in constants.items() if k.startswith('OBJ_')],'counts':{'metatileTables':len(metatiles),'metatileDefinitions':len(metatiles)*256,'sharedPlayerFrames':81,'objectIds':180,'levelLayouts':len(levels),'byteDataLabels':len(byteLabels),'sourceSymbols':len(records)},'limitations':['Raw CHR inventory is exhaustive; semantic asset identity is not encoded per tile.','Object sprite composition can be code-driven and state/bank dependent, so default object descriptors are not every animation frame.','Level object generator byte streams require executing original loader or porting all tileset generator routines; the ROM already expands full active level into SRAM.']}
(base/'binary-asset-manifest.json').write_text(json.dumps(manifest,indent=2));(base/'all-byte-data-labels.json').write_text(json.dumps(byteLabels,indent=2));(base/'symbol-bank-map.json').write_text(json.dumps(records,indent=2));print(json.dumps(manifest['counts']));print('W101L',records['W101L']);print('SPPF_Table',records['SPPF_Table'])
