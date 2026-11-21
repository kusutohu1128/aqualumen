.PHONY: build check
build:
	python3 tools/build.py
build/glcheck: tools/glcheck.cpp tools/solar-radiometry-probe.h tools/solar-cloud-probe.h tools/water-optical-depth-probe.h tools/bathymetry-gradient-probe.h
	mkdir -p build
	g++ -std=c++17 -O2 -Wall -Wextra tools/glcheck.cpp -o build/glcheck -lepoxy -lEGL
check: build/glcheck
	build/glcheck shaders
