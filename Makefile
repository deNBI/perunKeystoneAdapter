lint:
	flake8 --ignore=E501 denbi/ test

test:
	docker-compose -f .docker-keystone.yml up -d
	# Sleep until the container is ready
	bash -c 'while true; do docker-compose -f .docker-keystone.yml logs --tail=10 | grep "exited: keystone-bootstrap"; ec=$$?; if ((ec==0)); then break; else echo -n .; sleep 1; fi; done;'
	# Then start testing
	-python -m unittest test.test_keystone.TestKeystone
	-python -m unittest test.test_endpoint.TestEndpoint
	docker-compose -f .docker-keystone.yml kill
	docker-compose -f .docker-keystone.yml rm -f


.PHONY: lint test
