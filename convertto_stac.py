import os
import tempfile
import json
from datetime import datetime, timezone
from osgeo import gdal
import pystac
from rio_stac.stac import create_stac_item
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
# from pandas import DataFrame, concat

gdal.UseExceptions()
gdal.SetCacheMax(4608 * 1024 * 1024) # 4.5 GB
gdal.SetConfigOption("GDAL_NUM_THREADS", "ALL_CPUS")

# --- Step 1 & 2: Set parameters ---
input_dir = "data.nosync"
dataset_name = "paleocar_v3"
catalog_desc = "Root catalog for SKOPE paleoenvironmental data."
trunc_to_uint16 = True

max_bands_per_slice = 100

dataset_start_datetime = datetime(103, 1, 1, tzinfo=timezone.utc)
dataset_time_delta = {"years": 1} # Valid keys match dateutil.relativedelta (e.g., years, months, days, hours)

# -----------------------------------------------------------------------------------------------------------------
# Datetime helpers
def get_iso_key(dt, time_delta):
    """Returns a partially or fully ISO-8601 compliant string based on the time step resolution."""
    if any(k in time_delta for k in ["hours", "minutes", "seconds"]):
        return f"{dt.year:04d}-{dt.month:02d}-{dt.day:02d}T{dt.hour:02d}:{dt.minute:02d}:{dt.second:02d}Z"
    elif "days" in time_delta or "weeks" in time_delta:
        return f"{dt.year:04d}-{dt.month:02d}-{dt.day:02d}"
    elif "months" in time_delta:
        return f"{dt.year:04d}-{dt.month:02d}"
    else: # Default to year precision
        return f"{dt.year:04d}"

def format_stac_datetime(dt):
    """Returns a strict STAC ISO-8601 compliant string with 4-digit year padding."""
    return f"{dt.year:04d}-{dt.month:02d}-{dt.day:02d}T{dt.hour:02d}:{dt.minute:02d}:{dt.second:02d}Z"

def generate_date_range(start_dt, end_dt, step):
    """Yields datetimes from start to end (inclusive) by a given step."""
    current = start_dt
    while current <= end_dt:
        yield current
        current += step

# -----------------------------------------------------------------------------------------------------------------

