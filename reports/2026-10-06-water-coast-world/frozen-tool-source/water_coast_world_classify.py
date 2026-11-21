"""Independent saved full-cube camera occlusion; no fitted hit tolerance."""
import json
from water_coast_world_pack import ROOT,OUT
from water_coast_world_geometry import SavedCoast
from water_coast_world_lifecycle import core


def classify(point):
    first=point['firstIntersection'];camera=point.get('independentCameraRayToPhysicalFirstPoint')
    if first['status']!='first_supported_full_cube' or not camera or camera['status']!='first_supported_full_cube':
        return 'unsupported'
    if camera['cell']==first['cell']:return 'same_first_cube_visible_to_camera_ray'
    assert camera['travelMetres']<point['cameraPointTravel']
    return 'different_full_cube_occludes_physical_receiver'


def main():
    geometry=json.loads((OUT/'geometry-audit.json').read_text())
    receipt=json.loads((OUT/'saved-test-coast-terrain.json').read_text())
    saved=SavedCoast(OUT/'saved-test-coast-terrain',receipt)
    prior=ROOT/'reports/2026-10-06-water-coast-stop'
    older=SavedCoast(prior/'saved-test-coast-terrain',json.loads((prior/'saved-test-coast-terrain.json').read_text()))
    records=[]
    for p in geometry['points']:
        value=classify(p)
        camera=p['independentCameraRayToPhysicalFirstPoint']
        stable=all(saved.block(tuple(s['cell']))==older.block(tuple(s['cell']))==s['state'] for s in camera['visited'])
        assert stable and p['allVisitedBlockStatesMatchEarlierSnapshot']
        records.append(dict(pair=p['pair'],priorRole=p['priorRole'],classification=value,
            receiverCell=p['firstIntersection']['cell'],cameraFirstCell=camera['cell'],
            targetDistance=p['cameraPointTravel'],cameraFirstDistance=camera['travelMetres'],
            blockerDistanceBeforeTarget=p['cameraPointTravel']-camera['travelMetres'],
            refractedAndCameraRayCellsUnchangedAcrossSavedSnapshots=True,
            physicalWaterCellsTraversed=p['firstIntersection']['enteredFluidCells'],
            lastShaderSourcePointDistanceFromPhysicalFirstPoint=p['distanceLastSampleToFirstPoint']))
    assert len(records)==16
    assert all(r['classification']==('different_full_cube_occludes_physical_receiver' if r['priorRole']=='miss'
        else 'same_first_cube_visible_to_camera_ray') for r in records)
    core.save('camera-occlusion-audit.json',dict(schema='aqualumen-coast-world-camera-occlusion-v1',points=records,
        eightDarkPointsOccludedByNearerSand=True,eightAdjacentHitPointsCameraVisible=True,
        noncubeOrCutoutEncounteredOnTheseRays=False,usesShaderSearchToChooseFirstObject=False,
        physicalPointCenterOcclusionQualifiedWithinDeclaredFullCubeScope=True,
        exactRenderedPixelFootprintProven=False,geometryAndRawSameFrameProven=False,
        universalRootCauseProven=False,productionFixImplemented=False,fullGoalAchieved=False,
        nextAction='Recover geometrically and optically coherent off-screen/occluded receiver information; do not weaken screen-space guards'))
    print('Independent camera occlusion:all8 dark physical receivers blocked;all8 adjacent positives visible')


if __name__=='__main__':main()
