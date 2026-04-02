import os
import tempfile
import json
import pystac
import yaml
from osgeo import gdal
from datetime import datetime, timezone
from rio_stac.stac import create_stac_item
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta

gdal.UseExceptions()
gdal.SetCacheMax(4608 * 1024 * 1024) # 4.5 GB
gdal.SetConfigOption("GDAL_NUM_THREADS", "ALL_CPUS")

# --- Set parameters ---
input_dir = "data.nosync"
dataset_name = "paleocar_v3"
metadata_file_path = "../skope-api/timeseries/app/metadata.yml"
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

def singular_to_plural_for_relativedelta(time_delta):
    """Converts singular keys (e.g., 'year') to plural keys (e.g., 'years') for relativedelta."""
    return {k + 's' if not k.endswith('s') else k: v for k, v in time_delta.items()}

# -----------------------------------------------------------------------------------------------------------------
# Update/Validate Metadata
def load_and_verify_metadata(metadata_file_path, dataset_name):
    """Loads YAML metadata and verifies the dataset exists."""
    print(f"Loading metadata from {metadata_file_path}")
    if not os.path.exists(metadata_file_path):
        raise ValueError(f"Metadata file not found at: {metadata_file_path}")
        
    with open(metadata_file_path, "r") as f:
        yaml_content = yaml.safe_load(f) or []

    meta_by_id = {item.get("id"): item for item in yaml_content if isinstance(item, dict)} if isinstance(yaml_content, list) else {}
    ds_meta = meta_by_id.get(dataset_name)

    if ds_meta is None:
        raise ValueError(f"Dataset '{dataset_name}' not found in metadata file. Cannot proceed.")

    return yaml_content, ds_meta

def validate_else_add_timespan(ds_meta, start_dt, time_delta):
    """Validates user-provided time variables against metadata, adding to metadata if missing."""
    updated = False
    
    # Ensure nested dictionaries exist
    if "timespan" not in ds_meta: ds_meta["timespan"] = {}
    if "period" not in ds_meta["timespan"]: ds_meta["timespan"]["period"] = {}
    if "resolution" not in ds_meta["timespan"]: ds_meta["timespan"]["resolution"] = {}

    # 1. Validate Start Time (gte)
    expected_gte = get_iso_key(start_dt, time_delta)
    meta_gte = ds_meta["timespan"]["period"].get("gte")
    
    if meta_gte is None:
        print(f"Metadata missing start time (gte). Adding user-provided start time: {expected_gte}")
        ds_meta["timespan"]["period"]["gte"] = expected_gte
        updated = True
    elif str(meta_gte) != expected_gte:
        raise ValueError(f"Start time mismatch! User: {expected_gte}, Meta: {meta_gte}")

    # 2. Validate Time Delta (resolution)
    meta_res = ds_meta["timespan"]["resolution"]
    
    if not meta_res: 
        print(f"Metadata missing resolution. Adding user-provided value.")
        for k, v in time_delta.items():
            meta_res[k] = v
        updated = True
    else:
        user_delta = relativedelta(**time_delta)
        plural_meta_res = singular_to_plural_for_relativedelta(meta_res)
        meta_delta = relativedelta(**plural_meta_res)

        if user_delta != meta_delta:
            raise ValueError(f"Time delta mismatch! User: {time_delta}, Meta: {meta_res}")
            
    return updated

