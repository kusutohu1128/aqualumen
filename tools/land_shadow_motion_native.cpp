#define main land_shadow_common_main
#include "land_shadow_native.cpp"
#undef main

constexpr int motionSteps = 512;
constexpr double motionStart = 2.9;
constexpr double motionEnd = 3.1;
constexpr double motionMaximumStep = 0.02;
constexpr double motionMonotonicTolerance = 0.00005;

struct MotionResult {
    double startVisibility, endVisibility, maximumAbsoluteStep, minimumSignedStep;
    int descendingSteps;
    bool endpointContrastPassed, monotonicPassed, maximumStepPassed;
};

MotionResult assessMotion(const std::vector<float>& visibility) {
    require(visibility.size() == motionSteps+1,"motion profile does not contain all 513 positions");
    MotionResult result{visibility.front(),visibility.back(),0,1,0,false,true,true};
    for (size_t i = 0; i < visibility.size(); ++i) {
        require(std::isfinite(visibility[i]) && visibility[i] >= -1e-6 && visibility[i] <= 1+1e-6,
                "motion visibility is not a finite unit value");
        if (i == 0) continue;
        const double change = double(visibility[i])-visibility[i-1];
        result.maximumAbsoluteStep = std::max(result.maximumAbsoluteStep,std::abs(change));
        result.minimumSignedStep = std::min(result.minimumSignedStep,change);
        if (change < -motionMonotonicTolerance) ++result.descendingSteps;
    }
    result.endpointContrastPassed = result.startVisibility <= 0.01 && result.endVisibility >= 0.99;
    result.monotonicPassed = result.descendingSteps == 0;
    result.maximumStepPassed = result.maximumAbsoluteStep <= motionMaximumStep;
    return result;
}

void motionCpuTests() {
    cpuTests();
    std::vector<float> linear(motionSteps+1);
    for (int i = 0; i <= motionSteps; ++i) linear[i] = float(i)/motionSteps;
    const auto good = assessMotion(linear);
    require(good.endpointContrastPassed && good.monotonicPassed && good.maximumStepPassed,
            "valid motion profile rejected");
    auto changed = linear;
    for (int i = 0; i <= motionSteps; ++i) changed[i] = i < motionSteps/2 ? 0.0f : 1.0f;
    require(!assessMotion(changed).maximumStepPassed,"one-step silhouette jump accepted");
    changed = linear;
    changed[motionSteps/2] -= 0.02f;
    require(!assessMotion(changed).monotonicPassed,"descending motion profile accepted");
    changed.assign(motionSteps+1,0.5f);
    require(!assessMotion(changed).endpointContrastPassed,"vacuous endpoint contrast accepted");
    changed = linear;
    changed[motionSteps/2] = std::numeric_limits<float>::quiet_NaN();
    bool refused = false;
    try { assessMotion(changed); } catch (const std::runtime_error&) { refused = true; }
    require(refused,"nonfinite motion profile accepted");
    require(std::abs(motionEnd-motionStart-0.2) < 1e-12,"motion sweep span changed");
    require(receiverSide%2 == 1,"motion probe requires an exact centre pixel");
    std::cout << "cpu_motion_positions=513\ncpu_motion_jump_mutant=rejected\n"
              << "cpu_motion_monotonic_mutant=rejected\ncpu_motion_vacuous_endpoints=rejected\n"
              << "cpu_motion_nonfinite=rejected\n";
}

std::string motionReport(const fs::path& root, const std::string& algorithm, const Context& context,
                         const MotionResult& result, int writtenTexels) {
    std::ostringstream out;
    out << std::setprecision(17)
        << "{\n  \"evidenceKind\": \"owned-native-fixed-light-receiver-translation-not-Minecraft\",\n"
        << "  \"shaderRoot\": " << json(root.string()) << ",\n  \"algorithm\": " << json(algorithm)
        << ",\n  \"renderer\": " << json(context.renderer) << ",\n  \"vendor\": " << json(context.vendor)
        << ",\n  \"version\": " << json(context.version)
        << ",\n  \"mapResolution\": 2048,\n  \"depthFormat\": \"DEPTH_COMPONENT24\",\n"
        << "  \"compareFunction\": \"LEQUAL\",\n  \"compareFilter\": \"LINEAR\",\n"
        << "  \"receiverGridResolution\": 129,\n  \"receiverGridSpanMetres\": 4,\n"
        << "  \"sampledPixelXY\": [64,64],\n  \"casterEdgeXMetres\": 3,\n"
        << "  \"casterBottomGapMetres\": 2,\n  \"casterThicknessMetres\": 0.01,\n"
        << "  \"startReceiverCentreXMetres\": " << motionStart
        << ",\n  \"endReceiverCentreXMetres\": " << motionEnd
        << ",\n  \"translationSteps\": " << motionSteps << ",\n  \"evaluatedPositions\": " << motionSteps+1
        << ",\n  \"translationStepMetres\": " << (motionEnd-motionStart)/motionSteps
        << ",\n  \"maximumAllowedAbsoluteVisibilityStep\": " << motionMaximumStep
        << ",\n  \"monotonicTolerance\": " << motionMonotonicTolerance
        << ",\n  \"writtenDepthTexels\": " << writtenTexels
        << ",\n  \"mapLightProjectionHeldFixed\": true,\n  \"mapReadbackBeforeAfterExact\": true,\n"
        << "  \"startVisibility\": " << result.startVisibility << ",\n  \"endVisibility\": " << result.endVisibility
        << ",\n  \"maximumAbsoluteVisibilityStep\": " << result.maximumAbsoluteStep
        << ",\n  \"minimumSignedVisibilityStep\": " << result.minimumSignedStep
        << ",\n  \"descendingStepsBeyondTolerance\": " << result.descendingSteps
        << ",\n  \"endpointContrastPassed\": " << (result.endpointContrastPassed?"true":"false")
        << ",\n  \"monotonicPassed\": " << (result.monotonicPassed?"true":"false")
        << ",\n  \"maximumStepPassed\": " << (result.maximumStepPassed?"true":"false")
        << ",\n  \"limitations\": [\"Fixed-light receiver translation, not dynamic Sun motion.\","
        << "\"Synthetic geometry and owned sampler state, not actual Iris appearance.\","
        << "\"The centre pixel is the motion target; other grid pixels are not an interior shadow gate.\","
        << "\"No frame-time, live performance or Minecraft FPS measurement.\"]\n}\n";
    return out.str();
}

