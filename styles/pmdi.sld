<?xml version="1.0" encoding="UTF-8"?><sld:StyledLayerDescriptor xmlns="http://www.opengis.net/sld" xmlns:sld="http://www.opengis.net/sld" xmlns:gml="http://www.opengis.net/gml" xmlns:ogc="http://www.opengis.net/ogc" version="1.0.0">
  <sld:NamedLayer>
    <sld:Name>Default Styler</sld:Name>
    <sld:UserStyle>
      <sld:Name>Default Styler</sld:Name>
      <sld:Title>Palmer Drought Severity Index</sld:Title>
      <sld:FeatureTypeStyle>
        <sld:Name>name</sld:Name>
        <sld:Rule>
          <sld:RasterSymbolizer>
            <sld:ColorMap type="intervals" extended="true">
              <sld:ColorMapEntry color="#660000" opacity="${env('opacity',1.0)}" quantity="-5.0" label="Exceptional Drought"/>
              <sld:ColorMapEntry color="#ff0000" opacity="${env('opacity',1.0)}" quantity="-4.0" label="Extreme Drought"/>
              <sld:ColorMapEntry color="#ff6600" opacity="${env('opacity',1.0)}" quantity="-3.0" label="Severe Drought"/>
              <sld:ColorMapEntry color="#ffcc99" opacity="${env('opacity',1.0)}" quantity="-2.0" label="Moderate Drought"/>
              <sld:ColorMapEntry color="#fdff00" opacity="${env('opacity',1.0)}" quantity="-1.0" label="Abnormally Dry"/>
              <sld:ColorMapEntry color="#000000" opacity="${env('opacity',1.0)/5}" quantity="1.0" label="Normal Conditions"/>
              <sld:ColorMapEntry color="#aaff55" opacity="${env('opacity',1.0)}" quantity="2.0" label="Abnormally Wet"/>
              <sld:ColorMapEntry color="#01ffff" opacity="${env('opacity',1.0)}" quantity="3.0" label="Moderate Wet"/>
              <sld:ColorMapEntry color="#00aaff" opacity="${env('opacity',1.0)}" quantity="4.0" label="Severe Wet"/>
              <sld:ColorMapEntry color="#0000ff" opacity="${env('opacity',1.0)}" quantity="5.0" label="Extreme Wet"/>
              <sld:ColorMapEntry color="#0000aa" opacity="${env('opacity',1.0)}" quantity="100" label="Exceptional Wet"/>
            </sld:ColorMap>
            <sld:ContrastEnhancement/>
          </sld:RasterSymbolizer>
        </sld:Rule>
      </sld:FeatureTypeStyle>
    </sld:UserStyle>
  </sld:NamedLayer>
</sld:StyledLayerDescriptor>
