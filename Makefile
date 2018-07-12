
.PHONY: format
format:
	black .

.PHONY: tests
tests:
	tox
