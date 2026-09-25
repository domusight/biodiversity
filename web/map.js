/* Leaflet map. Biodiversity potential is a translucent tile overlay. */
(function () {
  var BASEMAPS = {
    light: {
      url: "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
      options: {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19,
        pane: "basemap"
      }
    },
    satellite: {
      url: "https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2023_3857/default/g/{z}/{y}/{x}.jpg",
      options: {
        attribution: 'Sentinel-2 cloudless &copy; <a href="https://s2maps.eu/">EOX</a> (contains modified Copernicus Sentinel data 2023)',
        maxZoom: 19,
        maxNativeZoom: 16,
        pane: "imagery"
      }
    }
  };

  var EMPTY_TILE = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7";

  var map;
  var mainTiles;
  var indexLayer = null;
  var activePlace = null;

  function tileLayer(name) {
    var spec = BASEMAPS[name];
    return L.tileLayer(spec.url, spec.options);
  }

  function startingPlace(manifest) {
    var places = manifest.places || [];
    for (var i = 0; i < places.length; i++) {
      if (places[i].tiles) return places[i];
    }
    return places[0];
  }

  function setIndexTiles(url) {
    if (indexLayer) {
      map.removeLayer(indexLayer);
      indexLayer = null;
    }
    if (!url) return;
    indexLayer = L.tileLayer(url, {
      pane: "index",
      opacity: 1,
      maxZoom: 19,
      maxNativeZoom: 16,
      errorTileUrl: EMPTY_TILE
    });
    indexLayer.addTo(map);
  }

  function setBasemap(name) {
    if (mainTiles) map.removeLayer(mainTiles);
    mainTiles = tileLayer(name).addTo(map);
    if (indexLayer) indexLayer.bringToFront();
    document.getElementById("basemap-light").setAttribute("aria-pressed", name === "light" ? "true" : "false");
    document.getElementById("basemap-satellite").setAttribute("aria-pressed", name === "satellite" ? "true" : "false");
  }

  function showPlace(place) {
    activePlace = place;
    var title = document.getElementById("class-name");
    var detail = document.getElementById("place");
    title.textContent = place.title;
    if (place.tiles) {
      detail.textContent = "The index is the translucent green overlay.";
      setIndexTiles(place.tiles);
    } else {
      detail.textContent = "No index has been uploaded for this place.";
      setIndexTiles(null);
    }
    map.flyTo([place.lat, place.lon], place.zoom);
  }

  function initMap(manifest) {
    activePlace = startingPlace(manifest);
    map = L.map("map", {
      zoomControl: true,
      minZoom: 6,
      maxZoom: 18
    });
    map.createPane("basemap");
    map.getPane("basemap").style.zIndex = 200;
    map.getPane("basemap").style.filter = "grayscale(1)";
    map.createPane("imagery");
    map.getPane("imagery").style.zIndex = 200;
    map.createPane("index");
    map.getPane("index").style.zIndex = 450;
    map.getPane("index").style.mixBlendMode = "multiply";

    map.attributionControl.addAttribution(
      '<a href="https://github.com/domusight/biodiversity">Biodiversity potential</a>'
    );
    mainTiles = tileLayer("light").addTo(map);
    map.setView([activePlace.lat, activePlace.lon], activePlace.zoom);
    setIndexTiles(activePlace.tiles || null);

    document.getElementById("class-name").textContent = activePlace.title;
    document.getElementById("place").textContent = activePlace.tiles
      ? "The index is the translucent green overlay."
      : "No index has been uploaded for this place.";

    document.getElementById("basemap-light").addEventListener("click", function () {
      setBasemap("light");
    });
    document.getElementById("basemap-satellite").addEventListener("click", function () {
      setBasemap("satellite");
    });

    var places = document.getElementById("places");
    if (manifest.places.length > 1) {
      places.hidden = false;
      manifest.places.forEach(function (place) {
        var button = document.createElement("button");
        button.type = "button";
        button.textContent = place.title;
        button.addEventListener("click", function () {
          showPlace(place);
        });
        places.appendChild(button);
      });
    }

    var about = document.getElementById("about-more");
    var aboutToggle = document.getElementById("about-toggle");
    aboutToggle.addEventListener("click", function () {
      var open = about.hidden;
      about.hidden = !open;
      aboutToggle.textContent = open ? "Show less" : "Read more";
      aboutToggle.setAttribute("aria-expanded", open ? "true" : "false");
    });

    var legend = document.getElementById("legend");
    if (window.matchMedia("(min-width: 721px)").matches) {
      legend.open = true;
    }
  }

  function fail(message) {
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
      })
      .catch(function () {
        fail("The map did not load. Serve this folder over HTTP and reload.");
      });
  });
})();
