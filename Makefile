help:
	@egrep '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-16s\033[0m %s\n", $$1, $$2}'

lint: ## Lint all python code with flake8
	python -m flake8 --ignore=E501,W503 denbi/ test

test_docker: ## Run tests with docker-compose launch of container
	docker-compose up
	# Sleep until the container is ready
	bash -c 'while true; do docker-compose logs --tail=10 | grep "exited: keystone-bootstrap"; ec=$$?; if ((ec==0)); then break; else echo -n .; sleep 1; fi; done;'
	# Then start testing
	-python -m unittest test.test_keystone.TestKeystone
	-python -m unittest test.test_endpoint.TestEndpoint
	# Cleanup
	docker-compose kill
	docker-compose rm -f

test_tox:
	# Set environment variables for container
	#docker-compose -f  docker-compose.yml -f docker-compose.local.yml up -d
	docker-compose -f  docker-compose.yml up -d
	# Sleep until the container is ready
	bash -c 'while true; do docker-compose logs --tail=10 | grep "exited: keystone-bootstrap"; ec=$$?; if ((ec==0)); then break; else echo -n .; sleep 2; fi; done;'
	#first test it
	curl localhost:5000
	#first test other port
	curl localhost:35357
	# Then start testing
	tox
	# Cleanup
	docker-compose -f  docker-compose.yml kill
	docker-compose -f  docker-compose.yml rm -f

test: ## Run tests without docker
	-python -m unittest test.test_keystone.TestKeystone
	-python -m unittest test.test_endpoint.TestEndpoint

docs: ## Build documentation
	rm -f docs/denbi.*.rst
	sphinx-apidoc -o docs/ denbi/
	cd docs && $(MAKE) html


.PHONY: help lint test test_docker docs
