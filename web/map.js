/* Leaflet map. The magnifying glass (Benjamin Becquet, MIT) shows the
   biodiversity potential layer at a closer zoom than the basemap. */
(function () {
  var BASEMAPS = {
    light: {
      url: "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
      options: {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19,
        className: "basemap-greyscale"
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
    if (potential) layers.push(potential);
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
    if (score < 0.5) return "0–0.5";
    if (score < 3) return "0.5–3";
    if (score < 5) return "3–5";
    if (score < 10) return "5–10";
    if (score < 45) return "10–45";
    if (score < 85) return "45–85";
    return "85–100";
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
    if (!config.layer || !config.layer.samples) return null;
    config.layer.samples.forEach(function (sample) {
      var distance = Math.hypot(sample.easting - easting, sample.northing - northing);
      if (distance <= bestDistance) {
        best = sample;
        bestDistance = distance;
      }
    });
    return best;
  }

  function applyLensZoom(latlng) {
    var pixelRadius = glass.options.radius;
    var zoom = Lens.zoomForRadius(latlng.lat, pixelRadius, Lens.RADIUS_M);
    zoom = Math.max(map.getMinZoom(), Math.min(map.getMaxZoom(), zoom));
    glass._fixedZoom = true;
    glass.options.fixedZoom = zoom;
    var glassMap = glass.getMap();
    if (glassMap) {
      glassMap.options.zoomSnap = 0;
      glassMap.options.zoomDelta = 0.1;
    }
  }

  function updateZoomNote() {
    var note = document.getElementById("zoom-note");
    if (!glassOn) {
      note.textContent = "The glass is hidden. The basemap stays in view.";
      return;
    }
    note.textContent = "The lens covers a 250 m radius, the neighbourhood the QGIS tool scores. Scroll the map and the lens stays at that scale.";
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

  function moveGlass(latlng) {
    if (!glassOn || !map.hasLayer(glass)) return;
    applyLensZoom(latlng);
    glass.setLatLng(latlng);
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
    glassMap.options.zoomSnap = 0;
    glassMap.options.zoomDelta = 0.1;
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

  function startingPlace(manifest) {
    var places = manifest.places || [];
    for (var i = 0; i < places.length; i++) {
      if (places[i].tiles) return places[i];
    }
    return places[0];
  }

  function initMap(manifest) {
    config = manifest;
    activePlace = startingPlace(manifest);
    map = L.map("map", {
      zoomControl: true,
      minZoom: 6,
      maxZoom: 19
    });
    map.attributionControl.addAttribution(
      '<a href="https://github.com/domusight/biodiversity">Biodiversity potential</a>'
    );
    mainTiles = tileLayer("light").addTo(map);
    map.setView([activePlace.lat, activePlace.lon], activePlace.zoom);

    glassTiles = tileLayer("light");
    potential = null;
    var pixelRadius = Number(document.getElementById("radius").value);
    glass = L.magnifyingGlass({
      radius: pixelRadius,
      fixedZoom: Lens.zoomForRadius(activePlace.lat, pixelRadius, Lens.RADIUS_M),
      latLng: [activePlace.lat, activePlace.lon],
      layers: [glassTiles]
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
    setCityTiles(activePlace.tiles || null);
    moveGlass(L.latLng(activePlace.lat, activePlace.lon));
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
        updateReadout(currentLatLng());
      })
      .catch(function () {
        fail("The index layer did not load. Serve this folder over HTTP and reload.");
      });
  });
})();
