.PHONY: build check
build:
	python3 tools/build.py
build/glcheck: tools/glcheck.cpp
	mkdir -p build
	g++ -std=c++17 -O2 -Wall -Wextra tools/glcheck.cpp -o build/glcheck -lepoxy -lEGL
check: build/glcheck
	build/glcheck shaders
