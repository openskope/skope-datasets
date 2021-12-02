N=$(($(nproc --all)-2))

mkdir -p paleocar_v3/raw

#for long in {103..115} 
#    do
#    for lat in {31..42}
#        do
#        echo paleocar_v3/raw/$long\W$lat\N_GDD.nc4
#        if ! [ -f paleocar_v3/raw/$long\W$lat\N_GDD.nc4 ]; then
#            curl https://www1.ncdc.noaa.gov/pub/data/paleo/treering/reconstructions/northamerica/usa/bocinsky2016/$long\W$lat\N_GDD.nc4 --output paleocar_v3/raw/$long\W$lat\N_GDD.nc4
#        fi
#        echo paleocar_v3/raw/$long\W$lat\N_PPT.nc4
#        if ! [ -f paleocar_v3/raw/$long\W$lat\N_PPT.nc4 ]; then
#            curl https://www1.ncdc.noaa.gov/pub/data/paleo/treering/reconstructions/northamerica/usa/bocinsky2016/$long\W$lat\N_PPT.nc4 --output paleocar_v3/raw/$long\W$lat\N_PPT.nc4
#        fi
#        done
#    done


## ppt_water_year
echo "Building paleocar_v3 ppt_water_year dataset"

make_tifs (){
    mkdir -p paleocar_v3/$1/geoserver

        gdalbuildvrt -a_srs EPSG:4326 paleocar_v3/$1/cube.vrt paleocar_v3/raw/$1_demosaic/*prediction_scaled*.tif

    (
        for year in {0103..2000}; do
            ((i=i%N)); ((i++==0)) && wait
            # echo "paleocar_v3/$1/geoserver/paleocar_v3_ppt_water_year_$year.tif"
            if [ -f "paleocar_v3/$1/geoserver/paleocar_v3_$1_$year.tif" ]
            then
                continue
            else
                let band=$((10#$year))-102; gdal_translate paleocar_v3/$1/cube.vrt paleocar_v3/$1/geoserver/paleocar_v3_$1_$year.tif -b $band -of COG -ot UInt16 -co BLOCKSIZE=128 -co OVERVIEWS=NONE -co COMPRESS=DEFLATE -q &
            fi
        done
        )
}

make_tifs ppt_water_year
make_tifs ppt_annual
make_tifs ppt_may_sept
make_tifs gdd_may_sept

make_cubes (){
    if ! [ -f paleocar_v3/$1/cube.tif ]; then
        gdalbuildvrt -separate data-derived/paleocar/$1/cube.vrt paleocar_v3/$1/geoserver/paleocar_v3_$1_*.tif
        gdal_translate -ot UInt16 -co BIGTIFF=YES -co TILED=YES -co BLOCKXSIZE=16 -co BLOCKYSIZE=16 -co COMPRESS=DEFLATE -co NUM_THREADS=ALL_CPUS --config GDAL_PAM_ENABLED NO paleocar_v3/$1/cube.vrt paleocar_v3/$1/cube.tif
    fi
}

make_cubes ppt_water_year
make_cubes ppt_annual
make_cubes ppt_may_sept
make_cubes gdd_may_sept


## maize_farming_niche
#echo "Building paleocar_v3 maize_farming_niche dataset"
#mkdir -p paleocar_v3/maize_farming_niche/geoserver
#
#(
#  for year in {0001..2000}; do
#    ((i=i%N)); ((i++==0)) && wait
#    # echo "paleocar_v3/maize_farming_niche/geoserver/paleocar_v3_maize_farming_niche_$year.tif"
#    if [ -f "paleocar_v3/maize_farming_niche/geoserver/paleocar_v3_maize_farming_niche_$year.tif" ]
#    then
#      continue
#    else
#      let band=$((10#$year)); gdal_calc.py -A paleocar_v3/ppt_water_year/geoserver/paleocar_v3_ppt_water_year_$year.tif -B paleocar_v3/gdd_may_sept/geoserver/paleocar_v3_gdd_may_sept_$year.tif --outfile=paleocar_v3/maize_farming_niche/geoserver/temp.tif --calc="(A>=300)*(B>=1800)" --type=Byte --co TILED=YES --co BLOCKXSIZE=128 --co BLOCKYSIZE=128 --co COMPRESS=DEFLATE --overwrite --quiet; gdal_translate paleocar_v3/maize_farming_niche/geoserver/temp.tif paleocar_v3/maize_farming_niche/geoserver/paleocar_v3_maize_farming_niche_$year.tif -of COG -ot Byte -co BLOCKSIZE=128 -co OVERVIEWS=NONE -co COMPRESS=DEFLATE -q &
#    fi
#  done
#)
#
### Bash add pause prompt for 5 seconds ##
#sleep 30
#
#rm paleocar_v3/maize_farming_niche/geoserver/temp.tif

cp styles/paleocar_ppt_annual.sld paleocar_v3/ppt_water_year/geoserver/paleocar_ppt_annual.sld
cp styles/paleocar_ppt_annual.sld paleocar_v3/ppt_annual/geoserver/paleocar_ppt_annual.sld
cp styles/paleocar_ppt_annual.sld paleocar_v3/ppt_may_sept/geoserver/paleocar_ppt_annual.sld
cp styles/paleocar_gdd_summer.sld paleocar_v3/gdd_may_sept/geoserver/paleocar_gdd_summer.sld
#cp styles/paleocar_niche.sld paleocar_v3/maize_farming_niche/geoserver/paleocar_niche.sld

rsync -razhv paleocar_v3/ppt_water_year skope_staging:/projects/skope/datasets/paleocar_v3/
rsync -razhv paleocar_v3/ppt_annual skope_staging:/projects/skope/datasets/paleocar_v3/
rsync -razhv paleocar_v3/ppt_may_sept skope_staging:/projects/skope/datasets/paleocar_v3/
rsync -razhv paleocar_v3/gdd_may_sept skope_staging:/projects/skope/datasets/paleocar_v3/

#gdalbuildvrt -separate paleocar_v3/maize_farming_niche/cube.vrt paleocar_v3/maize_farming_niche/geoserver/*.tif
#gdal_translate -ot Byte -co BIGTIFF=YES -co TILED=YES -co BLOCKXSIZE=16 -co BLOCKYSIZE=16 -co COMPRESS=DEFLATE -co NUM_THREADS=ALL_CPUS --config GDAL_PAM_ENABLED NO paleocar_v3/maize_farming_niche/cube.vrt paleocar_v3/maize_farming_niche/cube.tif
#
#rsync -razhv paleocar_v3/maize_farming_niche skope_staging:/projects/skope/datasets/paleocar_v3/

#python main.py geoserver load --host https://geoserver.openskope.org --workspace SKOPE --geoserver-base-path /projects/skope/datasets/paleocar_v3/ppt_water_year/geoserver --base-path /projects/skope/datasets/paleocar_v3/ppt_water_year/geoserver
#python main.py geoserver load --host https://geoserver.openskope.org --workspace SKOPE --geoserver-base-path /projects/skope/datasets/paleocar_v3/gdd_may_sept/geoserver --base-path /projects/skope/datasets/paleocar_v3/gdd_may_sept/geoserver
#python main.py geoserver load --host https://geoserver.openskope.org --workspace SKOPE --geoserver-base-path /projects/skope/datasets/paleocar_v3/maize_farming_niche/geoserver --base-path /projects/skope/datasets/paleocar_v3/maize_farming_niche/geoserver