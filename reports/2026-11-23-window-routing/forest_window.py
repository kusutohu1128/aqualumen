"""Put a lit red window behind the camera in the surveyed four-torch birch stand."""
from selective_room import HERE, ROOT, DIGEST, PACK, TorchCounts, guarded, analyze
from window_room import PACKS

class ForestWindow(TorchCounts):
    def geometry(self,names):
        return dict(super().geometry(names),rearWindow={"x":[207,209],"y":[64,65],"z":352})
    def datapack(self,names):
        assert names==["birch-0","birch-4"]
        files=super().datapack(names)
        insert=[
            "fill 207 64 352 209 65 352 air",
            "fill 207 64 352 207 65 352 red_stained_glass_pane[east=true]",
            "fill 208 64 352 208 65 352 red_stained_glass_pane[east=true,west=true]",
            "fill 209 64 352 209 65 352 red_stained_glass_pane[west=true]"]
        # Warm the original world before placing the window and torch quartet.
        # The p function runs 80 ticks after teleport, with the chunks loaded.
        key="data/animal/function/p1.mcfunction"
        files[key]+="\n".join(insert)+"\n"
        for phase,tag in (("v","READY"),("e","STILL")):
            k=f"data/animal/function/{phase}1.mcfunction"
            marker=f"say AQLAVA_{tag}_birch-4_END"
            assert files[k].count(marker)==1
            tag="execute if score #ok aq_room matches 1 run "
            assert tag+marker in files[k]
            files[k]=files[k].replace(tag+marker,"execute unless block 208 65 352 red_stained_glass_pane[east=true,west=true] run scoreboard players set #ok aq_room 0\n"+tag+marker)
        return files

def run(role):
    name,sha=PACKS["control"]
    p=ROOT/"dist"/("Aqualumen-"+name+".zip") if role=="control" else PACK
    assert guarded.sha(p)==(sha if role=="control" else DIGEST)
    label="back-window-"+role+"-warm"
    assert not (HERE/label).exists()
    fixed=dict(backend="vgl",size="2560x1440",settle="1",stages="birch-0,birch-4",glcache=str(guarded.BUILD/"driver-cache"),
               **{"period-ticks":"650","shot-gap":".15","compiler-mod":str(ROOT/"dist/aqualumen-lighting-compiler-0.3.0.jar")})
    try:guarded.launch(p,label,"off",fixed,HERE,ForestWindow)
    except SystemExit as exc:
        if exc.code:raise
    analyze(HERE/label,p,False,min_frames=50)
if __name__=="__main__":
    import sys
    assert sys.argv[1] in ("control","selective")
    run(sys.argv[1])
