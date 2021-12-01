
mkdir -p paleocar_v2/raw

for long in {103..115} 
    do
    for lat in {32..42}
        do
        echo paleocar_v2/raw/$long\W$lat\N_GDD.nc4
        if ! [ -f "paleocar_v2/raw/$long\W$lat\N_GDD.nc4" ]; then
            curl https://www1.ncdc.noaa.gov/pub/data/paleo/treering/reconstructions/northamerica/usa/bocinsky2016/$long\W$lat\N_GDD.nc4 --output paleocar_v2/raw/$long\W$lat\N_GDD.nc4
        fi
        if ! [ -f "paleocar_v2/raw/$long\W$lat\N_PPT.nc4" ]; then
            curl https://www1.ncdc.noaa.gov/pub/data/paleo/treering/reconstructions/northamerica/usa/bocinsky2016/$long\W$lat\N_PPT.nc4 --output paleocar_v2/raw/$long\W$lat\N_PPT.nc4
        fi
        done
    done


## ppt_water_year
mkdir -p paleocar_v2/ppt_water_year/geoserver
gdalbuildvrt -a_srs EPSG:4326 -srcnodata -32768 paleocar_v2/ppt_water_year/cube.vrt paleocar_v2/raw/*PPT.nc4
gdal_translate -ot Int16 -co BIGTIFF=YES -co TILED=YES -co BLOCKXSIZE=16 -co BLOCKYSIZE=16 -co COMPRESS=DEFLATE -co NUM_THREADS=ALL_CPUS --config GDAL_PAM_ENABLED NO paleocar_v2/ppt_water_year/cube.vrt paleocar_v2/ppt_water_year/cube.tif

N=$(($(nproc --all)-2))
(
  for year in {0001..2000}; do
    ((i=i%N)); ((i++==0)) && wait
    # echo "paleocar_v2/ppt_water_year/geoserver/paleocar_v2_ppt_water_year_$year.tif"
    if [ -f "paleocar_v2/ppt_water_year/geoserver/paleocar_v2_ppt_water_year_$year.tif" ]
    then
      continue
    else
      let band=$((10#$year)); gdal_translate paleocar_v2/ppt_water_year/cube.tif paleocar_v2/ppt_water_year/geoserver/paleocar_v2_ppt_water_year_$year.tif -b $band -of COG -ot Int16 -co BLOCKSIZE=128 -co OVERVIEWS=NONE -co COMPRESS=DEFLATE -q &
    fi
  done
)

## gdd_may_sept
mkdir -p paleocar_v2/gdd_may_sept/geoserver
gdalbuildvrt -a_srs EPSG:4326 -srcnodata -32768 paleocar_v2/gdd_may_sept/cube.vrt paleocar_v2/raw/*GDD.nc4
gdal_translate -ot Int16 -co BIGTIFF=YES -co TILED=YES -co BLOCKXSIZE=16 -co BLOCKYSIZE=16 -co COMPRESS=DEFLATE -co NUM_THREADS=ALL_CPUS --config GDAL_PAM_ENABLED NO paleocar_v2/gdd_may_sept/cube.vrt paleocar_v2/gdd_may_sept/cube.tif

(
  for year in {0001..2000}; do
    ((i=i%N)); ((i++==0)) && wait
    # echo "paleocar_v2/gdd_may_sept/geoserver/paleocar_v2_gdd_may_sept_$year.tif"
    if [ -f "paleocar_v2/gdd_may_sept/geoserver/paleocar_v2_gdd_may_sept_$year.tif" ]
    then
      continue
    else
      let band=$((10#$year)); gdal_translate paleocar_v2/gdd_may_sept/cube.tif paleocar_v2/gdd_may_sept/geoserver/paleocar_v2_gdd_may_sept_$year.tif -b $band -of COG -ot Int16 -co BLOCKSIZE=128 -co OVERVIEWS=NONE -co COMPRESS=DEFLATE -q &
    fi
  done
)


## maize_farming_niche
#mkdir -p paleocar_v2/maize_farming_niche/geoserver
#
#gdal_translate -ot Int16 -co BIGTIFF=YES -co TILED=NO --config GDAL_PAM_ENABLED NO paleocar_v2/ppt_water_year/cube.tif paleocar_v2/maize_farming_niche/ppt.tif
#gdal_translate -ot Int16 -co BIGTIFF=YES -co TILED=NO --config GDAL_PAM_ENABLED NO paleocar_v2/gdd_may_sept/cube.tif paleocar_v2/maize_farming_niche/gdd.tif
#
#gdal_calc.py -A paleocar_v2/maize_farming_niche/ppt.tif -B paleocar_v2/maize_farming_niche/gdd.tif --allBands=A --allBands=B --outfile=paleocar_v2/maize_farming_niche/niche.tif --calc="(A>=300)*(B>=1800)" --type=Byte --creation-option BIGTIFF=YES --creation-option TILED=NO --overwrite
#
#gdal_translate -ot Byte -co BIGTIFF=YES -co TILED=YES -co BLOCKXSIZE=16 -co BLOCKYSIZE=16 -co COMPRESS=DEFLATE -co NUM_THREADS=ALL_CPUS --config GDAL_PAM_ENABLED NO paleocar_v2/maize_farming_niche/niche.tif paleocar_v2/maize_farming_niche/cube.tif
#
#rm paleocar_v2/maize_farming_niche/ppt.tif
#rm paleocar_v2/maize_farming_niche/gdd.tif
#rm paleocar_v2/maize_farming_niche/niche.tif
#
#(
#  for year in {0001..2000}; do
#    ((i=i%N)); ((i++==0)) && wait
#    # echo "paleocar_v2/maize_farming_niche/geoserver/paleocar_v2_maize_farming_niche_$year.tif"
#    if [ -f "paleocar_v2/maize_farming_niche/geoserver/paleocar_v2_maize_farming_niche_$year.tif" ]
#    then
#      continue
#    else
#      let band=$((10#$year)); gdal_translate paleocar_v2/maize_farming_niche/cube.tif paleocar_v2/maize_farming_niche/geoserver/paleocar_v2_maize_farming_niche_$year.tif -b $band -of COG -ot Byte -co BLOCKSIZE=128 -co OVERVIEWS=NONE -co COMPRESS=DEFLATE -q &
#    fi
#  done
#)

rsync -razhv paleocar_v2/ppt_water_year skope_staging:/projects/skope/datasets/paleocar_v2/
rsync -razhv paleocar_v2/gdd_may_sept skope_staging:/projects/skope/datasets/paleocar_v2/
# rsync -razhv paleocar_v2/maize_farming_niche skope_staging:/projects/skope/datasets/paleocar_v2/

#python main.py geoserver load --host https://geoserver.openskope.org --workspace SKOPE --geoserver-base-path /projects/skope/datasets/paleocar_v2/ppt_water_year/geoserver --base-path /projects/skope/datasets/paleocar_v2/ppt_water_year/geoserver
#python main.py geoserver load --host https://geoserver.openskope.org --workspace SKOPE --geoserver-base-path /projects/skope/datasets/paleocar_v2/gdd_may_sept/geoserver --base-path /projects/skope/datasets/paleocar_v2/gdd_may_sept/geoserver
#python main.py geoserver load --host https://geoserver.openskope.org --workspace SKOPE --geoserver-base-path /projects/skope/datasets/paleocar_v2/maize_farming_niche/geoserver --base-path /projects/skope/datasets/paleocar_v2/maize_farming_niche/geoserver