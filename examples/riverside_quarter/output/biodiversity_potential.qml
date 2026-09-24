<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis version="3.28.0" styleCategories="AllStyleCategories">
  <pipe>
    <provider>
      <resampling enabled="false" maxOversampling="2" zoomedInResamplingMethod="nearestNeighbour" zoomedOutResamplingMethod="nearestNeighbour"/>
    </provider>
    <rasterrenderer opacity="1" alphaBand="-1" band="1" type="singlebandpseudocolor" classificationMin="0" classificationMax="100" nodataColor="">
      <rasterTransparency/>
      <minMaxOrigin>
        <limits>None</limits>
        <extent>WholeRaster</extent>
        <statAccuracy>Estimated</statAccuracy>
        <cumulativeCutLower>0.02</cumulativeCutLower>
        <cumulativeCutUpper>0.98</cumulativeCutUpper>
        <stdDevFactor>2</stdDevFactor>
      </minMaxOrigin>
      <rastershader>
        <colorrampshader minimumValue="0" maximumValue="100" colorRampType="DISCRETE" classificationMode="1" clip="0">
          <colorramp type="gradient" name="[source]">
            <Option type="QString" name="color1" value="237,248,233,255"/>
            <Option type="QString" name="color2" value="0,90,50,255"/>
          </colorramp>
          <item alpha="255" value="0.5" label="0–0.5" color="#edf8e9"/>
          <item alpha="255" value="3" label="0.5–3" color="#c7e9c0"/>
          <item alpha="255" value="5" label="3–5" color="#a1d99b"/>
          <item alpha="255" value="10" label="5–10" color="#74c476"/>
          <item alpha="255" value="45" label="10–45" color="#41ab5d"/>
          <item alpha="255" value="85" label="45–85" color="#238b45"/>
          <item alpha="255" value="100" label="85–100" color="#005a32"/>
        </colorrampshader>
      </rastershader>
    </rasterrenderer>
    <brightnesscontrast brightness="0" contrast="0" gamma="1"/>
    <huesaturation colorizeGreen="128" colorizeOn="0" colorizeRed="255" colorizeBlue="128" grayscaleMode="0" saturation="0"/>
    <rasterresampler maxOversampling="2"/>
  </pipe>
  <blendMode>0</blendMode>
</qgis>
