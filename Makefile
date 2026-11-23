.PHONY: build check check-development check-entity check-bounce check-door check-film check-leaves check-lava check-canopy check-ground check-animal check-ceiling check-eye
build:
	python3 tools/build.py
build/glcheck: tools/ceiling-light-probe.h tools/animal-light-probe.h tools/ground-return-probe.h tools/canopy-sky-probe.h tools/water-world-reflection-probe.h tools/receiver-source-probe.h tools/receiver-run-probe.h tools/receiver-plant-dda-probe.h
build/glcheck: tools/water-reflection-normal-probe.h tools/local-lights-probe.h tools/carried-lights-probe.h tools/lamp-display-probe.h
build/glcheck: tools/entity-light-probe.h tools/bounce-light-probe.h tools/door-light-probe.h tools/rain-film-probe.h tools/leaf-light-probe.h tools/lava-light-probe.h tools/lava-idle-probe.h
build/glcheck: tools/glcheck.cpp tools/display-glare-probe.h tools/solar-tir-footprint-probe.h tools/solar-radiometry-probe.h tools/solar-cloud-probe.h tools/water-optical-depth-probe.h tools/bathymetry-gradient-probe.h tools/water-radiance-probe.h tools/underwater-angular-probe.h tools/underwater-backface-probe.h
	mkdir -p build
	g++ -std=c++17 -O2 -Wall -Wextra tools/glcheck.cpp -o build/glcheck -lepoxy -lEGL
build/rain-shelter-probe: tools/rain-shelter-probe.cpp
	mkdir -p build
	g++ -std=c++17 -O2 -Wall -Wextra $< -o $@ -lepoxy -lEGL
check: build/glcheck build/rain-shelter-probe
	build/glcheck release/shaders --play-release
	build/rain-shelter-probe release/shaders build/rain-shelter-latest.json
check-development: build/glcheck
	build/glcheck shaders
# Standalone entity-light QA; ENTITY_SHADERS defaults to the release tree (errors when it ships no entity pass).
ENTITY_SHADERS ?= release/shaders
check-entity: build/glcheck
	build/glcheck $(ENTITY_SHADERS) --entity-light-probe
# Standalone one-bounce QA; BOUNCE_SHADERS defaults to the release tree (errors when it ships no bounce pass).
BOUNCE_SHADERS ?= release/shaders
check-bounce: build/glcheck
	build/glcheck $(BOUNCE_SHADERS) --bounce-light-probe
# Standalone door-panel light-transmission QA (native GPU oracle); DOOR_SHADERS defaults to the release tree.
DOOR_SHADERS ?= release/shaders
check-door: build/glcheck
	build/glcheck $(DOOR_SHADERS) --door-light-probe
# Standalone rain-film optics QA (native GPU oracle); FILM_SHADERS defaults to the release tree. Dedicated: PENDING API parts fail.
FILM_SHADERS ?= release/shaders
check-film: build/glcheck
	build/glcheck $(FILM_SHADERS) --rain-film-probe
LEAF_SHADERS ?= release/shaders
check-leaves: build/glcheck
	build/glcheck $(LEAF_SHADERS) --leaf-light-probe
# Standalone lava area-light QA (actual fluid quads -> shadow_solid -> shadowcomp1 -> lampLighting) against an
# independent area integral. Optional LAVA_BASELINE = an unpacked lamp-only pack (e.g. dist/Aqualumen-1.8.0.zip)
# adds the lava-free equality check. With no explicit source, test the actual preview archive against stable.
LAVA_SHADERS ?=
LAVA_BASELINE ?=
check-lava: build/glcheck
ifneq ($(strip $(LAVA_SHADERS)),)
	build/glcheck $(LAVA_SHADERS) --lava-light-probe $(LAVA_BASELINE)
else
	@set -eu; stage=$$(mktemp -d build/lava-check.XXXXXX); trap 'rm -rf -- "$$stage"' EXIT; \
	python3 tools/build.py --lava-preview --output "$$stage/pack.zip"; \
	python3 -m zipfile -e "$$stage/pack.zip" "$$stage"; \
	build/glcheck "$$stage/shaders" --lava-light-probe "$(if $(LAVA_BASELINE),$(LAVA_BASELINE),release/shaders)"
endif

# Check the shipped directional sky solver on constant and two-colour skies,
# with open air, opaque walls, foliage, dyed glass, and a camera grid crossing.
check-canopy: build/glcheck
	@set -eu; stage=$$(mktemp -d build/canopy-check.XXXXXX); trap 'rm -rf -- "$$stage"' EXIT; \
	python3 tools/build.py --canopy-preview --output "$$stage/pack.zip"; \
	python3 -m zipfile -e "$$stage/pack.zip" "$$stage"; \
	build/glcheck "$$stage/shaders" --canopy-sky-probe

# Compare nearby daylight return with an independent area integral in a synthetic scene.
check-ground: build/glcheck
	@set -eu; stage=$$(mktemp -d build/ground-check.XXXXXX); trap 'rm -rf -- "$$stage"' EXIT; \
	python3 tools/build.py --ground-preview --output "$$stage/pack.zip"; \
	python3 -m zipfile -e "$$stage/pack.zip" "$$stage"; \
	build/glcheck "$$stage/shaders" --ground-return-probe

# Exercise the shipping vertex stage on off-grid, rotating animal surfaces.
check-animal: build/glcheck
	@set -eu; stage=$$(mktemp -d build/animal-check.XXXXXX); trap 'rm -rf -- "$$stage"' EXIT; \
	python3 tools/build.py --animal-preview --output "$$stage/pack.zip"; \
	python3 -m zipfile -e "$$stage/pack.zip" "$$stage"; \
	build/glcheck "$$stage/shaders" --animal-light-probe

check-ceiling: build/glcheck
	@set -eu; stage=$$(mktemp -d build/ceiling-check.XXXXXX); trap 'rm -rf -- "$$stage"' EXIT; \
	python3 tools/build.py --ceiling-preview --output "$$stage/pack.zip"; \
	python3 -m zipfile -e "$$stage/pack.zip" "$$stage"; \
	build/glcheck "$$stage/shaders" --ceiling-light-probe

check-eye: build/glcheck
	@set -eu; stage=$$(mktemp -d build/eye-check.XXXXXX); trap 'rm -rf -- "$$stage"' EXIT; \
	python3 tools/build.py --eye-preview --output "$$stage/pack.zip"; \
	python3 -m zipfile -e "$$stage/pack.zip" "$$stage"; \
	build/glcheck "$$stage/shaders" --eye-exposure-probe

.PHONY: check-face
check-face: build/glcheck
	@set -eu; stage=$$(mktemp -d build/face-check.XXXXXX); trap 'rm -rf -- "$$stage"' EXIT; \
	python3 tools/build.py --eye-preview --output "$$stage/reference.zip"; \
	python3 tools/build.py --face-preview --output "$$stage/candidate.zip"; \
	python3 -m zipfile -e "$$stage/reference.zip" "$$stage/reference"; \
	python3 -m zipfile -e "$$stage/candidate.zip" "$$stage/candidate"; \
	build/glcheck "$$stage/reference/shaders" --ceiling-light-probe "$$stage/candidate/shaders"
