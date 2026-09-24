.PHONY: test example plugin-zip

test:
	python3 -m pytest

plugin-zip:
	rm -f qgis/biodiversity_potential-0.2.4.zip qgis/biodiversity_potential-city-0.2.4.zip
	cd qgis && zip -r biodiversity_potential-0.2.4.zip biodiversity_potential -x '*__pycache__*' '*.pyc' 'biodiversity_potential/large.py'
	cd qgis && zip -r biodiversity_potential-city-0.2.4.zip biodiversity_potential -x '*__pycache__*' '*.pyc'

example:
	python3 examples/riverside_quarter/build_example.py
	python3 web/build_example_layer.py
