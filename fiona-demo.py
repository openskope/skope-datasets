import rasterio
import fiona
from rasterio.mask import raster_geometry_mask
import numpy as np

def summarize_tif(region='100km2', stat=np.ma.mean):
    with fiona.open('https://raw.githubusercontent.com/openskope/skope-datasets/main/geometries/'+region+'.geojson') as meve:
        meve = [feature["geometry"] for feature in meve]

    with rasterio.open('paleocar_v2/ppt_water_year/cube.tif') as dataset:
        # mask values outside of region
        masked, transform, window = raster_geometry_mask(dataset=dataset, shapes=meve, crop=True, all_touched=True)
        # read masked data
        data = dataset.read(indexes=np.arange(1, dataset.count, 1).tolist(), window=window)
        # mask missing values as well from stats
        values = np.ma.array(data=data, mask=np.logical_or(np.equal(data, dataset.nodata), masked))
        return stat(values, axis=(1, 2)).data