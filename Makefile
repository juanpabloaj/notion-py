.PHONY: help clean install dev-install self-install build
.PHONY: publish docs serve-docs lock format try-format
.PHONY: test try-test smoke-test try-smoke-test


tests       = $(or $(word 2, $(MAKECMDGOALS)), tests/)
smoke_tests = $(or $(word 2, $(MAKECMDGOALS)), smoke_tests/)
temp_files  = $(shell sed '/\# -/q' .gitignore | cut -d'\#' -f1)


help:  ## display this help
	@awk ' \
		BEGIN { \
			FS = ":.*##"; \
			printf "Usage:\n\t make \033[36m"; \
			printf "<target>\033[0m\n\nTargets:\n"; \
		} /^[a-zA-Z_-]+:.*?##/ { \
			printf "\033[36m%17s\033[0m -%s\n", $$1, $$2; \
		}' $(MAKEFILE_LIST)


clean:  ## clean all temp files
	rm -rf $(temp_files)
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete


install:  ## install requirements
	python -m pip install -r requirements.lock


dev-install:  ## install dev requirements
	python -m pip install -r dev-requirements.txt


self-install:  ## install the package locally
	python setup.py install


build: ## build wheel package
	python setup.py sdist bdist_wheel


publish:  ## publish the package on PyPI
	twine check dist/*
	twine upload --skip-existing dist/*


docs:  ## generate documentation in HTML
	sphinx-build -b dirhtml docs/ public/


serve-docs:  ## generate and serve documentation
	python docs/serve.py


lock:  ## lock all dependency versions
	python -m pip freeze | xargs pip uninstall -y
	python -m pip install --upgrade -r requirements.txt
	python -m pip freeze > requirements.lock


format:  ## format code with black
	python -m black .


try-format:  ## try to format code with black
	python -m black --check .


test:  ## test code with unit tests
	python -m pytest -v tests/


try-test:  ## try test code with unit tests
	python -m pytest -v -x --pdb $(tests)


smoke-test:  ## test code with smoke tests
	python -m pytest -v smoke_tests/


try-smoke-test:  ## try to test code with smoke tests
	python -m pytest -v -x --pdb $(smoke_tests)
