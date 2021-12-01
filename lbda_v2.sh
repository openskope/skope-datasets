mkdir -p lbda_v2/pmdi/geoserver

if ! [ -f lbda_v2/lbda-v2_kddm_pmdi_2017.nc ]; then
  curl https://www.ncei.noaa.gov/pub/data/paleo/drought/LBDP-v2/lbda-v2_kddm_pmdi_2017.nc --output lbda_v2/lbda-v2_kddm_pmdi_2017.nc
fi

N=30
(
  for year in {0001..2017}; do
    ((i=i%N)); ((i++==0)) && wait
    if [ -f "lbda_v2/pmdi/geoserver/lbda_v2_pmdi_$year.tif" ]
    then
      continue
    else
      let band=$((10#$year))+1; gdal_translate lbda_v2/lbda-v2_kddm_pmdi_2017.nc lbda_v2/pmdi/geoserver/lbda_v2_pmdi_$year.tif -b $band -a_srs EPSG:4326 -of COG -co BLOCKSIZE=128 -co OVERVIEWS=NONE -co COMPRESS=DEFLATE --config GDAL_PAM_ENABLED NO -q &
    fi
  done
)

gdalbuildvrt -separate lbda_v2/pmdi/cube.vrt lbda_v2/pmdi/geoserver/lbda_v2_pmdi_*.tif
gdal_translate -co BIGTIFF=YES -co TILED=YES -co BLOCKXSIZE=16 -co BLOCKYSIZE=16 -co COMPRESS=DEFLATE -co NUM_THREADS=ALL_CPUS --config GDAL_PAM_ENABLED NO lbda_v2/pmdi/cube.vrt lbda_v2/pmdi/cube.tif

cp styles/pmdi.sld lbda_v2/pmdi/geoserver/pmdi.sld

#python main.py geoserver load --host https://geoserver.openskope.org --workspace SKOPE --geoserver-base-path /projects/skope/datasets/lbda_v2/pmdi/geoserver --base-path /projects/skope/datasets/lbda_v2/pmdi/geoserver
