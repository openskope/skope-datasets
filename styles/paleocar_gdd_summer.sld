<?xml version="1.0" encoding="UTF-8"?><sld:StyledLayerDescriptor xmlns="http://www.opengis.net/sld" xmlns:sld="http://www.opengis.net/sld" xmlns:gml="http://www.opengis.net/gml" xmlns:ogc="http://www.opengis.net/ogc" version="1.0.0">
  <sld:NamedLayer>
    <sld:Name>Default Styler</sld:Name>
    <sld:UserStyle>
      <sld:Name>Default Styler</sld:Name>
      <sld:Title>PaleoCAR color gradient</sld:Title>
      <sld:FeatureTypeStyle>
        <sld:Name>name</sld:Name>
        <sld:Rule>
          <sld:RasterSymbolizer>
            <sld:ColorMap type="intervals" extended="true">
              <sld:ColorMapEntry color="#2166ac" quantity="600" opacity="${env('opacity',1.0)}" label="&lt; 600 FGDD"/>
              <sld:ColorMapEntry color="#4393c3" quantity="1000" opacity="${env('opacity',1.0)}" label="600–1000"/>
              <sld:ColorMapEntry color="#92c5de" quantity="1400" opacity="${env('opacity',1.0)}" label="1000–1400"/>
              <sld:ColorMapEntry color="#d1e5f0" quantity="1800" opacity="${env('opacity',1.0)}" label="1400–1800"/>
              
              <sld:ColorMapEntry color="#fddbc7" quantity="2200" opacity="${env('opacity',1.0)}" label="1800–2200"/>
              <sld:ColorMapEntry color="#f4a582" quantity="2600" opacity="${env('opacity',1.0)}" label="2200–2600"/>
              <sld:ColorMapEntry color="#d6604d" quantity="3000" opacity="${env('opacity',1.0)}" label="2600–3000"/>
              <sld:ColorMapEntry color="#b2182b" quantity="65000" opacity="${env('opacity',1.0)}" label="&gt; 3000 FGDD"/>
            </sld:ColorMap>
            <sld:ContrastEnhancement/>
          </sld:RasterSymbolizer>
        </sld:Rule>
      </sld:FeatureTypeStyle>
    </sld:UserStyle>
  </sld:NamedLayer>
</sld:StyledLayerDescriptor>
