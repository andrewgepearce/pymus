.PHONY: venv install-dev run format lint build install-global reinstall-global uninstall-global clean

venv:
	python3 -m venv .venv

install-dev: venv
	. .venv/bin/activate && pip install -U pip && pip install -e .

run:
	. .venv/bin/activate && pymus

format:
	. .venv/bin/activate && black src tests

lint:
	. .venv/bin/activate && ruff src tests

build:
	python -m build

install-global:
	pipx install .

reinstall-global:
	pipx reinstall .

uninstall-global:
	pipx uninstall pymus

clean:
	rm -rf .venv dist build *.egg-info

# Version Bump
# Add to pyproject.toml: version = "1.0.99"
# then
# make build
# make re-install-global
# git tag v1.0.99

