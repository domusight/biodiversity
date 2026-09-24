.PHONY: test example plugin-zip

test:
	python3 -m pytest

plugin-zip:
	rm -f qgis/biodiversity_potential-0.1.0.zip
	cd qgis && zip -r biodiversity_potential-0.1.0.zip biodiversity_potential -x '*__pycache__*' '*.pyc'

example:
	python3 examples/riverside_quarter/build_example.py
	python3 web/build_example_layer.py