def validate_else_add_extracted_info(ds_meta, var_name, c_extra):
    """Validates actual data extracted from the COG against metadata, adding if missing."""
    updated = False
    
    # 1. CRS
    m_crs = ds_meta.get("crs")
    extracted_crs = f"EPSG:{c_extra.get('proj:epsg')}" if c_extra.get("proj:epsg") else None
    if m_crs is None and extracted_crs:
        print("Metadata missing CRS. Adding extracted CRS.")
        ds_meta["crs"] = extracted_crs
        updated = True
    elif m_crs and extracted_crs and m_crs.upper() != extracted_crs.upper():
        raise ValueError(f"CRS mismatch! Meta: {m_crs}, Data: {extracted_crs}")
        
    # 2. Transform (Compare first 6 elements rounded to 5 decimals)
    m_trans = ds_meta.get("transform")
    c_trans = c_extra.get("proj:transform")
    if m_trans is None and c_trans:
        print("Metadata missing Transform. Adding extracted Transform.")
        ds_meta["transform"] = c_trans
        updated = True
    elif m_trans and c_trans:
        if not all(round(m, 5) == round(d, 5) for m, d in zip(m_trans[:6], c_trans[:6])):
            raise ValueError(f"Transform mismatch!\nMeta: {m_trans[:6]}\nData: {c_trans[:6]}")
    
    # 3. Min/Max
    if "variables" not in ds_meta: ds_meta["variables"] = []
    var_meta = next((v for v in ds_meta["variables"] if v.get("id") == var_name), None)
    
    if var_meta is None:
        raise ValueError(f"Metadata missing variable entry for '{var_name}'.")

    c_min, c_max = c_extra.get("titiler:min"), c_extra.get("titiler:max")
    
    if var_meta.get("min") is None and c_min is not None:
        print(f"Metadata missing min for {var_name}. Adding extracted min.")
        var_meta["min"] = float(c_min)
        updated = True
    elif var_meta.get("min") is not None and c_min is not None and abs(var_meta["min"] - c_min) > 0.001:
        raise ValueError(f"Min mismatch for {var_name}! Meta: {var_meta['min']}, Data: {c_min}")

    if var_meta.get("max") is None and c_max is not None:
        print(f"Metadata missing max for {var_name}. Adding extracted max.")
        var_meta["max"] = float(c_max)
        updated = True
    elif var_meta.get("max") is not None and c_max is not None and abs(var_meta["max"] - c_max) > 0.001:
        raise ValueError(f"Max mismatch for {var_name}! Meta: {var_meta['max']}, Data: {c_max}")

    return updated

# -----------------------------------------------------------------------------------------------------------------



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

# -----------------------------------------------------------------------------------------------------------------

dataset_time_delta = singular_to_plural_for_relativedelta(dataset_time_delta)

yaml_content, ds_meta = load_and_verify_metadata(metadata_file_path, dataset_name)
any_metadata_updated = validate_else_add_timespan(ds_meta, dataset_start_datetime, dataset_time_delta)

input_paths = [os.path.join(input_dir, f) for f in os.listdir(input_dir) if f.endswith(".tif") and not f.endswith("_cogd.tif")]

output_dir = os.path.join(input_dir, dataset_name)
root_cogs_dir = os.path.join(output_dir, "cogs")
stac_dir = os.path.join(output_dir, "stac")
os.makedirs(root_cogs_dir, exist_ok=True)
os.makedirs(stac_dir, exist_ok=True)

# Initialize the STAC Catalog and lookup dictionary
catalog_desc = ds_meta.get("description", f"STAC Catalog for {dataset_name} dataset.")
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

    process_variable(
        paths_dict,
        collection,
        lookup_dict,
        window=max_bands_per_slice,
        trunc=trunc_to_uint16,
        start_dt=dataset_start_datetime,
        time_delta=dataset_time_delta
    )

    updated_extracted = validate_else_add_extracted_info(ds_meta, var_name, collection.extra_fields)
    any_metadata_updated = any_metadata_updated or updated_extracted

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

if any_metadata_updated:
    print(f"Saving updated metadata back to {metadata_file_path}")
    with open(metadata_file_path, "w") as f:
        yaml.dump(yaml_content, f, default_flow_style=False, sort_keys=False)

print(f"Done! Tree generated in {stac_dir} and {root_cogs_dir}")
print(f"Lookup Dictionary generated at {lookup_file_path}")
