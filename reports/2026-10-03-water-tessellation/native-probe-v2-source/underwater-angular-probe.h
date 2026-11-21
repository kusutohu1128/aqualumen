#ifndef AQUALUMEN_UNDERWATER_ANGULAR_PROBE_H
#define AQUALUMEN_UNDERWATER_ANGULAR_PROBE_H

// ONE opt-in angular-map tracer bullet. Original VS/FS main, public flat/foam
// options, real directional LUT and STORE-only observation. No environment,
// refraction, wave or reflection function is replaced. Preparation is CPU-only;
// the caller alone owns the exclusive NVIDIA GL slot when invoking this.
#include "water-radiance-probe.h"

namespace aqualumenUnderwaterAngularDetail {
using V3=std::array<double,3>;
using M4=std::array<float,16>;
using D4=std::array<double,16>;
using aqualumenWaterOpticalDepthDetail::dot;
using aqualumenWaterOpticalDepthDetail::add;
using aqualumenWaterOpticalDepthDetail::normalized;
using aqualumenWaterOpticalDepthDetail::firstHit;
using aqualumenWaterOpticalDepthDetail::Box;
using aqualumenWaterRadianceDetail::arithmeticBound;
using aqualumenWaterRadianceDetail::storageRoundoff;
using aqualumenWaterRadianceDetail::textFile;
using aqualumenWaterRadianceDetail::rawFile;
constexpr double pi=3.14159265358979323846,index=1.333;
constexpr int skyWidth=1024,skyHeight=512;
inline void qualify(bool value,const std::string& message) {
    if(!value) throw std::runtime_error("INCONCLUSIVE underwater-angular: "+message);
}
inline D4 widen(const M4& a) {D4 b={};for(int i=0;i<16;++i)b[i]=a[i];return b;}
inline D4 inverse(const M4& matrix) {
    double a[4][8]={};
    for(int r=0;r<4;++r)for(int c=0;c<4;++c){a[r][c]=matrix[c*4+r];a[r][4+c]=double(r==c);}
    for(int c=0;c<4;++c) {
        int pivot=c;for(int r=c+1;r<4;++r)if(std::abs(a[r][c])>std::abs(a[pivot][c]))pivot=r;
        qualify(std::abs(a[pivot][c])>1e-15,"singular supplied matrix");
        for(int j=0;j<8;++j)std::swap(a[c][j],a[pivot][j]);
        const double scale=a[c][c];for(double& value:a[c])value/=scale;
        for(int r=0;r<4;++r)if(r!=c){const double q=a[r][c];for(int j=0;j<8;++j)a[r][j]-=q*a[c][j];}
    }
    D4 result={};for(int r=0;r<4;++r)for(int c=0;c<4;++c)result[c*4+r]=a[r][4+c];return result;
}
inline std::array<double,4> multiply(const D4& m,const std::array<double,4>& v) {
    std::array<double,4> result={};for(int r=0;r<4;++r)for(int c=0;c<4;++c)result[r]+=m[c*4+r]*v[c];return result;
}
inline V3 point(const D4& m,const V3& p) {
    const auto q=multiply(m,{p[0],p[1],p[2],1});qualify(std::isfinite(q[3])&&std::abs(q[3])>1e-14,"invalid affine point");
    return {q[0]/q[3],q[1]/q[3],q[2]/q[3]};
}
inline V3 vector(const D4& m,const V3& p) {
    const auto q=multiply(m,{p[0],p[1],p[2],0});return {q[0],q[1],q[2]};
}
struct Input {
    int sourceWidth=129,sourceHeight=129,width=129,height=129;
    bool supplied=false;
    M4 projection={},projectionInverse={},view={},viewInverse={};
    D4 inverseProjection={},inverseView={};V3 eye={};
};
// Strict <=16KiB packet; queried inverse matrices are retained, not substituted.
// aqualumen-underwater-matrices-v1
// source_size W H
// gbufferProjection <16 column-major binary32 round-trip decimals>
// gbufferProjectionInverse <16> / gbufferModelView <16> / ...Inverse <16>
// Capture identity/time/program metadata stays in the lifecycle owner's JSON.
inline Input input(const std::filesystem::path& packet={}) {
    Input result;
    if(packet.empty()) {
        const float f=float(1/std::tan(50*pi/180)),n=0.1f,z=128;
        result.projection={f,0,0,0,0,f,0,0,0,0,-(z+n)/(z-n),-1,0,0,-2*z*n/(z-n),0};
        result.view={1,0,0,0,0,0,-1,0,0,1,0,0,0,0,0,1};
        const auto p=inverse(result.projection),v=inverse(result.view);
        for(int i=0;i<16;++i){result.projectionInverse[i]=float(p[i]);result.viewInverse[i]=float(v[i]);}
    } else {
        qualify(std::filesystem::is_regular_file(packet)&&std::filesystem::file_size(packet)<=16384,"projection packet absent/oversized");
        std::ifstream stream(packet);std::string label;
        qualify(bool(stream>>label)&&label=="aqualumen-underwater-matrices-v1","wrong matrix-packet version");
        qualify(bool(stream>>label>>result.sourceWidth>>result.sourceHeight)&&label=="source_size"
            &&result.sourceWidth>=32&&result.sourceWidth<=2560&&result.sourceHeight>=32&&result.sourceHeight<=1440,"invalid source dimensions");
        for(auto item:std::array<std::pair<const char*,M4*>,4>{{{"gbufferProjection",&result.projection},
            {"gbufferProjectionInverse",&result.projectionInverse},{"gbufferModelView",&result.view},{"gbufferModelViewInverse",&result.viewInverse}}}) {
            qualify(bool(stream>>label)&&label==item.first,"matrix packet labels/order differ");
            for(float& value:*item.second)qualify(bool(stream>>value)&&std::isfinite(value),"nonfinite/truncated matrix packet");
        }
        qualify(!(stream>>label),"trailing matrix packet data");result.supplied=true;
        result.height=std::max(33,int(std::lround(129.0*result.sourceHeight/result.sourceWidth)));
        qualify(result.height<=257,"source aspect exceeds bounded resampled grid");
    }
    result.inverseProjection=inverse(result.projection);result.inverseView=inverse(result.view);
    for(auto item:std::array<std::pair<D4,M4>,2>{{{result.inverseProjection,result.projectionInverse},{result.inverseView,result.viewInverse}}})
        for(int i=0;i<16;++i)qualify(std::abs(item.first[i]-item.second[i])<=arithmeticBound(1+std::abs(item.first[i]),256),"queried inverse inconsistent with independently inverted matrix");
    qualify(result.view[3]==0&&result.view[7]==0&&result.view[11]==0&&result.view[15]==1,"model-view is not affine");
    for(int a=0;a<3;++a)for(int b=0;b<3;++b) {
        double product=0;for(int r=0;r<3;++r)product+=double(result.view[a*4+r])*result.view[b*4+r];
        qualify(std::abs(product-double(a==b))<=arithmeticBound(2,256),"model-view is not a rigid camera basis");
    }
    qualify(result.projection[3]==0&&result.projection[7]==0&&result.projection[15]==0&&result.projection[11]<0,"not a perspective projection");
    result.eye=point(result.inverseView,{0,0,0});return result;
}
inline V3 ray(const Input& in,double u,double v) {
    const auto q=multiply(in.inverseProjection,{2*u-1,2*v-1,1,1});
    qualify(q[3]>0,"invalid far unprojection");
    return normalized(vector(in.inverseView,{q[0]/q[3],q[1]/q[3],q[2]/q[3]}));
}
inline std::array<double,3> project(const Input& in,const V3& world) {
    const auto view=point(widen(in.view),world);const auto p=multiply(widen(in.projection),{view[0],view[1],view[2],1});
    qualify(p[3]>0,"receiver lies behind eye");return {p[0]/p[3]*.5+.5,p[1]/p[3]*.5+.5,p[2]/p[3]*.5+.5};
}
struct Boundary {bool tir=false;V3 transmitted={};double fresnel=1;};
inline Boundary boundary(const V3& incoming,double ratio=index) {
    Boundary value;const double ci=incoming[1],squared=ratio*ratio*(1-ci*ci);
    qualify(ci>0&&ci<=1.000000001,"ray does not meet the upper plane from below");
    if(squared>=1){value.tir=true;return value;}
    const double ct=std::sqrt(std::max(0.0,1-squared));value.transmitted={ratio*incoming[0],ct,ratio*incoming[2]};
    const double rs=(ratio*ci-ct)/(ratio*ci+ct),rp=(ci-ratio*ct)/(ci+ratio*ct);
    value.fresnel=.5*(rs*rs+rp*rp);return value;
}
inline bool masked(const V3& direction,double padding=0) {
    const double s=std::sqrt(.75),limit=std::cos((8*pi/180)+padding);
    for(const V3 q:std::array<V3,5>{{{0,1,0},{s,.5,0},{-s,.5,0},{0,.5,s},{0,.5,-s}}})if(dot(q,direction)>limit)return true;
    return direction[1]<=0;
}
inline V3 marker(const V3& t,bool rotated=false) {
    return rotated?V3{.2+.15*t[2],.2+.15*t[1],.2-.15*t[0]}:V3{.2+.15*t[0],.2+.15*t[1],.2+.15*t[2]};
}
inline std::vector<float> field(bool zero=false,bool rotated=false) {
    std::vector<float> data(skyWidth*skyHeight*4,0);
    for(int y=0;y<skyHeight;++y)for(int x=0;x<skyWidth;++x) {
        const int p=(y*skyWidth+x)*4;data[p+3]=1;if(zero||y==skyHeight-1)continue;
        const double phi=((x+.5)/skyWidth-.5)*2*pi,elevation=(double(y)/(skyHeight-2)-.5)*pi;
        const V3 d={std::cos(elevation)*std::cos(phi),std::sin(elevation),std::cos(elevation)*std::sin(phi)};
        if(masked(d))continue;
        const auto colour=marker(d,rotated);for(int c=0;c<3;++c)data[p+c]=float(colour[c]);
    }
    return data;
}
struct Sample {int x=0,y=0;V3 incident={},surface={},transmitted={};double fresnel=0;bool tir=false;};
struct Capture {std::array<std::vector<float>,4> output;};
// Fixed input preset, selected before any C0/SSR response: native129 CPU
// qualification puts the selected quad's hits in the .4 -> .668 m segment.
// The original .3 m preset remains archived as an INCONCLUSIVE control.
constexpr double reflectionWallTravel=.55;
struct ReflectionControl {std::vector<Box> boxes;int pixel=-1;size_t angleCandidates=0,qualifiedCandidates=0;};
inline ReflectionControl reflectionControl(const Input& in) {
    ReflectionControl control;const double depth=3.25;
    // Fixed input-only selection, callable without a GL context. All four
    // target rays and all four camera-source texel corners must qualify.
    for(int y=1;y<in.height-1;++y)for(int x=1;x<in.width-1;++x) {
        const V3 d=ray(in,(x+.5)/in.width,(y+.5)/in.height);if(d[1]<=0)continue;
        const double theta=std::acos(d[1]);if(theta<49.5*pi/180||theta>51*pi/180)continue;
        ++control.angleCandidates;
        const V3 p=add(in.eye,d,depth/d[1]),r={d[0],-d[1],d[2]},origin=add(p,{0,-1,0},.06),receiver=add(origin,r,reflectionWallTravel);
        const int axis=std::abs(r[0])>std::abs(r[2])?0:2,other=2-axis;const double sign=r[axis]>0?1:-1;
        Box box;box.id=1;box.lo={in.eye[0]-32,in.eye[1]-8,in.eye[2]-32};box.hi={in.eye[0]+32,in.eye[1]+depth-.001,in.eye[2]+32};
        box.lo[axis]=receiver[axis]-(sign<0?.5:0);box.hi[axis]=receiver[axis]+(sign>0?.5:0);box.lo[other]=receiver[other]-1;box.hi[other]=receiver[other]+1;
        const std::vector<Box> candidate={box};bool valid=true;
        for(int corner=0;corner<4;++corner) {
            const V3 cr=ray(in,double(x+(corner&1))/in.width,double(y+((corner>>1)&1))/in.height);
            if(cr[1]<=0||!boundary(cr).tir){valid=false;break;}
            const V3 cp=add(in.eye,cr,depth/cr[1]),rr={cr[0],-cr[1],cr[2]},co=add(cp,{0,-1,0},.06);
            const auto hit=firstHit(candidate,co,rr),front=firstHit(candidate,in.eye,cr);
            if(!hit.valid||hit.inside||hit.tangent||hit.axis!=axis||(front.valid&&front.travel<=depth/cr[1])){valid=false;break;}
            const auto uv=project(in,hit.point),march=project(in,add(co,rr,.4));
            if(uv[0]<.02||uv[0]>.98||uv[1]<.02||uv[1]>.98||march[0]<.002||march[0]>.998||march[1]<.002||march[1]>.998){valid=false;break;}
            const auto camera=firstHit(candidate,in.eye,normalized(add(hit.point,in.eye,-1)));
            if(!camera.valid||camera.inside||camera.tangent||camera.axis!=axis){valid=false;break;}
            const int sx=int(uv[0]*in.width),sy=int(uv[1]*in.height);
            for(int sourceCorner=0;sourceCorner<4;++sourceCorner){const auto visible=firstHit(candidate,in.eye,ray(in,double(sx+(sourceCorner&1))/in.width,double(sy+((sourceCorner>>1)&1))/in.height));
                if(!visible.valid||visible.inside||visible.tangent||visible.axis!=axis){valid=false;break;}}
            if(!valid)break;
        }
        if(valid){++control.qualifiedCandidates;if(control.pixel<0){control.boxes=candidate;control.pixel=y*in.width+x;}}
    }
    qualify(control.pixel>=0,"no independently visible four-corner TIR reflector for supplied FOV");return control;
}
inline double maxDifference(const std::vector<float>& a,const std::vector<float>& b) {
    qualify(a.size()==b.size(),"capture size differs");double value=0;
    for(size_t i=0;i<a.size();++i)value=std::max(value,std::abs(double(a[i])-b[i]));
    return value;
}
inline double smoothUnit(double x) {x=std::clamp(x,0.0,1.0);return x*x*(3-2*x);}
inline std::vector<Box> frozenNearWall(const Input& in) {
    qualify(!in.supplied&&in.width==129&&in.height==129,"near-wall regression is the frozen native129 fixture only");
    const V3 d=ray(in,24.5/129,11.5/129),p=add(in.eye,d,3.25/d[1]),r={d[0],-d[1],d[2]};
    const V3 receiver=add(add(p,{0,-1,0},.06),r,.3);
    const int axis=std::abs(r[0])>std::abs(r[2])?0:2,other=2-axis;const double sign=r[axis]>0?1:-1;
    Box box;box.id=1;box.lo={in.eye[0]-32,in.eye[1]-8,in.eye[2]-32};box.hi={in.eye[0]+32,in.eye[1]+3.25-.001,in.eye[2]+32};
    box.lo[axis]=receiver[axis]-(sign<0?.5:0);box.hi[axis]=receiver[axis]+(sign>0?.5:0);
    box.lo[other]=receiver[other]-1;box.hi[other]=receiver[other]+1;return {box};
}
struct NearRay {
    V3 origin={},direction={};std::array<double,4> clipOrigin={},clipDirection={};
    double uvError=0,zError=0,norm=0;
};
struct NearCell {
    int ray=0,pixel=0;double begin=0,end=0,zLow=0,zHigh=0;
};
struct NearOracle {
    double corridorLow=.4,corridorHigh=0,pathLow=0,pathHigh=0,edgeMinimum=1,confidenceMinimum=0;
    double sourceMinimum=1,rayNormMinimum=2,rayNormMaximum=0,maximumResidual=0,redLower=0;
    size_t reachableCells=0;std::vector<NearRay> rays;std::vector<NearCell> cells;std::string records;
};
inline std::array<double,2> nearUV(const NearRay& ray,double t) {
    const double w=ray.clipOrigin[3]+ray.clipDirection[3]*t;
    qualify(w>0,"near-wall ray has nonpositive clip W");
    return {.5+(ray.clipOrigin[0]+ray.clipDirection[0]*t)/(2*w),.5+(ray.clipOrigin[1]+ray.clipDirection[1]*t)/(2*w)};
}
inline std::array<double,2> nearStoredZ(const Input& in,float depth) {
    // Standard captured/default perspective only: reconstructed view Z/W must
    // be independent of source UV. Actual depth32F is not rounded a second time.
    qualify(in.projectionInverse[2]==0&&in.projectionInverse[6]==0&&in.projectionInverse[3]==0&&in.projectionInverse[7]==0,
        "near-wall inverse has UV-dependent Z/W");
    const double z=2*double(depth)-1,pz=in.projectionInverse[10]*z+in.projectionInverse[14],pw=in.projectionInverse[11]*z+in.projectionInverse[15];
    const double zError=arithmeticBound(2*std::abs(double(depth))+1,4);
    const double numeratorError=std::abs(in.projectionInverse[10])*zError+arithmeticBound(std::abs(in.projectionInverse[10]*z)+std::abs(in.projectionInverse[14]),12);
    const double denominatorError=std::abs(in.projectionInverse[11])*zError+arithmeticBound(std::abs(in.projectionInverse[11]*z)+std::abs(in.projectionInverse[15]),12);
    qualify(pw>denominatorError,"near-wall depth inverse denominator unresolved");
    const double value=pz/pw,error=(numeratorError+std::abs(value)*denominatorError)/(pw-denominatorError)+arithmeticBound(std::abs(value),4);
    return {value-error,value+error};
}
inline std::vector<NearCell> nearCells(const Input& in,const NearRay& ray,int index,const std::vector<float>& depth) {
    std::vector<double> boundaries={0,.4};
    // Rational projected coordinates are monotone while W>0. Split at BOTH
    // expanded sides of every texel boundary; ties/adjacent cells stay included.
    for(int coordinate=0;coordinate<2;++coordinate) {
        const int size=coordinate==0?in.width:in.height;
        for(int k=0;k<=size;++k)for(double sign:{-1.0,1.0}) {
            const double level=double(k)/size+sign*ray.uvError,b=2*level-1;
            const double denominator=ray.clipDirection[coordinate]-b*ray.clipDirection[3];
            if(std::abs(denominator)<1e-15)continue;
            const double t=(b*ray.clipOrigin[3]-ray.clipOrigin[coordinate])/denominator;
            if(t>0&&t<.4)boundaries.push_back(t);
        }
    }
    std::sort(boundaries.begin(),boundaries.end());boundaries.erase(std::unique(boundaries.begin(),boundaries.end()),boundaries.end());
    qualify(boundaries.size()<2048,"near-wall cell partition exceeds bounded fixture");std::vector<NearCell> result;
    for(size_t i=1;i<boundaries.size();++i) {
        const double a=boundaries[i-1],b=boundaries[i];if(b-a<1e-14)continue;
        const auto ua=nearUV(ray,a),ub=nearUV(ray,b);
        const double xLow=std::min(ua[0],ub[0])-ray.uvError,xHigh=std::max(ua[0],ub[0])+ray.uvError;
        const double yLow=std::min(ua[1],ub[1])-ray.uvError,yHigh=std::max(ua[1],ub[1])+ray.uvError;
        qualify(xLow>=.002&&xHigh<=.998&&yLow>=.002&&yHigh<=.998,"near-wall full first bracket leaves unchanged viewport guard");
        const int x0=int(std::floor(std::nextafter(xLow,-std::numeric_limits<double>::infinity())*in.width));
        const int x1=int(std::floor(std::nextafter(xHigh,std::numeric_limits<double>::infinity())*in.width));
        const int y0=int(std::floor(std::nextafter(yLow,-std::numeric_limits<double>::infinity())*in.height));
        const int y1=int(std::floor(std::nextafter(yHigh,std::numeric_limits<double>::infinity())*in.height));
        qualify(x0>=0&&x1<in.width&&y0>=0&&y1<in.height&&(x1-x0+1)*(y1-y0+1)<=9,"near-wall expanded cell range unresolved");
        for(int y=y0;y<=y1;++y)for(int x=x0;x<=x1;++x){const int pixel=y*in.width+x;const auto z=nearStoredZ(in,depth[pixel]);result.push_back({index,pixel,a,b,z[0],z[1]});}
    }
    return result;
}
inline NearOracle nearReflectionOracle(const Input& in,const std::vector<Box>& wall,const std::vector<float>& depth,
    const std::vector<float>& source,const V3& observedPosition,const V3& observedNormal,double clarity,std::string* evidence=nullptr) {
    qualify(!in.supplied&&in.width==129&&in.height==129&&wall.size()==1,"near oracle requires frozen native case");
    qualify(depth.size()==size_t(in.width*in.height)&&source.size()==depth.size()*4,"near oracle actual input sizes differ");
    for(float value:depth)qualify(std::isfinite(value),"nonfinite actual near depth");
    for(float value:source)qualify(std::isfinite(value),"nonfinite actual near source");
    qualify(clarity>0&&std::isfinite(clarity),"near clarity invalid");
    const V3 ideal=add(in.eye,ray(in,24.5/129,11.5/129),3.25/ray(in,24.5/129,11.5/129)[1]);
    for(int c=0;c<3;++c)qualify(std::abs(observedPosition[c]-ideal[c])<=arithmeticBound(1+std::abs(ideal[c]),256),"near actual original-VS position differs from frozen plane");
    const double normalLength=std::sqrt(dot(observedNormal,observedNormal));
    qualify(std::abs(normalLength-1)<=arithmeticBound(2,128),"near actual normal length unresolved");
    const V3 n=normalized(observedNormal);for(int c=0;c<3;++c)qualify(std::abs(n[c]-(c==1?-1.0:0.0))<=arithmeticBound(2,128),"near actual facet is not flat underside");
    NearOracle oracle;std::vector<double> firstParameters;int sourceAxis=-1,sourceSide=0;
    for(int sample=-1;sample<4;++sample) {
        const V3 incident=sample<0?normalized(add(observedPosition,in.eye,-1)):ray(in,double(24+(sample&1))/129,double(11+((sample>>1)&1))/129);
        qualify(boundary(incident).tir,"near centre/corner ray is not independently TIR");
        const V3 surface=sample<0?observedPosition:add(in.eye,incident,3.25/incident[1]);
        const V3 mirror=add(incident,n,-2*dot(incident,n));
        // Actual FS viewStart expression, widened from observed P/N + actual
        // uploaded matrices. Physical-origin intersection is applicability only.
        NearRay current;current.origin=add(point(widen(in.view),surface),vector(widen(in.view),observedNormal),.06);
        current.direction=vector(widen(in.view),mirror);current.norm=std::sqrt(dot(current.direction,current.direction));
        qualify(std::abs(current.norm-1)<=arithmeticBound(2,256),"near ray/isometry lacks declared unit envelope");
        if(sample<0){oracle.rayNormMinimum=current.norm;oracle.rayNormMaximum=current.norm;}
        const V3 biased=point(in.inverseView,current.origin);const auto first=firstHit(wall,biased,mirror),physical=firstHit(wall,surface,mirror);
        const auto front=firstHit(wall,in.eye,incident);
        qualify(first.valid&&!first.inside&&!first.tangent&&physical.valid&&!physical.inside&&!physical.tangent&&first.axis==physical.axis&&first.side==physical.side
            &&first.id==physical.id&&(!front.valid||front.travel>3.25/incident[1])&&first.point[1]<3.25&&physical.point[1]<3.25,"near independent biased/physical first source not qualified");
        if(sourceAxis<0){sourceAxis=first.axis;sourceSide=first.side;}
        qualify(first.axis==sourceAxis&&first.side==sourceSide,"near target footprint spans different first wall sides");
        if(sample<0)firstParameters.push_back(first.travel);
        const auto uv=project(in,first.point),physicalUV=project(in,physical.point);
        for(const auto& coordinate:{uv,physicalUV})qualify(coordinate[0]>=.02&&coordinate[0]<=.98&&coordinate[1]>=.02&&coordinate[1]<=.98,"near physical source outside retained visibility margin");
        const int sx=int(uv[0]*in.width),sy=int(uv[1]*in.height);
        for(int corner=0;corner<4;++corner){const auto hit=firstHit(wall,in.eye,ray(in,double(sx+(corner&1))/in.width,double(sy+((corner>>1)&1))/in.height));
            qualify(hit.valid&&!hit.inside&&!hit.tangent&&hit.axis==first.axis&&hit.side==first.side,"near camera-source footprint crosses genuine side/occlusion edge");}
        // Four target-corner rays prove physical/source applicability. The one
        // C0 fragment follows only its actual centre P/N ray + FP envelope;
        // do not require four DIFFERENT shader rays to share its depth root.
        if(sample>=0)continue;
        current.clipOrigin=multiply(widen(in.projection),{current.origin[0],current.origin[1],current.origin[2],1});
        current.clipDirection=multiply(widen(in.projection),{current.direction[0],current.direction[1],current.direction[2],0});
        const double originError=arithmeticBound(1+std::sqrt(dot(current.origin,current.origin)),128);
        const double directionError=arithmeticBound(2,128)+8*std::abs(normalLength-1),qError=originError+.4*directionError;
        current.zError=qError;std::array<double,4> clipError={};
        for(int r=0;r<4;++r){double norm=0;for(int c=0;c<3;++c)norm+=std::abs(in.projection[c*4+r]);
            clipError[r]=norm*qError+arithmeticBound(std::abs(current.clipOrigin[r])+.4*std::abs(current.clipDirection[r])+1,64);}
        const double minimumW=std::min(current.clipOrigin[3],current.clipOrigin[3]+.4*current.clipDirection[3]);qualify(minimumW>clipError[3],"near first bracket clip W unresolved");
        for(int c=0;c<2;++c){const double maximum=std::max(std::abs(current.clipOrigin[c]),std::abs(current.clipOrigin[c]+.4*current.clipDirection[c]));
            current.uvError=std::max(current.uvError,(clipError[c]+maximum/minimumW*clipError[3])/(2*(minimumW-clipError[3]))+arithmeticBound(1,8));}
        oracle.rays.push_back(current);const auto cells=nearCells(in,current,int(oracle.rays.size()-1),depth);
        oracle.cells.insert(oracle.cells.end(),cells.begin(),cells.end());
    }
    std::ostringstream rows;rows<<std::setprecision(14)<<"ray,begin,end,x,y,zLow,zHigh,gLow,gHigh,preSign,postSign\n";
    for(const NearCell& cell:oracle.cells) {
        const auto& r=oracle.rays[cell.ray];const double a=r.origin[2]+r.direction[2]*cell.begin,b=r.origin[2]+r.direction[2]*cell.end;
        const double lower=std::min(a,b)-r.zError-cell.zHigh,upper=std::max(a,b)+r.zError-cell.zLow;
        const bool pre=lower>0,post=upper<0;if(!pre)oracle.corridorLow=std::min(oracle.corridorLow,cell.begin);if(!post)oracle.corridorHigh=std::max(oracle.corridorHigh,cell.end);
        rows<<cell.ray<<","<<cell.begin<<","<<cell.end<<","<<cell.pixel%in.width<<","<<cell.pixel/in.width<<","<<cell.zLow<<","<<cell.zHigh<<","<<lower<<","<<upper<<","<<pre<<","<<post<<"\n";
    }
    oracle.records=rows.str();if(evidence)*evidence=oracle.records;
    std::ostringstream endpoint;endpoint<<std::setprecision(14);
    for(const NearCell& cell:oracle.cells)if(cell.end==.4){const auto& r=oracle.rays[cell.ray];endpoint<<" ray"<<cell.ray<<" cell"<<cell.pixel%in.width<<":"<<cell.pixel/in.width
        <<" finalG="<<r.origin[2]+r.direction[2]*.4-r.zError-cell.zHigh<<":"<<r.origin[2]+r.direction[2]*.4+r.zError-cell.zLow;}
    qualify(oracle.corridorLow>0&&oracle.corridorLow<=oracle.corridorHigh&&oracle.corridorHigh<.4,
        "near full reachable-cell prefix/suffix signs do not bound first crossing L="+std::to_string(oracle.corridorLow)+" U="+std::to_string(oracle.corridorHigh)+endpoint.str());
    for(double value:firstParameters)qualify(value>=oracle.corridorLow&&value<=oracle.corridorHigh,"near biased first intersection lies outside independent sign corridor");
    const double parameterHigh=std::min(.4,oracle.corridorHigh+.4/16+arithmeticBound(.4,16));
    const double lengthError=arithmeticBound(1+parameterHigh,128),directionError=arithmeticBound(2,128)+8*std::abs(normalLength-1);
    oracle.pathLow=std::max(0.0,oracle.corridorLow*(oracle.rayNormMinimum-directionError)-lengthError);
    oracle.pathHigh=parameterHigh*(oracle.rayNormMaximum+directionError)+lengthError;
    for(const NearCell& cell:oracle.cells) {
        const double a=std::max(cell.begin,oracle.corridorLow),b=std::min(cell.end,parameterHigh);if(a>b)continue;
        const auto& r=oracle.rays[cell.ray];const auto ua=nearUV(r,a),ub=nearUV(r,b);
        for(int c=0;c<2;++c)oracle.edgeMinimum=std::min({oracle.edgeMinimum,ua[c]-r.uvError,ub[c]-r.uvError,1-ua[c]-r.uvError,1-ub[c]-r.uvError});
        const double za=r.origin[2]+r.direction[2]*a,zb=r.origin[2]+r.direction[2]*b;
        oracle.maximumResidual=std::max({oracle.maximumResidual,std::abs(std::min(za,zb)-r.zError-cell.zHigh),std::abs(std::max(za,zb)+r.zError-cell.zLow)});
        qualify(depth[cell.pixel]<.999999f&&source[cell.pixel*4]>0&&source[cell.pixel*4+1]==0&&source[cell.pixel*4+2]==0&&source[cell.pixel*4+3]==1,"near final-return reachable cell lacks isolated positive source");
        oracle.sourceMinimum=std::min(oracle.sourceMinimum,double(source[cell.pixel*4]));++oracle.reachableCells;
        for(int corner=0;corner<4;++corner){const auto hit=firstHit(wall,in.eye,ray(in,double(cell.pixel%in.width+(corner&1))/in.width,double(cell.pixel/in.width+((corner>>1)&1))/in.height));
            qualify(hit.valid&&!hit.inside&&!hit.tangent&&hit.axis==sourceAxis&&hit.side==sourceSide,"near final reachable source footprint crosses genuine wall/occlusion edge");}
    }
    oracle.confidenceMinimum=1-smoothUnit((oracle.maximumResidual-.05)/(.18-.05));
    oracle.redLower=oracle.sourceMinimum*std::exp(-.32*oracle.pathHigh/clarity)*smoothUnit(oracle.edgeMinimum/.08)*oracle.confidenceMinimum;
    qualify(oracle.reachableCells>0&&oracle.edgeMinimum>=.002&&oracle.confidenceMinimum>0&&oracle.redLower>0,"near independent edge/confidence/Beer lower bound unresolved");
    oracle.records=rows.str();return oracle;
}
inline std::vector<Box> frozenBlackFirst(const Input& in) {
    auto boxes=frozenNearWall(in);
    const V3 d=ray(in,24.5/129,11.5/129),p=add(in.eye,d,3.25/d[1]),r={d[0],-d[1],d[2]};
    const V3 receiver=add(add(p,{0,-1,0},.06),r,.18);
    const int axis=std::abs(r[0])>std::abs(r[2])?0:2,other=2-axis;const double sign=r[axis]>0?1:-1;
    Box black;black.id=2;black.lo=add(receiver,{-.22,-.22,-.22});black.hi=add(receiver,{.22,.22,.22});
    black.lo[axis]=receiver[axis]-(sign<0?.04:0);black.hi[axis]=receiver[axis]+(sign>0?.04:0);
    black.lo[other]=receiver[other]-.22;black.hi[other]=receiver[other]+.22;
    black.hi[1]=std::min(black.hi[1],in.eye[1]+3.25-.001);boxes.push_back(black);return boxes;
}
inline size_t qualifyBlackFirst(const Input& in,const std::vector<Box>& boxes,const std::vector<float>& source,
    const std::vector<float>& depth,const V3& observedPosition,const V3& observedNormal) {
    qualify(boxes.size()==2&&source.size()==size_t(in.width*in.height*4)&&depth.size()==size_t(in.width*in.height),"black-first input dimensions differ");
    const V3 expected=add(in.eye,ray(in,24.5/129,11.5/129),3.25/ray(in,24.5/129,11.5/129)[1]);
    for(int c=0;c<3;++c)qualify(std::abs(observedPosition[c]-expected[c])<=arithmeticBound(1+std::abs(expected[c]),256),"black-first observed VS position differs");
    qualify(std::abs(std::sqrt(dot(observedNormal,observedNormal))-1)<=arithmeticBound(2,128),"black-first observed normal length differs");
    const V3 n=normalized(observedNormal);
    for(int c=0;c<3;++c)qualify(std::abs(n[c]-(c==1?-1.0:0.0))<=arithmeticBound(2,128),"black-first observed facet differs");
    for(int sample=-1;sample<4;++sample) {
        const V3 incident=sample<0?normalized(add(observedPosition,in.eye,-1)):ray(in,double(24+(sample&1))/in.width,double(11+((sample>>1)&1))/in.height);
        qualify(boundary(incident).tir,"black-first target footprint is not TIR");
        const V3 p=sample<0?observedPosition:add(in.eye,incident,3.25/incident[1]),mirror=add(incident,n,-2*dot(incident,n));
        const V3 biased=point(in.inverseView,add(point(widen(in.view),p),vector(widen(in.view),observedNormal),.06));
        const auto physical=firstHit(boxes,p,mirror),first=firstHit(boxes,biased,mirror),foreground=firstHit(boxes,in.eye,incident);
        qualify(physical.valid&&first.valid&&!physical.inside&&!first.inside&&!physical.tangent&&!first.tangent&&physical.id==2&&first.id==2
            &&physical.axis==first.axis&&physical.side==first.side&&(!foreground.valid||foreground.travel>3.25/incident[1]),"black is not the independently visible FIRST reflected receiver");
        for(const auto& hit:{physical,first}) {
            for(int c=0;c<3;++c)if(c!=hit.axis)qualify(std::min(hit.point[c]-boxes[1].lo[c],boxes[1].hi[c]-hit.point[c])>arithmeticBound(1+std::abs(hit.point[c]),512),"black first-hit footprint touches physical box edge");
            const auto uv=project(in,hit.point);qualify(uv[0]>=.02&&uv[0]<=.98&&uv[1]>=.02&&uv[1]<=.98,"black first receiver outside source visibility margin");
            const int x=int(uv[0]*in.width),y=int(uv[1]*in.height),pixel=y*in.width+x;
            qualify(depth[pixel]<.999999f&&source[pixel*4]==0&&source[pixel*4+1]==0&&source[pixel*4+2]==0&&source[pixel*4+3]==1,"actual own-source black receiver is not black/opaque");
            for(int corner=0;corner<4;++corner){const auto camera=firstHit(boxes,in.eye,ray(in,double(x+(corner&1))/in.width,double(y+((corner>>1)&1))/in.height));
                qualify(camera.valid&&!camera.inside&&!camera.tangent&&camera.id==2&&camera.axis==hit.axis&&camera.side==hit.side,"black own-source camera footprint crosses real occlusion/box edge");}
        }
    }
    size_t redPixels=0,redFullFootprints=0;
    for(int y=0;y<in.height;++y)for(int x=0;x<in.width;++x){const int pixel=y*in.width+x;if(source[pixel*4]!=.75f)continue;
        qualify(std::isfinite(depth[pixel])&&depth[pixel]<.999999f&&source[pixel*4+1]==0&&source[pixel*4+2]==0&&source[pixel*4+3]==1,"actual background red source differs");++redPixels;
        bool full=true;for(int corner=0;corner<4;++corner){const auto camera=firstHit(boxes,in.eye,ray(in,double(x+(corner&1))/in.width,double(y+((corner>>1)&1))/in.height));
            full=full&&camera.valid&&!camera.inside&&!camera.tangent&&camera.id==1;}
        if(full)++redFullFootprints;
    }
    qualify(redPixels>16&&redFullFootprints>16,"black-first negative is vacuous: no resolved positive camera-visible red background");return redFullFootprints;
}
} // namespace aqualumenUnderwaterAngularDetail