def process_variable(paths_dict, stac_collection, lookup_dict, window=100, trunc=False, start_dt=None, time_delta=None):

    input_path = paths_dict["input_path"]
    cogs_var_dir = paths_dict["cogs_var_dir"]
    partial_path_base = paths_dict["partial_path_base"]
    var_name = paths_dict["var_name"]
    step = relativedelta(**time_delta)
    
    tmpfiles = []
    lookup_dict[var_name] = {}

    with gdal.Open(input_path) as ds:
        tot_bands = ds.RasterCount

    n = -(- tot_bands // window) # ceiling division
    print(f"Dividing raster into {n} slices (Max {window} bands each)")

    global_min = float('inf')
    global_max = float('-inf')
    
    for s in range(n): 
        suffx = f"{s+1}"
        cog_filename = f"{var_name}_{suffx}.tif"
        cog_file_path = os.path.join(cogs_var_dir, cog_filename)
        partial_file_path = os.path.join(partial_path_base, cog_filename)
        
        start_idx = s * window
        end_idx = min((s + 1) * window, tot_bands) - 1

        # Determine bands to extract for this slice
        start_band = start_idx + 1
        end_band_plus_1 = end_idx + 2

        slice_start_dt = start_dt + (step * start_idx)
        slice_end_dt = start_dt + (step * end_idx)

        print(f"\nProcessing slice {suffx}")
        print(f"Populating lookup dict for years {slice_start_dt} to {slice_end_dt}")

        for i, current_dt in enumerate(generate_date_range(slice_start_dt, slice_end_dt, step)):
            iso_key = get_iso_key(current_dt, time_delta)
            lookup_dict[var_name][iso_key] = {
                "file": partial_file_path,
                "bidx": i + 1
            }

        if not os.path.isfile(cog_file_path):
            with tempfile.NamedTemporaryFile(suffix=f'_{suffx}.tif', delete=False) as tmp_block:
                slice_file = tmp_block.name
                
                print(f"\nCreating slice {suffx} with bands {start_band} to {end_band_plus_1 - 1}")
                print(f"Mapped to Time Steps: {slice_start_dt} to {slice_end_dt}")

                selected_bands = ",".join(str(b) for b in range(start_band, end_band_plus_1))
                
                # 1. Select bands → write GeoTiff. 
                print("Selecting bands and writing GeoTiff file")
                trunc_data = f"set-type --datatype=UInt16 ! edit --nodata 65535 ! " if trunc else ""
                pipe_str = f"read {input_path} ! select --band={selected_bands} ! {trunc_data}\
                write {slice_file} --format GTiff --co COMPRESS=ZSTD --co TILED=YES --co BLOCKXSIZE=128 --co BLOCKYSIZE=128 --overwrite"
                gdal.Run("raster", "pipeline", pipeline=pipe_str, progress=lambda p, o, d: print(f"{p*100:.0f}% ", end="", flush=True))
                
                # 2. Convert GeoTiff slice to COG
                print("\nConverting file to COG")
                gdal.Run("raster", "convert",
                        input=slice_file,
                        output=cog_file_path,
                        output_format="COG",
                        creation_option=[
                            "BLOCKSIZE=128",
                            "COMPRESS=ZSTD", 
                            "PREDICTOR=2",
                            "OVERVIEWS=IGNORE_EXISTING",
                            "INTERLEAVE=TILE",
                            "SPARSE_OK=TRUE",
                        ],
                        overwrite=True)
            
                tmpfiles.append(slice_file)

        # 3. Generate the STAC Item for this slice 
        print(f"Generating STAC Item for {os.path.basename(cog_file_path)}")

        item = create_stac_item(
            source=cog_file_path,
            id=f"{var_name}_{s+1}",
            asset_name="data",
            asset_roles=["data"],
            asset_media_type=pystac.MediaType.COG,
            with_proj=True,
            with_raster=True
        )
        item.properties["start_datetime"] = format_stac_datetime(slice_start_dt)
        # End datetime represents the *end* of the period for the last band in this slice
        almost_one_step = step - relativedelta(seconds=1)
        item.properties["end_datetime"] = format_stac_datetime(slice_end_dt + almost_one_step)
        item.datetime = None

        # find relative path from item's json to cog asset, then save the item with that relative path
        item_dir_path = cog_file_path.replace("cogs", "stac").replace(".tif", "")
        item_json_path = os.path.join(item_dir_path, cog_filename.replace(".tif", ".json"))
        rel_cog_path = pystac.utils.make_relative_href(cog_file_path, item_json_path)
        item.assets["data"].href = rel_cog_path

        # update global min/max for collection extent
        bands = item.assets["data"].extra_fields["raster:bands"]
        for b in bands:   
            b_min = b["statistics"]["minimum"]
            b_max = b["statistics"]["maximum"]
            global_min = min(global_min, b_min)
            global_max = max(global_max, b_max)

        stac_collection.add_item(item)
        print("STAC Item attached to collection.")

    # get nodata and proj data from the last item (all items come from the same COG)
    nodata_val = item.assets["data"].extra_fields["raster:bands"][0]["nodata"]
    proj_props = item.properties

    stac_collection.extra_fields.update({
        "titiler:nodata": nodata_val,
        "titiler:min": global_min,
        "titiler:max": global_max,
        "proj:epsg": proj_props["proj:epsg"],
        "proj:geometry": proj_props["proj:geometry"],
        "proj:shape": proj_props["proj:shape"],
        "proj:transform": proj_props["proj:transform"]
    })

    # Cleanup temp files
    for tmp in tmpfiles:
        if os.path.exists(tmp):
            os.unlink(tmp)



input_paths = [os.path.join(input_dir, f) for f in os.listdir(input_dir) if f.endswith(".tif") and not f.endswith("_cogd.tif")]

output_dir = os.path.join(input_dir, dataset_name)
root_cogs_dir = os.path.join(output_dir, "cogs")
stac_dir = os.path.join(output_dir, "stac")
os.makedirs(root_cogs_dir, exist_ok=True)
os.makedirs(stac_dir, exist_ok=True)

# Initialize the STAC Catalog and lookup dictionary
catalog = pystac.Catalog(
    id="skope-catalog",
    description=catalog_desc
)

lookup_dict = {}

for input_path in input_paths:

    var_name = os.path.basename(input_path).split(".")[0]
    print(f"Processing variable: {var_name}")
    cogs_var_dir = os.path.join(root_cogs_dir, var_name)
    partial_path_base = os.path.join(dataset_name, "cogs", var_name)
    os.makedirs(cogs_var_dir, exist_ok=True)

    collection = pystac.Collection(
        id=var_name,
        description=f"Chunked COGs for the {var_name} variable.",
        extent=pystac.Extent(
            spatial=pystac.SpatialExtent([[-180.0, -90.0, 180.0, 90.0]]), # Dummy spatial and time bounds, updated later
            temporal=pystac.TemporalExtent([[
                dataset_start_datetime, 
                dataset_start_datetime + relativedelta(years=1) # dummy initialization
            ]])
        )
    )

    paths_dict = {
        "input_path": input_path,
        "cogs_var_dir": cogs_var_dir,
        "partial_path_base": partial_path_base,
        "var_name": var_name,
    }

    process_variable(paths_dict, collection, lookup_dict, window=max_bands_per_slice, trunc=trunc_to_uint16, start_dt=dataset_start_datetime, time_delta=dataset_time_delta)

    collection.update_extent_from_items()
    catalog.add_child(collection)

print("\nSaving Master STAC Catalog")
catalog.normalize_hrefs(stac_dir)
catalog.make_all_asset_hrefs_relative()
catalog.save(dest_href=stac_dir, catalog_type=pystac.CatalogType.SELF_CONTAINED)

print("Saving Master Lookup Dictionary")
lookup_file_path = os.path.join(output_dir, "lookup.json")
with open(lookup_file_path, "w") as f:
    json.dump(lookup_dict, f, indent=2)

print(f"Done! Tree generated in {stac_dir} and {root_cogs_dir}")
print(f"Lookup Dictionary generated at {lookup_file_path}")


