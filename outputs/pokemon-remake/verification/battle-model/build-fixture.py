from pathlib import Path
import struct,json
p=Path(__file__).parent
# Deliberately non-character fixture: one triangle, explicit one-second translation idle.
binary=struct.pack('<9f',-.5,0,0,.5,0,0,0,1,0)+struct.pack('<3f',0,.5,1)+struct.pack('<9f',0,0,0,0,.2,0,0,0,0)
g={'asset':{'version':'2.0'},'scene':0,'scenes':[{'nodes':[0]}],'nodes':[{'name':'FixtureAncestor','translation':[0,.1,0],'children':[1]},{'name':'FixtureTriangle','mesh':0}],'meshes':[{'primitives':[{'attributes':{'POSITION':0}}]}],'buffers':[{'byteLength':len(binary)}],'bufferViews':[{'buffer':0,'byteOffset':0,'byteLength':36},{'buffer':0,'byteOffset':36,'byteLength':12},{'buffer':0,'byteOffset':48,'byteLength':36}],'accessors':[{'bufferView':0,'componentType':5126,'count':3,'type':'VEC3','min':[-.5,0,0],'max':[.5,1,0]},{'bufferView':1,'componentType':5126,'count':3,'type':'SCALAR','min':[0],'max':[1]},{'bufferView':2,'componentType':5126,'count':3,'type':'VEC3'}],'animations':[{'name':'idle','samplers':[{'input':1,'output':2}],'channels':[{'sampler':0,'target':{'node':1,'path':'translation'}}]}]}
j=json.dumps(g,separators=(',',':')).encode();j+=b' '*((-len(j))%4);binary+=b'\0'*((-len(binary))%4);data=struct.pack('<III',0x46546c67,2,28+len(j)+len(binary))+struct.pack('<II',len(j),0x4e4f534a)+j+struct.pack('<II',len(binary),0x004e4942)+binary;(p/'idle-fixture.glb').write_bytes(data)
