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



as_proj <- function(x){
  x %>%
    {paste0("+",names(.),"=",., collapse = " ")}
}

vep3_projection <-
  list(proj = "omerc",
       lat_0 = 36.998981,
       lonc = -109.045189,
       alpha = 0,
       gamma = 0,
       k_0 = 1,
       x_0 = 0,
       y_0 = 0,
       units = "km"
  ) %>%
  as_proj() %>%
  sf::st_crs()

sf::st_bbox(c(xmin = 0,
              xmax = 10,
              ymin = 0,
              ymax = 10), 
            crs = vep3_projection) %>%
  sf::st_as_sfc() %>%
  sf::st_transform(4326) %>%
  sf::write_sf("100km2.geojson", delete_dsn=TRUE)

sf::st_bbox(c(xmin = 0,
              xmax = sqrt(1000),
              ymin = 0,
              ymax = sqrt(1000)), 
            crs = vep3_projection) %>%
  sf::st_as_sfc() %>%
  sf::st_transform(4326) %>%
  sf::write_sf("1000km2.geojson", delete_dsn=TRUE)

sf::st_bbox(c(xmin = 0,
              xmax = 100,
              ymin = 0,
              ymax = 100), 
            crs = vep3_projection) %>%
  sf::st_as_sfc() %>%
  sf::st_transform(4326) %>%
  sf::write_sf("10000km2.geojson", delete_dsn=TRUE)

sf::st_bbox(c(xmin = 0,
              xmax = sqrt(20000),
              ymin = 0,
              ymax = sqrt(20000)), 
            crs = vep3_projection) %>%
  sf::st_as_sfc() %>%
  sf::st_transform(4326) %>%
  sf::write_sf("20000km2.geojson", delete_dsn=TRUE)

sf::st_bbox(c(xmin = 0,
              xmax = sqrt(40000),
              ymin = 0,
              ymax = sqrt(40000)), 
            crs = vep3_projection) %>%
  sf::st_as_sfc() %>%
  sf::st_transform(4326) %>%
  sf::write_sf("40000km2.geojson", delete_dsn=TRUE)



  
