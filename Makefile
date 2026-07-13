# The Sequence Group — OpenRV studio kit
PY      ?= python3
DIST    ?= dist
SUPPORT ?=

.PHONY: help lint test packages install dev clean

help:
	@echo "Sequence RV studio kit"
	@echo ""
	@echo "  make lint      byte-compile sources and validate PACKAGE manifests"
	@echo "  make test      run unit tests (no RV required)"
	@echo "  make packages  build dist/*.rvpkg"
	@echo "  make install   install dist/*.rvpkg via rvpkg (SUPPORT=<dir>, default ~/.rv)"
	@echo "  make dev       install into ./rv-support for RV_SUPPORT_PATH testing"
	@echo "  make clean     remove build products"

lint:
	$(PY) -m compileall -q packages scripts tests
	$(PY) scripts/make_packages.py --check

test:
	$(PY) -m unittest discover -s tests -v

packages: lint
	$(PY) scripts/make_packages.py --dist $(DIST)

install: packages
	bash scripts/install_packages.sh $(SUPPORT)

dev: packages
	bash scripts/install_packages.sh rv-support

clean:
	rm -rf $(DIST) rv-support
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
