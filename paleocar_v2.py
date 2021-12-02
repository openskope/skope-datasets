import rasterio
import fiona
from rasterio.mask import mask
from rasterio.windows import Window
import numpy as np
import pandas as pd

with fiona.open('meve.geojson') as meve:
    meve = [feature["geometry"] for feature in meve]

dataset = rasterio.open('data-derived/PPT_water_year/0001.tif')
meve_rast = mask(dataset,
                 shapes=meve,
                 all_touched=True,
                 crop=True)[0].astype(float)
meve_rast[meve_rast == -32768] = np.nan
meve_mean = np.nanmean(meve_rast, axis=(1,2))
meve_median = np.nanmedian(meve_rast, axis=(1,2))

with fiona.open('four_corners.geojson') as four_corners:
    four_corners = [feature["geometry"] for feature in four_corners]
four_corners_rast = mask(dataset,
                         shapes=four_corners,
                         all_touched=True,
                         crop=True)[0].astype(float)
four_corners_rast[four_corners_rast == -32768] = np.nan
four_corners_mean = np.nanmean(four_corners_rast, axis=(1,2))

# This is what the timeseries service is doing
py, px = dataset.index(-109.04519, 36.99898) # This returns row, col
data = dataset.read(1, window=Window(px, py, 1, 1), out_dtype=np.float64).flatten() # Window expects col, row! (Line 88 of datasets.py)

dataset.close()

pd.DataFrame({'year': np.arange(1,2005,1),
             'four_corners': four_corners_mean.astype(int),
             'meve_mean': meve_mean,
             'meve_median': meve_median.astype(int)}).\
    to_csv("paleocar_v2.csv")