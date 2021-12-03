library(magrittr)

get_nps_unit <- function(unit){
  "https://services.arcgis.com/P3ePLMYs2RVChkJx/ArcGIS/rest/services/USA_Protected_Areas_Fee_Manager/FeatureServer/0/query" %>%
    httr::modify_url(
      query = list(
        f = "json",
        where = paste0("Unit_Nm='",unit,"'"),
        returnGeometry = "true"
      )
    ) %>%
    sf::read_sf() %>%
    sf::st_transform(4326) 
}

get_nps_unit("Mesa Verde National Park") %>%
  sf::st_geometry() %>%
  sf::write_sf("meve.geojson", delete_dsn=TRUE)

get_nps_unit("Chaco Culture National Historical Park") %>%
  sf::st_geometry() %>%
  sf::write_sf("chaco.geojson", delete_dsn=TRUE)

get_nps_unit("Bandelier National Monument") %>%
  sf::st_geometry() %>%
  sf::write_sf("band.geojson", delete_dsn=TRUE)

get_nps_unit("Hopi") %>%
  sf::st_geometry() %>%
  sf::write_sf("hopi.geojson", delete_dsn=TRUE)

sf::read_sf("ltvtp_hohokam.geojson") %>%
  sf::st_geometry() %>%
  sf::write_sf("ltvtp_hohokam.geojson", delete_dsn=TRUE)

sf::read_sf("~/Dropbox/NRG Ag Model/data-raw/Study Area Boundary/") %>%
  sf::st_transform(4326) %>%
  sf::st_geometry() %>%
  sf::write_sf("davis_nrg.geojson", delete_dsn=TRUE)

sf::read_sf("vepii_nrg.geojson") %>%
  sf::st_area() %>%
  units::set_units("km^2")