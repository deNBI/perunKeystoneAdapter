help:
	@egrep '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-16s\033[0m %s\n", $$1, $$2}'

lint: ## Lint all python code with flake8
	flake8 --ignore=E501 denbi/ test

test_docker: ## Run tests with docker-compose launch of container
	docker-compose -f .docker-keystone.yml up -d
	# Sleep until the container is ready
	bash -c 'while true; do docker-compose -f .docker-keystone.yml logs --tail=10 | grep "exited: keystone-bootstrap"; ec=$$?; if ((ec==0)); then break; else echo -n .; sleep 1; fi; done;'
	# Then start testing
	-python -m unittest test.test_keystone.TestKeystone
	-python -m unittest test.test_endpoint.TestEndpoint
	docker-compose -f .docker-keystone.yml kill
	docker-compose -f .docker-keystone.yml rm -f

test: ## Run tests without docker
	-python -m unittest test.test_keystone.TestKeystone
	-python -m unittest test.test_endpoint.TestEndpoint


.PHONY: help lint test test_docker
