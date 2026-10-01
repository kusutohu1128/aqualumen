"""Create a new, isolated water test world using the standard NBT format.

Refuses to modify an existing world. No downloaded/supplied saves are used.
"""
import gzip
import struct
import sys
from pathlib import Path

def string(value):
    raw=value.encode('utf-8')
    return struct.pack('>H',len(raw))+raw

def payload(kind,value):
    if kind==1: return struct.pack('>b',value)
    if kind==3: return struct.pack('>i',value)
    if kind==4: return struct.pack('>q',value)
    if kind==5: return struct.pack('>f',value)
    if kind==6: return struct.pack('>d',value)
    if kind==8: return string(value)
    if kind==9:
        subtype,items=value
        return bytes([subtype])+struct.pack('>i',len(items))+b''.join(payload(subtype,x) for x in items)
    if kind==10:
        return b''.join(bytes([t])+string(k)+payload(t,v) for k,(t,v) in value.items())+b'\0'
    raise ValueError(kind)

S=lambda x:(8,x)
I=lambda x:(3,x)
B=lambda x:(1,int(x))
C=lambda x:(10,x)
L=lambda t,x:(9,(t,x))
layer=lambda height,block:{'height':I(height),'block':S('minecraft:'+block)}
flat={'type':S('minecraft:flat'),'settings':C({
    'biome':S('minecraft:deep_ocean'),'lakes':B(False),'features':B(False),
    'structure_overrides':L(8,[]),
    'layers':L(10,[layer(1,'bedrock'),layer(110,'stone'),layer(6,'sand'),layer(10,'water')])})}
noise=lambda setting,source:{'type':S('minecraft:noise'),'settings':S('minecraft:'+setting),'biome_source':C(source)}
dimensions={
 'minecraft:overworld':C({'type':S('minecraft:overworld'),'generator':C(flat)}),
 'minecraft:the_nether':C({'type':S('minecraft:the_nether'),'generator':C(noise('nether',{'type':S('minecraft:multi_noise'),'preset':S('minecraft:nether')}))}),
 'minecraft:the_end':C({'type':S('minecraft:the_end'),'generator':C(noise('end',{'type':S('minecraft:the_end')}))})}
player={
 'Pos':L(6,[0.5,66.0,0.5]),'Motion':L(6,[0.0,0.0,0.0]),'Rotation':L(5,[0.0,12.0]),
 'Dimension':S('minecraft:overworld'),'Health':(5,20.0),'foodLevel':I(20),
 'playerGameType':I(1),'Inventory':L(10,[]),
 'abilities':C({'flying':B(True),'mayfly':B(True),'invulnerable':B(True),'instabuild':B(True),'mayBuild':B(True),'flySpeed':(5,0.05),'walkSpeed':(5,0.1)})}
data={
 'DataVersion':I(3955),'version':I(19133),'DragonFight':C({}),
 'Version':C({'Id':I(3955),'Name':S('1.21.1'),'Snapshot':B(False)}),
 'LevelName':S('Aqualumen Benchmark'),'GameType':I(1),'Difficulty':B(0),
 'hardcore':B(False),'allowCommands':B(True),'initialized':B(True),
 'SpawnX':I(0),'SpawnY':I(66),'SpawnZ':I(0),'Time':(4,6000),'DayTime':(4,6000),
 'raining':B(False),'thundering':B(False),'rainTime':I(999999),'thunderTime':I(999999),
 'GameRules':C({k:S(v) for k,v in {'doDaylightCycle':'false','doWeatherCycle':'false','doMobSpawning':'false','randomTickSpeed':'0'}.items()}),
 'WorldGenSettings':C({'seed':(4,308060),'generate_features':B(False),'bonus_chest':B(False),'dimensions':C(dimensions)}),
 'Player':C(player)}
target=Path(sys.argv[1])
if not target.name.startswith('AqualumenBenchmark') or 'Aqualumen Lab' not in target.parts:
    raise SystemExit('Refusing target outside the isolated instance')
target.mkdir(parents=True,exist_ok=False)
with gzip.open(target/'level.dat','wb') as file:
    file.write(b'\x0a\x00\x00'+payload(10,{'Data':C(data)}))
print('Created',target)
