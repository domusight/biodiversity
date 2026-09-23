.PHONY: test example

test:
	python3 -m pytest

example:
	python3 examples/riverside_quarter/build_example.py
	python3 web/build_example_layer.py
