.PHONY: help clean install dev-install self-install build publish format try-format test docs lock


help:  ## display this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n\nTargets:\n"} \
	/^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%17s\033[0m  %s\n", $$1, $$2 }' $(MAKEFILE_LIST)


clean:  ## clean all temp files
	rm -rf $$(sed '/# -/q' .gitignore | sed '/^\s*#/d ; /^\s*$$/d')
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete


install:  ## install requirements
	python -m pip install --upgrade pip
	python -m pip install -r requirements.lock


dev-install:  ## install dev requirements
	python -m pip install --upgrade pip
	python -m pip install -r dev-requirements.txt


self-install:  ## install the package locally
	python setup.py install


build: ## build wheel package
	python setup.py sdist bdist_wheel


publish:  ## publish the package on PyPI
	twine check dist/*
	twine upload --skip-existing dist/*


format:  ## format code with black
	python -m black .


try-format:  ## try to format code with black
	python -m black --check .


test:  ## test code with unit tests
	python -m pytest tests/


try-test:  ## try test code with unit tests
	python -m pytest -x --pdb tests/


smoke-test:  ## test smoke code with unit tests
	python -m pytest smoke_tests/


try-smoke-test:  ## try smoke test code with unit tests
	python -m pytest -x --pdb smoke_tests/


docs:  ## generate documentation in HTML
	sphinx-apidoc -f -o docs/api/ notion/
	sphinx-build -b dirhtml docs/ public/


lock:  ## lock all dependency versions
	python -m pip freeze | xargs pip uninstall -y
	python -m pip install --upgrade -r requirements.txt
	python -m pip freeze > requirements.lock

