/* Leaflet map. The magnifying glass (Benjamin Becquet, MIT) shows the
   biodiversity potential layer at a closer zoom than the basemap. */
(function () {
  var BASEMAPS = {
    light: {
      url: "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
      options: {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: "abcd",
        maxZoom: 20
      }
    },
    satellite: {
      url: "https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2023_3857/default/g/{z}/{y}/{x}.jpg",
      options: {
        attribution: 'Sentinel-2 cloudless &copy; <a href="https://s2maps.eu/">EOX</a> (contains modified Copernicus Sentinel data 2023)',
        maxZoom: 19,
        maxNativeZoom: 16
      }
    }
  };

  var map;
  var glass;
  var potential;
  var config;
  var grid;
  var mainTiles;
  var glassTiles;
  var cityLayer = null;
  var activePlace = null;
  var pointerInside = false;
  var lastContainerPoint = null;
  var glassOn = true;

  var EMPTY_TILE = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7";

  function tileLayer(name) {
    var spec = BASEMAPS[name];
    return L.tileLayer(spec.url, spec.options);
  }

  function syncGlassLayers() {
    var layers = [glassTiles];
    if (cityLayer) layers.push(cityLayer);
    layers.push(potential);
    glass.options.layers = layers;
  }

  function setCityTiles(url) {
    var glassMap = glassOn && map.hasLayer(glass) ? glass.getMap() : null;
    if (cityLayer && glassMap) glassMap.removeLayer(cityLayer);
    cityLayer = null;
    if (url) {
      cityLayer = L.tileLayer(url, {
        opacity: 1,
        maxZoom: 19,
        maxNativeZoom: 18,
        errorTileUrl: EMPTY_TILE
      });
      if (glassMap) cityLayer.addTo(glassMap);
    }
    syncGlassLayers();
    if (glassMap) raisePotential();
  }

  function indexClass(score) {
    if (score < 15) return "Low";
    if (score < 30) return "Limited";
    if (score < 45) return "Moderate";
    if (score < 65) return "High";
    return "Very high";
  }

  function sampleScore(latitude, longitude) {
    if (!grid) return null;
    var bng = OSGB.wgs84ToBng(latitude, longitude);
    var easting = bng[0];
    var northing = bng[1];
    var column = Math.floor((easting - grid.origin_easting) / grid.cell_m);
    var row = Math.floor((grid.origin_northing + grid.size_m - northing) / grid.cell_m);
    if (column < 0 || row < 0 || column >= grid.width || row >= grid.height) return null;
    var value = grid.values[row * grid.width + column];
    if (value < 0) return null;
    return { score: value, easting: easting, northing: northing };
  }

  function nearestSample(easting, northing) {
    var best = null;
    var bestDistance = 8;
    config.layer.samples.forEach(function (sample) {
      var distance = Math.hypot(sample.easting - easting, sample.northing - northing);
      if (distance <= bestDistance) {
        best = sample;
        bestDistance = distance;
      }
    });
    return best;
  }

  function glassZoom() {
    var offset = glass.options.zoomOffset;
    return Math.min(map.getMaxZoom(), map.getZoom() + offset);
  }

  function updateZoomNote() {
    var note = document.getElementById("zoom-note");
    if (!glassOn) {
      note.textContent = "The glass is hidden. The basemap stays in view.";
      return;
    }
    var closer = glass.options.zoomOffset;
    if (closer === 0) {
      note.textContent = "The glass is at the same zoom as the map, so it works as a window onto the index.";
    } else {
      note.textContent = "The glass is " + closer + " zoom " + (closer === 1 ? "level" : "levels") + " closer than the map.";
    }
  }

  function updateReadout(latlng) {
    var scoreEl = document.getElementById("score");
    var classEl = document.getElementById("class-name");
    var placeEl = document.getElementById("place");
    if (!glassOn) {
      scoreEl.textContent = "—";
      classEl.textContent = "Magnifying glass is off";
      placeEl.textContent = "";
      updateZoomNote();
      return;
    }
    if (!grid) {
      scoreEl.textContent = "…";
      classEl.textContent = "Loading the index";
      placeEl.textContent = "";
      return;
    }
    var reading = sampleScore(latlng.lat, latlng.lng);
    if (!reading) {
      scoreEl.textContent = "—";
      if (activePlace && activePlace.tiles) {
        classEl.textContent = activePlace.title;
        placeEl.textContent = "The index for this city is drawn in the glass.";
      } else {
        classEl.textContent = "No index on this ground";
        placeEl.textContent = "";
      }
      updateZoomNote();
      return;
    }
    scoreEl.textContent = reading.score.toFixed(2);
    classEl.textContent = indexClass(reading.score);
    var named = nearestSample(reading.easting, reading.northing);
    placeEl.textContent = named ? named.name : "";
    updateZoomNote();
  }

  function currentLatLng() {
    if (pointerInside && lastContainerPoint) {
      return map.containerPointToLatLng(lastContainerPoint);
    }
    var stored = glass.options.latLng;
    if (stored) return L.latLng(stored);
    return map.getCenter();
  }

  function moveGlass(latlng, layerPoint) {
    if (!glassOn || !map.hasLayer(glass)) return;
    glass.setLatLng(latlng, layerPoint);
    updateReadout(latlng);
  }

  function raisePotential() {
    if (potential && potential._map) potential.bringToFront();
  }

  function onGlassAdded() {
    if (!glass._wrapperElt.querySelector(".lens-hair")) {
      L.DomUtil.create("div", "lens-hair", glass._wrapperElt);
    }
    if (glassTiles) {
      glassTiles.off("load", raisePotential);
      glassTiles.on("load", raisePotential);
    }
    raisePotential();
    var glassMap = glass.getMap();
    glassMap.off("zoomend", raisePotential);
    glassMap.on("zoomend", raisePotential);
  }

  function setBasemap(name) {
    if (mainTiles) map.removeLayer(mainTiles);
    mainTiles = tileLayer(name).addTo(map);
    var replacement = tileLayer(name);
    if (glassOn && map.hasLayer(glass)) {
      glass.getMap().removeLayer(glassTiles);
      replacement.addTo(glass.getMap());
    }
    glassTiles = replacement;
    syncGlassLayers();
    if (cityLayer && glassOn && map.hasLayer(glass)) cityLayer.bringToFront();
    if (glassOn && map.hasLayer(glass)) onGlassAdded();
    document.getElementById("basemap-light").setAttribute("aria-pressed", name === "light" ? "true" : "false");
    document.getElementById("basemap-satellite").setAttribute("aria-pressed", name === "satellite" ? "true" : "false");
  }

  function setGlassVisible(visible) {
    glassOn = visible;
    var button = document.getElementById("toggle");
    if (visible) {
      if (!map.hasLayer(glass)) glass.addTo(map);
      button.textContent = "Hide magnifying glass";
      button.setAttribute("aria-pressed", "true");
      moveGlass(currentLatLng());
    } else if (map.hasLayer(glass)) {
      map.removeLayer(glass);
      button.textContent = "Show magnifying glass";
      button.setAttribute("aria-pressed", "false");
      updateReadout(map.getCenter());
    }
  }

  function initMap(manifest) {
    config = manifest;
    var layer = manifest.layer;
    map = L.map("map", {
      zoomControl: true,
      minZoom: 6,
      maxZoom: 19
    });
    map.attributionControl.addAttribution(
      '<a href="https://github.com/domusight/biodiversity">Biodiversity potential</a>'
    );
    mainTiles = tileLayer("light").addTo(map);
    map.setView(layer.center, layer.zoom);

    L.circle(layer.aoi_center, {
      radius: layer.radius_m,
      color: "#f4f1ea",
      weight: 5,
      opacity: 0.95,
      fill: false,
      interactive: false
    }).addTo(map);
    L.circle(layer.aoi_center, {
      radius: layer.radius_m,
      color: "#0c3b2e",
      weight: 2,
      dashArray: "5 6",
      fill: false,
      interactive: false
    }).addTo(map);

    glassTiles = tileLayer("light");
    potential = L.imageOverlay(layer.image, layer.bounds, { opacity: 1, interactive: false });
    glass = L.magnifyingGlass({
      radius: Number(document.getElementById("radius").value),
      zoomOffset: Number(document.getElementById("zoom-offset").value),
      latLng: layer.lens,
      layers: [glassTiles, potential]
    });
    map.on("layeradd", function (event) {
      if (event.layer === glass) onGlassAdded();
    });
    glass.addTo(map);

    map.on("mouseover", function () { pointerInside = true; });
    map.on("mouseout", function () { pointerInside = false; });
    map.on("mousemove", function (event) {
      lastContainerPoint = event.containerPoint;
      moveGlass(event.latlng, event.layerPoint);
    });
    map.on("zoom", function () {
      if (!pointerInside) return;
      moveGlass(currentLatLng());
    });
    map.on("move", function () {
      if (pointerInside) return;
      moveGlass(map.getCenter());
    });

    document.getElementById("zoom-offset").addEventListener("input", function (event) {
      glass.options.zoomOffset = Number(event.target.value);
      document.getElementById("zoom-readout").textContent = event.target.value;
      moveGlass(currentLatLng());
    });
    document.getElementById("radius").addEventListener("input", function (event) {
      var radius = Number(event.target.value);
      document.getElementById("radius-readout").textContent = String(radius);
      glass.setRadius(radius);
      if (glass.getMap()) glass.getMap().invalidateSize();
      moveGlass(currentLatLng());
    });
    document.getElementById("toggle").addEventListener("click", function () {
      setGlassVisible(!glassOn);
    });
    document.getElementById("basemap-light").addEventListener("click", function () {
      setBasemap("light");
    });
    document.getElementById("basemap-satellite").addEventListener("click", function () {
      setBasemap("satellite");
    });

    var places = document.getElementById("places");
    activePlace = manifest.places[0];
    manifest.places.forEach(function (place) {
      var button = document.createElement("button");
      button.type = "button";
      button.textContent = place.title;
      button.addEventListener("click", function () {
        activePlace = place;
        pointerInside = false;
        setCityTiles(place.tiles || null);
        map.flyTo([place.lat, place.lon], place.zoom);
        moveGlass(map.getCenter());
      });
      places.appendChild(button);
    });

    document.getElementById("toggle").setAttribute("aria-pressed", "true");
    moveGlass(L.latLng(layer.lens));
    updateZoomNote();
  }

  function fail(message) {
    document.getElementById("score").textContent = "—";
    document.getElementById("class-name").textContent = message;
  }

  document.addEventListener("DOMContentLoaded", function () {
    fetch("data/layers.json")
      .then(function (response) {
        if (!response.ok) throw new Error("layers");
        return response.json();
      })
      .then(function (manifest) {
        initMap(manifest);
        return fetch(manifest.layer.index);
      })
      .then(function (response) {
        if (!response.ok) throw new Error("index");
        return response.json();
      })
      .then(function (index) {
        grid = index;
        updateReadout(currentLatLng());
      })
      .catch(function () {
        fail("The index layer did not load. Serve this folder over HTTP and reload.");
      });
  });
})();
