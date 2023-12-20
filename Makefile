help:
	@egrep '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-16s\033[0m %s\n", $$1, $$2}'

lint: ## Lint all python code with flake8
	python -m flake8 --ignore=E501,W503 denbi/ test

test: ## Run tests without docker
	-python -m unittest test.test_keystone.TestKeystone
	-python -m unittest test.test_endpoint.TestEndpoint

.PHONY: help lint test
