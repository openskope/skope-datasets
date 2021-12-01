<?xml version="1.0" encoding="UTF-8"?><sld:StyledLayerDescriptor xmlns="http://www.opengis.net/sld" xmlns:sld="http://www.opengis.net/sld" xmlns:gml="http://www.opengis.net/gml" xmlns:ogc="http://www.opengis.net/ogc" version="1.0.0">
  <sld:NamedLayer>
    <sld:Name>PaleoCAR V3 Precipitation Annual</sld:Name>
    <sld:UserStyle>
      <sld:Name>PaleoCAR V3 Precipitation Annual</sld:Name>
      <sld:Title>PaleoCAR V3 Precipitation Annual</sld:Title>
      <sld:FeatureTypeStyle>
        <sld:Name>name</sld:Name>
        <sld:Rule>
          <sld:RasterSymbolizer>
            <sld:ColorMap type="intervals" extended="true">
              <sld:ColorMapEntry color="#8c510a" quantity="100" opacity="${env('opacity',1.0)}" label="&lt; 100 mm"/>
              <sld:ColorMapEntry color="#bf812d" quantity="150" opacity="${env('opacity',1.0)}" label="100–150"/>
              <sld:ColorMapEntry color="#dfc27d" quantity="200" opacity="${env('opacity',1.0)}" label="150–200"/>
              <sld:ColorMapEntry color="#f6e8c3" quantity="250" opacity="${env('opacity',1.0)}" label="200–250"/>
              
              <sld:ColorMapEntry color="#c7eae5" quantity="300" opacity="${env('opacity',1.0)}" label="250–300"/>
              <sld:ColorMapEntry color="#80cdc1" quantity="350" opacity="${env('opacity',1.0)}" label="300–350"/>
              <sld:ColorMapEntry color="#35978f" quantity="400" opacity="${env('opacity',1.0)}" label="350–400"/>
              <sld:ColorMapEntry color="#01665e" quantity="65000" opacity="${env('opacity',1.0)}" label="&gt; 400 mm"/>
            </sld:ColorMap>
            <sld:ContrastEnhancement/>
          </sld:RasterSymbolizer>
        </sld:Rule>
      </sld:FeatureTypeStyle>
    </sld:UserStyle>
  </sld:NamedLayer>
</sld:StyledLayerDescriptor>