inline void productionUnderwaterAngularProbe(const std::filesystem::path& root,const std::filesystem::path& artifacts,
    const aqualumenUnderwaterAngularDetail::Input& in,bool nearReflectionOnly=false) {
    using namespace aqualumenUnderwaterAngularDetail;
    using aqualumenSolarProbeDetail::declaredFormat;
    const auto* name=glGetString(GL_RENDERER);qualify(name&&std::string(reinterpret_cast<const char*>(name)).find("NVIDIA")!=std::string::npos,"real NVIDIA renderer required");
    qualify(!artifacts.empty()&&!std::filesystem::exists(artifacts),"choose a NEW artifact directory");
    GLint attachments=0,subpixelBits=0;glGetIntegerv(GL_MAX_DRAW_BUFFERS,&attachments);glGetIntegerv(GL_SUBPIXEL_BITS,&subpixelBits);
    qualify(attachments>=4&&subpixelBits>=4,"four MRTs and declared raster subpixel precision required");
    std::filesystem::create_directories(artifacts);
    const auto vs=expand(root/"gbuffers_water.vsh",root,0),fs=expand(root/"gbuffers_water.fsh",root,0);
    const auto vertex=aqualumenWaterRadianceDetail::flatOptions(vs),fragment=aqualumenWaterRadianceDetail::flatOptions(fs);
    const auto producer=expand(root/"prepare.fsh",root,0);
    const GLenum c0Format=declaredFormat(producer,0),skyFormat=declaredFormat(producer,6);
    qualify(c0Format==GL_RGBA32F&&(skyFormat==GL_RGBA16F||skyFormat==GL_RGBA32F),"declared output/LUT formats changed");
    std::string observed=fragment;
    const std::string anchor="    gl_FragData[0]=vec4(max(color,vec3(0.0)),1.0);";
    const auto at=observed.find(anchor);qualify(at!=std::string::npos&&observed.find(anchor,at+anchor.size())==std::string::npos,"water final STORE anchor ambiguous");
    const std::string stores="\n// DEBUG-underwater-angular STORE begin\n    gl_FragData[1]=vec4(n,fresnel);\n    gl_FragData[2]=vec4(transmitted,float(receiverKind));\n    gl_FragData[3]=vec4(worldPosition,reflectedHit.a);\n// DEBUG-underwater-angular STORE end\n";
    observed.insert(at+anchor.size(),stores);auto recovered=observed;recovered.erase(at+anchor.size(),stores.size());
    qualify(recovered==fragment,"removing STOREs did not recover exact original option-main");
    textFile(artifacts/"shipping-expanded.vsh",vs);textFile(artifacts/"shipping-expanded.fsh",fs);
    textFile(artifacts/"production-flat.vsh",vertex);textFile(artifacts/"production-flat.fsh",fragment);textFile(artifacts/"passive-stores.fsh",observed);
    std::ostringstream packet;packet<<std::setprecision(9)<<"aqualumen-underwater-matrices-v1\nsource_size "<<in.sourceWidth<<" "<<in.sourceHeight<<"\n";
    for(auto item:std::array<std::pair<const char*,M4>,4>{{{"gbufferProjection",in.projection},{"gbufferProjectionInverse",in.projectionInverse},{"gbufferModelView",in.view},{"gbufferModelViewInverse",in.viewInverse}}}) {
        packet<<item.first;for(float v:item.second)packet<<" "<<v;packet<<"\n";
    }
    textFile(artifacts/"used-matrices.txt",packet.str());
    aqualumenWaterOpticalDepthDetail::Fixture fixture;aqualumenWaterRadianceDetail::SamplerState samplerState;
    fixture.programs[0]=link(vertex,fragment,"underwater-angular-original-main","mc_Entity");
    fixture.programs[1]=link(vertex,observed,"underwater-angular-store-only-main","mc_Entity");
    const int count=in.width*in.height;auto& textures=fixture.textures;
    for(GLenum option:{GL_PACK_ROW_LENGTH,GL_PACK_SKIP_ROWS,GL_PACK_SKIP_PIXELS,GL_UNPACK_ROW_LENGTH,GL_UNPACK_SKIP_ROWS,GL_UNPACK_SKIP_PIXELS})glPixelStorei(option,0);
    glPixelStorei(GL_PACK_SWAP_BYTES,GL_FALSE);glPixelStorei(GL_UNPACK_SWAP_BYTES,GL_FALSE);
    for(GLenum option:{GL_RED_SCALE,GL_GREEN_SCALE,GL_BLUE_SCALE,GL_ALPHA_SCALE,GL_DEPTH_SCALE})glPixelTransferf(option,1);
    for(GLenum option:{GL_RED_BIAS,GL_GREEN_BIAS,GL_BLUE_BIAS,GL_ALPHA_BIAS,GL_DEPTH_BIAS})glPixelTransferf(option,0);
    glPixelTransferi(GL_MAP_COLOR,GL_FALSE);
    const auto allocate=[&](int slot,GLenum format,int w,int h,GLenum channel,const float* data) {
        glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,textures[slot]);
        for(GLenum p:{GL_TEXTURE_MIN_FILTER,GL_TEXTURE_MAG_FILTER})glTexParameteri(GL_TEXTURE_2D,p,GL_NEAREST);
        for(GLenum p:{GL_TEXTURE_WRAP_S,GL_TEXTURE_WRAP_T})glTexParameteri(GL_TEXTURE_2D,p,GL_CLAMP_TO_EDGE);
        glTexImage2D(GL_TEXTURE_2D,0,format,w,h,0,channel,GL_FLOAT,data);
        GLint actual=0;glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_INTERNAL_FORMAT,&actual);qualify(GLenum(actual)==format,"actual allocation differs");
    };
    const float white[4]={1,1,1,1},black[4]={0,0,0,1},shadow=0;std::vector<float> skyDepth(count,1),blackImage(count*4,0);
    for(int p=0;p<count;++p)blackImage[p*4+3]=1;
    auto markerField=field(),zeroField=field(true),rotatedField=field(false,true);
    allocate(0,GL_RGBA32F,1,1,GL_RGBA,white);allocate(1,GL_RGBA32F,in.width,in.height,GL_RGBA,blackImage.data());
    allocate(2,skyFormat,skyWidth,skyHeight,GL_RGBA,markerField.data());allocate(3,GL_DEPTH_COMPONENT32F,in.width,in.height,GL_DEPTH_COMPONENT,skyDepth.data());
    allocate(4,GL_DEPTH_COMPONENT32F,1,1,GL_DEPTH_COMPONENT,&shadow);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_MODE,GL_COMPARE_REF_TO_TEXTURE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_FUNC,GL_LEQUAL);
    allocate(5,GL_RGBA16F,1,1,GL_RGBA,black);allocate(7,skyFormat,skyWidth,skyHeight,GL_RGBA,zeroField.data());allocate(15,GL_RGBA32F,1,1,GL_RGBA,black);
    const std::array<int,4> outputSlots={6,8,9,10};std::array<GLenum,4> draws={};
    glBindFramebuffer(GL_FRAMEBUFFER,fixture.framebuffer);
    for(int i=0;i<4;++i){allocate(outputSlots[i],i==0?c0Format:GL_RGBA32F,in.width,in.height,GL_RGBA,nullptr);draws[i]=GL_COLOR_ATTACHMENT0+i;glFramebufferTexture2D(GL_FRAMEBUFFER,draws[i],GL_TEXTURE_2D,textures[outputSlots[i]],0);}
    glDrawBuffers(4,draws.data());qualify(glCheckFramebufferStatus(GL_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE,"separate-output framebuffer incomplete");
    const auto readSky=[&](const std::vector<float>& data,const std::string& label) {
        glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,textures[2]);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,skyWidth,skyHeight,GL_RGBA,GL_FLOAT,data.data());
        std::vector<float> actual(data.size(),std::numeric_limits<float>::quiet_NaN());glGetTexImage(GL_TEXTURE_2D,0,GL_RGBA,GL_FLOAT,actual.data());
        for(float v:actual)qualify(std::isfinite(v),"nonfinite actual source");
        rawFile(artifacts/(label+"-C6.rgba32f"),actual);return actual;
    };
    const auto actualField=readSky(markerField,"positive"),actualRotated=readSky(rotatedField,"rotated"),actualZero=readSky(zeroField,"zero");
    double sourceStorageError=0;
    for(size_t p=0;p<actualField.size();++p) {
        sourceStorageError=std::max(sourceStorageError,std::abs(double(actualField[p])-markerField[p]));
        qualify(actualZero[p]==zeroField[p],"actual zero source differs");
        qualify(std::abs(double(actualField[p])-markerField[p])<=storageRoundoff(skyFormat,markerField[p]),"source exceeds declared storage rounding");
    }
    // Masked cones include the entire interpolation cell around the five diffuse
    // quadrature directions. Independent angular padding excludes their edge
    // from the evaluated field; no incident/scattering formula is duplicated.
    const double cellAngle=2*pi/skyWidth+pi/(skyHeight-2);
    const V3 sunView=vector(widen(in.view),{0,1,0});
    for(GLuint program:fixture.programs) {
        glUseProgram(program);
        const char* names[]={"gtexture","colortex4","colortex6","depthtex1","shadowtex0","colortex8","aqualumenBathymetry","colortex7"};
        for(int unit=0;unit<8;++unit){const GLint loc=glGetUniformLocation(program,names[unit]);qualify(loc>=0,"active sampler missing");glUniform1i(loc,unit);}
        for(auto item:std::array<std::pair<const char*,M4>,6>{{{"gbufferProjection",in.projection},{"gbufferProjectionInverse",in.projectionInverse},
            {"gbufferModelView",in.view},{"gbufferModelViewInverse",in.viewInverse},{"shadowProjection",aqualumenWaterRadianceDetail::identity},{"shadowModelView",aqualumenWaterRadianceDetail::identity}}})
            glUniformMatrix4fv(glGetUniformLocation(program,item.first),1,GL_FALSE,item.second.data());
        glUniform3f(glGetUniformLocation(program,"cameraPosition"),0,63-float(in.eye[1]),0);
        glUniform3f(glGetUniformLocation(program,"sunPosition"),float(sunView[0]),float(sunView[1]),float(sunView[2]));
        glUniform3f(glGetUniformLocation(program,"shadowLightPosition"),float(sunView[0]),float(sunView[1]),float(sunView[2]));
        glUniform1f(glGetUniformLocation(program,"viewWidth"),float(in.width));glUniform1f(glGetUniformLocation(program,"viewHeight"),float(in.height));
        glUniform1f(glGetUniformLocation(program,"far"),128);glUniform1f(glGetUniformLocation(program,"frameTimeCounter"),120);
        glUniform1f(glGetUniformLocation(program,"rainStrength"),0);glUniform1f(glGetUniformLocation(program,"wetness"),0);
        glUniform1i(glGetUniformLocation(program,"isEyeInWater"),1);glUniform1i(glGetUniformLocation(program,"aqualumenDimension"),0);
        glUniform1i(glGetUniformLocation(program,"aqualumenActive"),0);glUniform1i(glGetUniformLocation(program,"aqualumenBathymetryReady"),0);
        glUniform1i(glGetUniformLocation(program,"worldTime"),6000);glUniform2i(glGetUniformLocation(program,"eyeBrightnessSmooth"),0,240);
    }
    glDisableVertexAttribArray(10);glVertexAttrib4f(10,10000,0,0,0);
    for(GLenum cap:{GL_DEPTH_TEST,GL_BLEND,GL_CULL_FACE,GL_ALPHA_TEST,GL_STENCIL_TEST,GL_SCISSOR_TEST,GL_FOG,GL_DITHER,GL_FRAMEBUFFER_SRGB,
        GL_COLOR_LOGIC_OP,GL_RASTERIZER_DISCARD,GL_POLYGON_OFFSET_FILL,GL_SAMPLE_ALPHA_TO_COVERAGE,GL_SAMPLE_COVERAGE})glDisable(cap);
    glDepthMask(GL_FALSE);glColorMask(GL_TRUE,GL_TRUE,GL_TRUE,GL_TRUE);glPolygonMode(GL_FRONT_AND_BACK,GL_FILL);glViewport(0,0,in.width,in.height);
    glMatrixMode(GL_PROJECTION);glLoadMatrixf(in.projection.data());glMatrixMode(GL_MODELVIEW);glLoadMatrixf(in.view.data());
    glColor4f(1,1,1,1);glNormal3f(0,1,0);glMultiTexCoord2f(GL_TEXTURE0,.5f,.5f);glMultiTexCoord2f(GL_TEXTURE1,0,1);
    std::vector<float> actualBoundColour,actualBoundDepth;bool isolationReadBack=false;
    const auto readBound=[&](GLuint program,const char* uniform,int expectedUnit,GLuint expectedTexture,GLenum expectedFormat,int w,int h,
        GLenum channel,const std::vector<float>& supplied,const std::string& label) {
        const GLint location=glGetUniformLocation(program,uniform);qualify(location>=0,"near active input sampler missing");
        const GLchar* name=uniform;GLuint index=GL_INVALID_INDEX;glGetUniformIndices(program,1,&name,&index);qualify(index!=GL_INVALID_INDEX,"near typed sampler index absent");
        GLint type=0,size=0,unit=-1;glGetActiveUniformsiv(program,1,&index,GL_UNIFORM_TYPE,&type);glGetActiveUniformsiv(program,1,&index,GL_UNIFORM_SIZE,&size);glGetUniformiv(program,location,&unit);
        qualify(type==GL_SAMPLER_2D&&size==1&&unit==expectedUnit,"near actual typed sampler/unit differs");
        GLint active=0;glGetIntegerv(GL_ACTIVE_TEXTURE,&active);glActiveTexture(GL_TEXTURE0+unit);
        GLint texture=0,sampler=0,format=0,width=0,height=0,minimum=0,magnification=0,compare=0;
        glGetIntegerv(GL_TEXTURE_BINDING_2D,&texture);glGetIntegerv(GL_SAMPLER_BINDING,&sampler);
        glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_INTERNAL_FORMAT,&format);glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_WIDTH,&width);glGetTexLevelParameteriv(GL_TEXTURE_2D,0,GL_TEXTURE_HEIGHT,&height);
        glGetTexParameteriv(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,&minimum);glGetTexParameteriv(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,&magnification);glGetTexParameteriv(GL_TEXTURE_2D,GL_TEXTURE_COMPARE_MODE,&compare);
        qualify(GLuint(texture)==expectedTexture&&sampler==0&&GLenum(format)==expectedFormat&&width==w&&height==h&&minimum==GL_NEAREST&&magnification==GL_NEAREST&&compare==GL_NONE,
            "near actual texture storage/filter/binding differs");
        std::vector<float> actual(supplied.size(),std::numeric_limits<float>::quiet_NaN());glGetTexImage(GL_TEXTURE_2D,0,channel,GL_FLOAT,actual.data());glActiveTexture(active);
        for(size_t i=0;i<actual.size();++i)qualify(std::isfinite(actual[i])&&actual[i]==supplied[i],"near actual RGBA32F/depth32F/zero-source readback differs from supplied input");
        rawFile(artifacts/(label+(channel==GL_DEPTH_COMPONENT?".f32":".rgba32f")),actual);
        std::ostringstream metadata;metadata<<"uniform="<<uniform<<" type="<<type<<" size="<<size<<" unit="<<unit<<" texture="<<texture<<" sampler="<<sampler<<" format="<<format<<" dimensions="<<w<<"x"<<h<<" finiteExactReadback=1\n";
        textFile(artifacts/(label+".txt"),metadata.str());return actual;
    };
    const auto draw=[&](double depth,const std::vector<float>& source,const std::vector<float>& sceneDepth,const std::vector<float>& colour,bool observe,const std::string& label) {
        const std::array<std::pair<int,const std::vector<float>*>,3> data={{{1,&colour},{2,&source},{3,&sceneDepth}}};
        for(const auto& item:data){glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,textures[item.first]);glTexSubImage2D(GL_TEXTURE_2D,0,0,0,item.first==2?skyWidth:in.width,item.first==2?skyHeight:in.height,item.first==3?GL_DEPTH_COMPONENT:GL_RGBA,GL_FLOAT,item.second->data());}
        for(int unit=0;unit<8;++unit){glActiveTexture(GL_TEXTURE0+unit);glBindTexture(GL_TEXTURE_2D,unit==6?textures[15]:textures[unit]);}
        glBindFramebuffer(GL_FRAMEBUFFER,fixture.framebuffer);glDrawBuffers(4,draws.data());const float zero[4]={};for(int i=0;i<4;++i)glClearBufferfv(GL_COLOR,i,zero);
        glDrawBuffers(observe?4:1,draws.data());glUseProgram(fixture.programs[observe?1:0]);
        if(nearReflectionOnly) {
            const GLuint program=fixture.programs[observe?1:0];
            actualBoundColour=readBound(program,"colortex4",1,textures[1],GL_RGBA32F,in.width,in.height,GL_RGBA,colour,label+"-bound-C4");
            actualBoundDepth=readBound(program,"depthtex1",3,textures[3],GL_DEPTH_COMPONENT32F,in.width,in.height,GL_DEPTH_COMPONENT,sceneDepth,label+"-bound-depth");
            if(!isolationReadBack){(void)readBound(program,"colortex6",2,textures[2],skyFormat,skyWidth,skyHeight,GL_RGBA,zeroField,"isolation-bound-C6");
                (void)readBound(program,"colortex7",7,textures[7],skyFormat,skyWidth,skyHeight,GL_RGBA,zeroField,"isolation-bound-C7");isolationReadBack=true;}
        }
        std::array<V3,4> corners={};
        for(int i=0;i<4;++i){const V3 d=ray(in,(i&1)?1.01:-.01,(i&2)?1.01:-.01);qualify(d[1]>0,"captured view does not cover a finite upward plane");corners[i]=add(in.eye,d,depth/d[1]);}
        const int order[6]={0,1,3,0,3,2};glBegin(GL_TRIANGLES);for(int i:order)glVertex3f(float(corners[i][0]),float(corners[i][1]),float(corners[i][2]));glEnd();
        Capture capture;
        for(int i=0;i<(observe?4:1);++i){capture.output[i].assign(count*4,std::numeric_limits<float>::quiet_NaN());glReadBuffer(draws[i]);glReadPixels(0,0,in.width,in.height,GL_RGBA,GL_FLOAT,capture.output[i].data());for(float v:capture.output[i])qualify(std::isfinite(v),"nonfinite output");rawFile(artifacts/(label+"-output"+std::to_string(i)+".rgba32f"),capture.output[i]);}
        qualify(glGetError()==GL_NO_ERROR,"GL error during original draw/readback");return capture;
    };
    std::ofstream results;if(!nearReflectionOnly){results.open(artifacts/"angular.csv");results<<std::setprecision(14)<<"eyeDepth,x,y,waterAngleDeg,airAngleDeg,tir,channel,actual,expected,bound,fresnelExpected,fresnelActual,kind\n";}
    bool failed=false;size_t qualified=0,tirCount=0;int inViewport=0,offViewport=0;double maximumError=0,wrongOracleError=0,rotatedError=0;
    if(!nearReflectionOnly)for(double depth:{.5,3.25}) {
        std::vector<Sample> samples;
        // Dense fixed NDC pixel grid: selection is CPU input geometry only,
        // before any actual C0/observer response is available.
        for(int y=1;y<in.height-1;++y)for(int x=1;x<in.width-1;++x) {
            const V3 incoming=ray(in,(x+.5)/in.width,(y+.5)/in.height);if(incoming[1]<=0)continue;
            const double angle=std::acos(std::clamp(incoming[1],-1.0,1.0));const auto optical=boundary(incoming);
            if(std::abs(angle-std::asin(1/index))<1.5*pi/180)continue;
            if(!optical.tir&&(masked(optical.transmitted,2*cellAngle)||optical.transmitted[1]<.03))continue;
            Sample s;s.x=x;s.y=y;s.incident=incoming;s.surface=add(in.eye,incoming,depth/incoming[1]);s.tir=optical.tir;s.transmitted=optical.transmitted;s.fresnel=optical.fresnel;samples.push_back(s);
        }
        qualify(samples.size()>256,"insufficient prequalified angular grid");
        const std::string prefix=depth==.5?"near":"deep";
        const auto zero=draw(depth,zeroField,skyDepth,blackImage,false,prefix+"-zero"),positive=draw(depth,markerField,skyDepth,blackImage,false,prefix+"-positive"),
            repeat=draw(depth,markerField,skyDepth,blackImage,false,prefix+"-repeat"),observedPositive=draw(depth,markerField,skyDepth,blackImage,true,prefix+"-observer"),
            rotated=draw(depth,rotatedField,skyDepth,blackImage,false,prefix+"-rotated");
        qualify(maxDifference(positive.output[0],repeat.output[0])==0,"whole-image repeat differs");
        for(int p=0;p<count;++p) {
            qualify(zero.output[0][p*4+3]==1&&positive.output[0][p*4+3]==1,"flat interface does not cover whole image");
            for(int c=0;c<3;++c)qualify(zero.output[0][p*4+c]==0,"zero source/scattering/reflection isolation failed");
            for(int c=0;c<4;++c){const double a=positive.output[0][p*4+c],b=observedPositive.output[0][p*4+c];qualify(std::abs(a-b)<=storageRoundoff(c0Format,a)+storageRoundoff(c0Format,b)+arithmeticBound(std::abs(a)+std::abs(b)),"STORE observer is not whole-image neutral");}
        }
        auto unrelated=blackImage;for(int p=0;p<count;++p){unrelated[p*4]=.75f;unrelated[p*4+1]=.125f;}
        const auto changedCamera=draw(depth,markerField,skyDepth,unrelated,false,prefix+"-camera-tag");
        qualify(maxDifference(positive.output[0],changedCamera.output[0])==0,"sky-map fixture depends on unrelated C4 camera image");
        for(const Sample& s:samples) {
            const int p=(s.y*in.width+s.x)*4;const auto& state=observedPositive.output;
            const double positionBound=arithmeticBound(1+std::sqrt(dot(s.surface,s.surface)),256)+depth*std::ldexp(1.0,-subpixelBits)/std::min(in.width,in.height)*8;
            for(int c=0;c<3;++c){qualify(std::abs(state[3][p+c]-s.surface[c])<=positionBound,"original VS/raster position is outside declared envelope");qualify(std::abs(state[1][p+c]-(c==1?-1.0:0.0))<=arithmeticBound(2,128),"actual optical normal is not a flat underside");}
            qualify(state[3][p+3]<0,"unexpected SSR geometry in sky-only input");
            const double ct=s.tir?1:s.transmitted[1],fBound=arithmeticBound(4*(1+1/std::pow(std::max(ct,.03),3)),128);
            if(std::abs(state[1][p+3]-s.fresnel)>fBound)failed=true;
            if(s.tir){++tirCount;for(int c=0;c<3;++c){const double a=positive.output[0][p+c];if(a!=0)failed=true;results<<depth<<","<<s.x<<","<<s.y<<","<<std::acos(s.incident[1])*180/pi<<",90,1,"<<c<<","<<a<<",0,0,"<<s.fresnel<<","<<state[1][p+3]<<","<<state[2][p+3]<<"\n";}continue;}
            ++qualified;if(state[2][p+3]!=0&&state[2][p+3]!=2)failed=true;
            for(int c=0;c<3;++c)if(std::abs(state[2][p+c]-s.transmitted[c])>positionBound/depth*4+arithmeticBound(4,256))failed=true;
            const auto projected=project(in,add(s.surface,s.transmitted,48));if(projected[0]>.001&&projected[0]<.999&&projected[1]>.001&&projected[1]<.999)++inViewport;else ++offViewport;
            const V3 expectedField=marker(s.transmitted),wrongField=marker(boundary(s.incident,1).transmitted);
            for(int c=0;c<3;++c) {
                const double expected=(1-s.fresnel)*expectedField[c],actual=positive.output[0][p+c];
                const double angular=.15*cellAngle+sourceStorageError+.15*positionBound/depth*4;
                const double bound=(1-s.fresnel)*angular+expectedField[c]*fBound+arithmeticBound(std::abs(actual)+std::abs(expected),512)+storageRoundoff(c0Format,actual);
                qualify(expected>4*bound&&actual>bound,"positive angular source lacks resolved C0 response");
                const double error=std::abs(actual-expected);maximumError=std::max(maximumError,error);if(error>bound)failed=true;
                wrongOracleError=std::max(wrongOracleError,std::abs(actual-(1-s.fresnel)*wrongField[c])-4*bound);
                rotatedError=std::max(rotatedError,std::abs(rotated.output[0][p+c]-expected)-4*bound);
                results<<depth<<","<<s.x<<","<<s.y<<","<<std::acos(s.incident[1])*180/pi<<","<<std::acos(s.transmitted[1])*180/pi<<",0,"<<c<<","<<actual<<","<<expected<<","<<bound<<","<<s.fresnel<<","<<state[1][p+3]<<","<<state[2][p+3]<<"\n";
            }
        }
    }
    if(!nearReflectionOnly){qualify(qualified>256&&tirCount>16&&inViewport>16&&offViewport>16,"dense positive/TIR/in-and-off-viewport qualification incomplete");
        qualify(wrongOracleError>0&&rotatedError>0,"broken independent index/rotated-marker controls are insensitive");}
    // One independently visible reflected wall in the deep flat fixture. Freeze
    // the first INPUT-qualified TIR pixel; never select by SSR success or C0.
    const auto reflection=reflectionControl(in);const auto& wall=reflection.boxes;const int reflectionPixel=reflection.pixel;const double depth=3.25;
    std::ostringstream reflectionQualification;reflectionQualification<<std::setprecision(14)
        <<"wallTravel="<<reflectionWallTravel<<"\nangleCandidates="<<reflection.angleCandidates
        <<"\nindependentFourCornerQualifiedCandidates="<<reflection.qualifiedCandidates
        <<"\nfirstInputQualifiedPixel="<<reflectionPixel%in.width<<","<<reflectionPixel/in.width
        <<"\nCPU input-geometry qualification only; not an observed SSR response or behavioral PASS.\n"
        <<"Original target/source four-corner visibility, TIR and viewport criteria retained; first qualifying input chosen without C0/SSR selection.\n";
    textFile(artifacts/"reflection-input-qualification.txt",reflectionQualification.str());
    std::vector<float> wallDepth(count,1),wallTag=blackImage;
    for(int y=0;y<in.height;++y)for(int x=0;x<in.width;++x){const auto hit=firstHit(wall,in.eye,ray(in,(x+.5)/in.width,(y+.5)/in.height));if(!hit.valid)continue;const int p=y*in.width+x;wallDepth[p]=float(project(in,hit.point)[2]);qualify(wallDepth[p]>0&&wallDepth[p]<.999999,"wall depth outside representable opaque range");wallTag[p*4]=.75f;}
    rawFile(artifacts/"reflection-control-depth.f32",wallDepth);rawFile(artifacts/"reflection-control-C4.rgba32f",wallTag);
    const auto reflectionBaseOriginal=draw(depth,zeroField,wallDepth,blackImage,false,"reflection-zero-original"),
        reflectionTagOriginal=draw(depth,zeroField,wallDepth,wallTag,false,"reflection-positive-original"),
        reflectionRepeat=draw(depth,zeroField,wallDepth,wallTag,false,"reflection-positive-repeat"),
        reflectionBase=draw(depth,zeroField,wallDepth,blackImage,true,"reflection-zero"),reflectionTag=draw(depth,zeroField,wallDepth,wallTag,true,"reflection-positive");
    qualify(maxDifference(reflectionTagOriginal.output[0],reflectionRepeat.output[0])==0,"whole-image visible-reflection repeat differs");
    for(const auto& pair:std::array<std::pair<const Capture*,const Capture*>,2>{{{&reflectionBaseOriginal,&reflectionBase},{&reflectionTagOriginal,&reflectionTag}}})
        for(size_t i=0;i<pair.first->output[0].size();++i){const double a=pair.first->output[0][i],b=pair.second->output[0][i];qualify(std::abs(a-b)<=storageRoundoff(c0Format,a)+storageRoundoff(c0Format,b)+arithmeticBound(std::abs(a)+std::abs(b)),"reflection STORE observer is not whole-image neutral");}
    const int p=reflectionPixel*4;qualify(reflectionTag.output[3][p+3]>0&&reflectionBase.output[3][p+3]>0,"input-qualified visible reflector was not resolved by actual SSR");
    qualify(reflectionTag.output[1][p+3]==1&&reflectionTag.output[2][p+3]==0,"reflection control is not pure TIR");
    qualify(reflectionTag.output[0][p]-reflectionBase.output[0][p]>.05&&reflectionTag.output[0][p+1]==reflectionBase.output[0][p+1]&&reflectionTag.output[0][p+2]==reflectionBase.output[0][p+2],"visible red reflector lacks isolated positive actual C0 response");
    if(nearReflectionOnly) {
        const double positiveDelta=reflectionTagOriginal.output[0][p]-reflectionBaseOriginal.output[0][p];
        const double positiveBound=storageRoundoff(c0Format,reflectionTagOriginal.output[0][p])+storageRoundoff(c0Format,reflectionBaseOriginal.output[0][p])
            +arithmeticBound(std::abs(double(reflectionTagOriginal.output[0][p]))+std::abs(double(reflectionBaseOriginal.output[0][p]))+.75);
        qualify(positiveDelta>4*positiveBound,"near test no-reflection/F=0 counter-expectation is insensitive");
        const auto nearWall=frozenNearWall(in);std::vector<float> nearDepth(count,1),nearSource=blackImage;
        for(int y=0;y<in.height;++y)for(int x=0;x<in.width;++x){const auto hit=firstHit(nearWall,in.eye,ray(in,(x+.5)/in.width,(y+.5)/in.height));if(!hit.valid)continue;const int pixel=y*in.width+x;
            nearDepth[pixel]=float(project(in,hit.point)[2]);qualify(nearDepth[pixel]>0&&nearDepth[pixel]<.999999,"near source depth not representable");nearSource[pixel*4]=.75f;}
        const auto base=draw(3.25,zeroField,nearDepth,blackImage,false,"near-wall-zero-original"),tag=draw(3.25,zeroField,nearDepth,nearSource,false,"near-wall-tag-original"),
            repeated=draw(3.25,zeroField,nearDepth,nearSource,false,"near-wall-tag-repeat"),baseState=draw(3.25,zeroField,nearDepth,blackImage,true,"near-wall-zero-observer"),
            tagState=draw(3.25,zeroField,nearDepth,nearSource,true,"near-wall-tag-observer");
        qualify(maxDifference(tag.output[0],repeated.output[0])==0,"near original whole-image repeat differs");
        for(const auto& pair:std::array<std::pair<const Capture*,const Capture*>,2>{{{&base,&baseState},{&tag,&tagState}}})for(size_t i=0;i<pair.first->output[0].size();++i){const double a=pair.first->output[0][i],b=pair.second->output[0][i];
            qualify(std::abs(a-b)<=storageRoundoff(c0Format,a)+storageRoundoff(c0Format,b)+arithmeticBound(std::abs(a)+std::abs(b)),"near STORE observer is not whole-image neutral");}
        for(int pixel=0;pixel<count;++pixel){qualify(base.output[0][pixel*4+3]==1&&tag.output[0][pixel*4+3]==1,"near water coverage/alpha changed");
            for(int c=0;c<3;++c)qualify(base.output[0][pixel*4+c]==0,"near zero source is not isolated");
            qualify(tag.output[0][pixel*4+1]==0&&tag.output[0][pixel*4+2]==0,"near red tag affects untagged G/B");}
        const int target=(11*in.width+24)*4;const auto& position=tagState.output[3];const auto& normal=tagState.output[1];
        qualify(normal[target+3]==1&&tagState.output[2][target+3]==0,"near actual TIR/receiver source isolation not qualified");
        const auto sigma=aqualumenWaterRadianceDetail::extinction(fragment);qualify(sigma[0]==.32&&sigma[1]==.085&&sigma[2]==.035,"near declared effective Beer coefficients changed");
        std::string cellEvidence;NearOracle oracle;
        try{oracle=nearReflectionOracle(in,nearWall,actualBoundDepth,actualBoundColour,{position[target],position[target+1],position[target+2]},
            {normal[target],normal[target+1],normal[target+2]},aqualumenWaterRadianceDetail::clarity(fragment),&cellEvidence);}
        catch(...){if(!cellEvidence.empty())textFile(artifacts/"near-reachable-cells.csv",cellEvidence);throw;}
        textFile(artifacts/"near-reachable-cells.csv",oracle.records);
        const double delta=tag.output[0][target]-base.output[0][target],bound=storageRoundoff(c0Format,tag.output[0][target])+storageRoundoff(c0Format,base.output[0][target])
            +arithmeticBound(std::abs(double(tag.output[0][target]))+std::abs(double(base.output[0][target]))+oracle.sourceMinimum+oracle.redLower,512);
        qualify(oracle.redLower>4*bound,"near independent source lower bound lacks resolved numerical margin");
        const double path=position[target+3];const bool passed=delta+bound>=oracle.redLower&&path>=oracle.pathLow&&path<=oracle.pathHigh;
        std::ostringstream report;report<<std::setprecision(15)<<"scope=frozen native129 underwater near-wall original-main tracer\npositive055Response="<<positiveDelta<<"\npositive055CounterBound="<<positiveBound
            <<"\nnearPixel=24,11\nphysicalFootprintRaysQualified=5\nactualCentreRayEnvelopesEnumerated=1\ncorridor="<<oracle.corridorLow<<","<<oracle.corridorHigh<<"\nallowedEuclideanPath="<<oracle.pathLow<<","<<oracle.pathHigh
            <<"\nviewRayNorm="<<oracle.rayNormMinimum<<","<<oracle.rayNormMaximum<<"\nreachableFirstBracketCellIntervals="<<oracle.cells.size()<<"\nfinalSourceCellIntervals="<<oracle.reachableCells
            <<"\nedgeMin="<<oracle.edgeMinimum<<"\nconfidenceMin="<<oracle.confidenceMinimum<<"\nresidualMax="<<oracle.maximumResidual<<"\nsourceMin="<<oracle.sourceMinimum
            <<"\nindependentRedLower="<<oracle.redLower<<"\nactualOriginalC0Delta="<<delta<<"\nnumericalBound="<<bound<<"\nactualObservedPath="<<path<<"\nbehavioralPass="<<passed
            <<"\nQualified actual bound C4/depth readback, original VS/FS, independent biased-origin/NEAREST/sign-corridor/Beer lower bound.\nNot actual terrain, natural image acceptance, generic SSR radiometry or Minecraft FPS.\n";
        textFile(artifacts/"NEAR-SUMMARY.txt",report.str());std::cout<<report.str();
        if(!passed)throw std::runtime_error("RED qualified underwater first visible near-wall reflection misses independent positive gain/path bound");
        // ONE closed-geometry negative: black is the first physical reflected
        // receiver; an independently camera-visible red background must not
        // leak through it. Qualification never depends on SSR path or C0.
        const auto blockedBoxes=frozenBlackFirst(in);std::vector<float> blockedDepth(count,1),blockedSource=blackImage;
        for(int y=0;y<in.height;++y)for(int x=0;x<in.width;++x){const auto hit=firstHit(blockedBoxes,in.eye,ray(in,(x+.5)/in.width,(y+.5)/in.height));if(!hit.valid)continue;const int pixel=y*in.width+x;
            blockedDepth[pixel]=float(project(in,hit.point)[2]);qualify(blockedDepth[pixel]>0&&blockedDepth[pixel]<.999999,"blocked depth is not representable");if(hit.id==1)blockedSource[pixel*4]=.75f;}
        (void)qualifyBlackFirst(in,blockedBoxes,blockedSource,blockedDepth,{position[target],position[target+1],position[target+2]},{normal[target],normal[target+1],normal[target+2]});
        const auto blockedBase=draw(3.25,zeroField,blockedDepth,blackImage,false,"black-first-zero-original"),blockedTag=draw(3.25,zeroField,blockedDepth,blockedSource,false,"black-first-tag-original"),
            blockedRepeat=draw(3.25,zeroField,blockedDepth,blockedSource,false,"black-first-tag-repeat"),blockedBaseState=draw(3.25,zeroField,blockedDepth,blackImage,true,"black-first-zero-observer"),
            blockedTagState=draw(3.25,zeroField,blockedDepth,blockedSource,true,"black-first-tag-observer");
        qualify(maxDifference(blockedTag.output[0],blockedRepeat.output[0])==0,"black-first original whole-image repeat differs");
        for(const auto& pair:std::array<std::pair<const Capture*,const Capture*>,2>{{{&blockedBase,&blockedBaseState},{&blockedTag,&blockedTagState}}})for(size_t i=0;i<pair.first->output[0].size();++i){const double a=pair.first->output[0][i],b=pair.second->output[0][i];
            qualify(std::abs(a-b)<=storageRoundoff(c0Format,a)+storageRoundoff(c0Format,b)+arithmeticBound(std::abs(a)+std::abs(b)),"black-first STORE observer is not whole-image neutral");}
        for(int pixel=0;pixel<count;++pixel){qualify(blockedBase.output[0][pixel*4+3]==1&&blockedTag.output[0][pixel*4+3]==1,"black-first water coverage/alpha differs");
            for(int c=0;c<3;++c)qualify(blockedBase.output[0][pixel*4+c]==0,"black-first zero source is not isolated");}
        const auto& blockedPosition=blockedTagState.output[3];const auto& blockedNormal=blockedTagState.output[1];
        qualify(blockedNormal[target+3]==1&&blockedTagState.output[2][target+3]==0,"black-first actual source is not TIR-isolated");
        const size_t visibleRed=qualifyBlackFirst(in,blockedBoxes,actualBoundColour,actualBoundDepth,{blockedPosition[target],blockedPosition[target+1],blockedPosition[target+2]},
            {blockedNormal[target],blockedNormal[target+1],blockedNormal[target+2]});
        std::ostringstream negative;negative<<std::setprecision(15)<<"scope=one closed black-FIRST red-BACKGROUND native129 negative\nnearPixel=24,11\nphysicalFootprintRaysQualified=5\nactualVisibleRedFullFootprints="<<visibleRed
            <<"\nActual C4/depth readback, original/store whole-image neutral and repeat; no SSR-path qualification.\n";
        bool blockedPass=true;for(int c=0;c<3;++c){const double gain=blockedTag.output[0][target+c]-blockedBase.output[0][target+c];
            const double allowed=storageRoundoff(c0Format,blockedTag.output[0][target+c])+storageRoundoff(c0Format,blockedBase.output[0][target+c])
                +arithmeticBound(std::abs(double(blockedTag.output[0][target+c]))+std::abs(double(blockedBase.output[0][target+c]))+.75,512);
            negative<<"channel="<<c<<" delta="<<gain<<" expected=0 bound="<<allowed<<"\n";if(std::abs(gain)>allowed)blockedPass=false;}
        negative<<"behavioralPass="<<blockedPass<<"\nNot a general silhouette/offscreen correctness or natural-image acceptance claim.\n";
        textFile(artifacts/"BLACK-FIRST-SUMMARY.txt",negative.str());std::cout<<negative.str();
        if(!blockedPass)throw std::runtime_error("RED qualified underwater black-FIRST receiver leaks red BACKGROUND");
        std::cout<<"PASS qualified bounded underwater near-wall original-main response; natural appearance remains unaccepted\n";return;
    }
    results.flush();qualify(bool(results),"cannot save angular results");
    std::ostringstream summary;summary<<std::setprecision(14)<<"scope="<<(in.supplied?"supplied-four-matrix resampled-NDC native replay":"declared native-only 100deg vertical-up fixture")
        <<"\ngrid="<<in.width<<"x"<<in.height<<"\nsourceSize="<<in.sourceWidth<<"x"<<in.sourceHeight<<"\nqualifiedTransmitting="<<qualified<<"\nqualifiedTIR="<<tirCount
        <<"\ninViewport="<<inViewport<<"\noffViewport="<<offViewport<<"\nmaxAbsoluteC0AngularError="<<maximumError<<"\nwrongIndexControlMargin="<<wrongOracleError
        <<"\nrotatedMarkerControlMargin="<<rotatedError<<"\nreflectionPixel="<<reflectionPixel%in.width<<","<<reflectionPixel/in.width<<"\nangularMapPass="<<(!failed)
        <<"\nOriginal VS/FS main retained; only WAVE_HEIGHT0/SHORE_FOAM0 and passive final STOREs.\n"
        <<"Independent double matrix/Snell/Fresnel/TIR oracle and fixed input-only pixel grid.\n"
        <<"Bound: source-cell angular Lipschitz error + actual LUT storage error + declared raster/gamma rounding. Not a universal driver transcendental theorem.\n"
        <<"C0 source convention follows retained underwater sky path; this is NOT reverse air-to-water radiance-unit calibration.\n"
        <<"Not actual terrain/PNG/same-frame Iris replay, Minecraft FPS, wave-rim quality, offscreen occlusion, natural underwater acceptance or full-goal completion.\n";
    textFile(artifacts/"SUMMARY.txt",summary.str());std::cout<<summary.str();
    if(failed)throw std::runtime_error("RED production underwater flat angular map exceeds independent bound");
    std::cout<<"PASS bounded original-main underwater angular map; natural appearance remains unaccepted\n";
}
#endif
