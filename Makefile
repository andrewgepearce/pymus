# ==============================================================================
# pymus Makefile
#
# Goals:
#  - Provide "npm scripts"-style commands committed to git.
#  - Support local development in a repo venv.
#  - Support global installs via pipx (isolated, yet on PATH).
#  - Support building release artifacts (wheel/sdist).
#  - Keep cleaning safe and predictable.
#
# Usage examples:
#  make install-dev     # create .venv + editable install of pymus
#  make run             # run pymus from .venv
#  make format          # format with Black
#  make lint            # lint with Ruff (if installed)
#  make build           # create dist/*.whl and dist/*.tar.gz
#  make install-global  # pipx install . (first time)
#  make reinstall-global# pipx reinstall . (after changes/version bump)
#  make clean           # remove venv + build artifacts + caches
# ==============================================================================

# Use bash so we can "source" the venv activation script.
SHELL := /bin/bash

# Path to local virtual environment for dev.
VENV := .venv

# Python executable to use for venv creation / tooling.
PYTHON := python3

# Convenience vars for running commands inside the venv.
PIP := $(VENV)/bin/pip
PY  := $(VENV)/bin/python
RUN := $(VENV)/bin/pymus

# Default target when someone runs just "make".
.DEFAULT_GOAL := help

# Mark these targets as phony so make doesn't confuse them with files.
.PHONY: help venv install-dev reinstall-dev run format lint check build \
        install-global reinstall-global uninstall-global clean clean-build \
        clean-cache

# ------------------------------------------------------------------------------
# Help: print a tidy list of targets
# ------------------------------------------------------------------------------
help:
	@echo ""
	@echo "pymus Makefile targets:"
	@echo "  make venv              Create a local dev virtualenv ($(VENV))"
	@echo "  make install-dev       Install pymus editable + deps into $(VENV)"
	@echo "  make reinstall-dev     Reinstall editable (use after deps change)"
	@echo "  make run               Run pymus from local venv"
	@echo "  make format            Format code with Black"
	@echo "  make lint              Lint code with Ruff (optional)"
	@echo "  make check             Format check + lint (CI-style)"
	@echo "  make build             Build wheel + sdist into dist/"
	@echo "  make install-global    Install pymus globally via pipx"
	@echo "  make reinstall-global  Reinstall global pipx package after changes"
	@echo "  make uninstall-global  Uninstall global pipx package"
	@echo "  make clean             Remove venv + build + caches"
	@echo ""

# ------------------------------------------------------------------------------
# Create local venv (idempotent)
# ------------------------------------------------------------------------------
venv:
	@if [ ! -d "$(VENV)" ]; then \
		echo "Creating virtualenv at $(VENV)"; \
		$(PYTHON) -m venv $(VENV); \
	else \
		echo "Virtualenv already exists at $(VENV)"; \
	fi

# ------------------------------------------------------------------------------
# Install for local development
#  - Upgrades pip tooling
#  - Installs project in editable mode: changes in src/ reflect immediately
# ------------------------------------------------------------------------------
install-dev: venv
	@echo "Upgrading pip/setuptools/wheel in $(VENV)"
	@$(PIP) install -U pip setuptools wheel
	@echo "Installing pymus editable + dev tools into $(VENV)"
	@$(PIP) install -e ".[dev]"

# Same as install-dev, but useful when you changed dependencies and want a reset.
reinstall-dev: install-dev

# ------------------------------------------------------------------------------
# Run locally from venv
# ------------------------------------------------------------------------------
run: venv
	@# Ensure deps installed; if not, this will fail with clear error.
	@echo "Running pymus from $(VENV)"
	@$(RUN)

# ------------------------------------------------------------------------------
# Format with Black
# Assumes Black is installed in the venv (either via deps or dev tools).
# If you keep Black global, you can change to "black src".
# ------------------------------------------------------------------------------
format: install-dev
	@echo "Formatting with Black"
	@$(PY) -m black src

# ------------------------------------------------------------------------------
# Lint with Ruff (optional but recommended)
# If Ruff isn't installed, this will error. Install via:
#   $(PIP) install ruff
# or add it to pyproject optional dev deps.
# ------------------------------------------------------------------------------
lint: install-dev
	@echo "Linting with Ruff"
	@$(PY) -m ruff check src

# CI-style combined checks (no auto-fixing)
check: install-dev
	@echo "Black check (no changes)"
	@$(PY) -m black --check src
	@echo "Ruff lint"
	@$(PY) -m ruff check src

# ------------------------------------------------------------------------------
# Build distributables (wheel + sdist)
# Requires "build" module installed in venv:
#   $(PIP) install build
# This is like "npm pack" or preparing a release.
# ------------------------------------------------------------------------------
build: venv clean-build
	@echo "Building wheel + sdist into dist/"
	@$(PY) -m build

# ------------------------------------------------------------------------------
# Global install / reinstall using pipx
# pipx keeps pymus in an isolated env but exposes "pymus" on PATH.
# Install pipx once via:
#   brew install pipx
#   pipx ensurepath
# ------------------------------------------------------------------------------
install-global:
	@echo "Installing pymus globally via pipx"
	@pipx install .

reinstall-global:
	@echo "Reinstalling global pipx package"
	@pipx reinstall .

uninstall-global:
	@echo "Uninstalling global pipx package"
	@pipx uninstall pymus

# ------------------------------------------------------------------------------
# Cleaning
# ------------------------------------------------------------------------------
clean: clean-build clean-cache
	@echo "Removing local venv"
	@rm -rf $(VENV)

clean-build:
	@echo "Removing build artifacts"
	@rm -rf dist build *.egg-info

clean-cache:
	@echo "Removing Python/tool caches"
	@rm -rf __pycache__ .pytest_cache .ruff_cache .mypy_cache .coverage htmlcov

# End Makefile
