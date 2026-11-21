"""Independent bounded first-full-cube oracle on immutable saved TEST terrain.

Air/water traverse; any unknown/cutout/noncube returns unsupported immediately.
No runtime requests, GPU calls, live saves, terrain writes or fitted shader paths.
"""
import importlib.util
import math
import hashlib
import json
from pathlib import Path
from water_coast_world_pack import ROOT

spec=importlib.util.spec_from_file_location('bounded_anvil_reader',ROOT/'tools/audit-fixture-air.py')
anvil=importlib.util.module_from_spec(spec);spec.loader.exec_module(anvil)
PASS={'minecraft:air','minecraft:cave_air','minecraft:void_air','minecraft:water'}
# Exact declared full-cube subset only. Anything not listed is unsupported.
SOLID={'minecraft:sand','minecraft:red_sand','minecraft:gravel','minecraft:stone',
       'minecraft:dirt','minecraft:grass_block','minecraft:clay','minecraft:sandstone',
       'minecraft:granite','minecraft:andesite','minecraft:diorite','minecraft:deepslate',
       'minecraft:bedrock','minecraft:coal_ore','minecraft:iron_ore','minecraft:copper_ore'}


class SavedCoast:
    def __init__(self,directory,receipt):
        directory=Path(directory)
        if receipt['worldUUID']!=anvil.UUID or receipt['seed']!=308060 or not receipt['closedJava']:
            raise ValueError('Saved TEST scope does not qualify')
        marker=dict(line.split('=',1) for line in (directory/'aqualumen-world.properties').read_text().splitlines())
        anvil.validate_marker('AqualumenNaturalV2',marker)
        path=directory/'r.-1.0.mca'
        if path.is_symlink() or not 8192<=path.stat().st_size<=anvil.LIMIT:
            raise ValueError('Snapshot path or size invalid')
        self.data=path.read_bytes();self.path=path
        if hashlib.sha256(self.data).hexdigest()!=receipt['regionSHA256']:
            raise ValueError('Saved region hash mismatch')
        self.chunks={};self.chunk_evidence={}
    def block(self,cell):
        x,y,z=cell
        if not -64<=y<=319 or (x//512,z//512)!=(-1,0):
            raise ValueError('Ray exits explicitly saved TEST region/build height')
        key=x//16,z//16
        if key not in self.chunks:
            chunk,evidence=anvil.decode_chunk(self.data,self.path,*key)
            if chunk.get('Status')!='minecraft:full':raise ValueError('Saved chunk not full')
            self.chunks[key]=chunk;self.chunk_evidence[key]=evidence
        return anvil.block_state(self.chunks[key],x,y,z)


def first_cube(origin,direction,block,max_travel=48):
    if len(origin)!=3 or len(direction)!=3 or not all(math.isfinite(v) for v in origin+direction):
        raise ValueError('Invalid finite world ray')
    norm=math.sqrt(sum(v*v for v in direction))
    if abs(norm-1)>1e-4:raise ValueError('World transmitted ray is not unit length')
    ray=[v/norm for v in direction]
    if not 0<max_travel<=48:raise ValueError('Ray exceeds original bounded trace range')
    cell=[math.floor(v) for v in origin]
    step=[1 if r>0 else -1 if r<0 else 0 for r in ray]
    delta=[abs(1/r) if r else math.inf for r in ray]
    crossing=[((cell[i]+1 if step[i]>0 else cell[i])-origin[i])/ray[i] if ray[i] else math.inf for i in range(3)]
    t=0.;water_cells=0;visited=[];normal=None
    for _ in range(256):
        state=block(tuple(cell));name=state['Name'];visited.append(dict(cell=list(cell),state=state,entry=t))
        if name in SOLID:
            return dict(status='first_supported_full_cube',cell=list(cell),state=state,travelMetres=t,
                point=[o+r*t for o,r in zip(origin,ray)],normal=normal,
                enteredFluidCells=water_cells,visited=visited,scope='first opaque within declared full-cube subset only')
        if name not in PASS:
            return dict(status='unsupported_geometry',cell=list(cell),state=state,travelMetres=t,
                enteredFluidCells=water_cells,visited=visited)
        if name=='minecraft:water':water_cells+=1
        next_t=min(crossing)
        if next_t>max_travel:return dict(status='no_supported_hit_within_range',visited=visited,enteredFluidCells=water_cells)
        axes=[i for i,c in enumerate(crossing) if abs(c-next_t)<=1e-10]
        if len(axes)!=1:
            # Edge/corner ownership is not silently assigned. Adjacent cutouts
            # or solids may touch the ray; leave the exact boundary unsupported.
            return dict(status='unsupported_edge_tie',travelMetres=next_t,visited=visited,enteredFluidCells=water_cells)
        axis=axes[0];cell[axis]+=step[axis];crossing[axis]+=delta[axis];t=next_t
        normal=[0,0,0];normal[axis]=-step[axis]
    raise ValueError('Ray exceeds traversal bound')