int main(int argc, char** argv) {
    try {
        if (argc == 2 && std::string(argv[1]) == "--cpu-self-test") { motionCpuTests(); return 0; }
        require(argc == 4,"usage: land-shadow-motion-native SHADER_ROOT legacy|land NEW_OUTPUT, or --cpu-self-test");
        const fs::path root = fs::canonical(argv[1]), output = argv[3];
        const std::string algorithm = argv[2];
        require(algorithm == "legacy" || algorithm == "land","unknown algorithm");
        require(!fs::exists(output),"output directory already exists");
        require(fs::is_directory(root) && fs::is_regular_file(root/"shadow.vsh") && fs::is_regular_file(root/"shadow.fsh"),
                "shader root does not contain the caster pair");
        motionCpuTests();
        const std::string vertex = expand(root/"shadow.vsh",root), fragment = expand(root/"shadow.fsh",root);
        const std::string lookup = receiverShader(root,algorithm);
        const std::string fullscreen = "#version 330 compatibility\nvoid main(){gl_Position=gl_Vertex;}\n";
        require(fs::create_directory(output),"cannot exclusively create output directory");
        writeText(output/"caster-expanded.vsh",vertex);
        writeText(output/"caster-expanded.fsh",fragment);
        writeText(output/"receiver-expanded.fsh",lookup);
        writeText(output/"receiver.vsh",fullscreen);
        Context context;
        const GLuint caster = link(vertex,fragment,"unchanged-ordinary-caster");
        const GLuint evaluator = link(fullscreen,lookup,"selected-production-shadow-lookup");
        MotionResult result{};
        int writtenTexels = 0;
        {
            Fixture fixture(caster,evaluator);
            const Plane flat = {{0,0},0,0,6,0};
            const Scenario blocker = {"motion-fixed-solid",ContactBox{flat,2.0,0.01,3},
                                      MapKind::Rasterized,Target::FullyBlocked,true};
            fixture.rasterMap(blocker);
            const auto initialMap = fixture.readMap();
            writtenTexels = int(std::count_if(initialMap.begin(),initialMap.end(),[](float value){return value < 1;}));
            require(writtenTexels > 100,"motion caster map is vacuous");
            std::vector<float> visibility;
            std::ostringstream csv;
            csv << std::setprecision(17) << "step,requestedCentreXMetres,uniformCentreXMetres,visibility,signedVisibilityStep\n";
            for (int step = 0; step <= motionSteps; ++step) {
                const double x = motionStart+(motionEnd-motionStart)*step/motionSteps;
                Plane moving = flat;
                moving.centre.x = x;
                const Scenario sample = {"motion-receiver",Empty{moving},MapKind::Rasterized,Target::FullyLit,false};
                const auto frame = fixture.evaluate(sample);
                const float value = frame.rgba[((receiverSide/2)*receiverSide+receiverSide/2)*4];
                const double delta = visibility.empty() ? 0.0 : double(value)-visibility.back();
                csv << step << ',' << x << ',' << float(x) << ',' << value << ',' << delta << '\n';
                visibility.push_back(value);
                if (step == 0 || step == motionSteps/2 || step == motionSteps)
                    writePreview(output/("grid-step-"+std::to_string(step)+".ppm"),frame);
            }
            require(initialMap == fixture.readMap(),"shadow map changed during the fixed-light motion sweep");
            result = assessMotion(visibility);
            writeText(output/"receiver-translation.csv",csv.str());
        }
        writeText(output/"RESULT.json",motionReport(root,algorithm,context,result,writtenTexels));
        glDeleteProgram(caster);
        glDeleteProgram(evaluator);
        glOkay("motion fixture completion");
        require(result.endpointContrastPassed,"fixed-light sweep lacks shadow-to-lit endpoint contrast");
        const bool passed = result.monotonicPassed && result.maximumStepPassed;
        std::cout << "motion_endpoints=pass\nmotion_monotonic=" << (result.monotonicPassed?"pass":"red")
                  << "\nmotion_maximum_step=" << result.maximumAbsoluteStep
                  << "\nmotion_target=" << (passed?"pass":"red") << '\n';
        return algorithm == "land" && !passed ? 2 : 0;
    } catch (const std::exception& error) {
        std::cerr << "motion_fixture_invalid=" << error.what() << '\n';
        return 1;
    }
}
