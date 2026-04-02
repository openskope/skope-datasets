import os
import json
import yaml
import pystac
from osgeo import gdal
from datetime import datetime, timezone

import metadata
import stac_builder
from datetime_utils import singular_to_plural_for_relativedelta

gdal.UseExceptions()
gdal.SetCacheMax(4608 * 1024 * 1024)  # 4.5 GB
gdal.SetConfigOption("GDAL_NUM_THREADS", "ALL_CPUS")

# --- Configuration ---
input_dir = "data.nosync"
dataset_name = "paleocar_v3"
metadata_file_path = "metadata.yml"
trunc_to_uint16 = True

max_bands_per_slice = 100

dataset_start_datetime = datetime(103, 1, 1, tzinfo=timezone.utc)
dataset_time_delta = {"years": 1}  # Valid keys match dateutil.relativedelta (e.g., years, months, days, hours)
# ---------------------


dataset_time_delta = singular_to_plural_for_relativedelta(dataset_time_delta)

yaml_content, ds_meta = metadata.load_and_verify_metadata(metadata_file_path, dataset_name)
any_metadata_updated = metadata.validate_else_add_timespan(ds_meta, dataset_start_datetime, dataset_time_delta)

input_paths = [
    os.path.join(input_dir, f)
    for f in os.listdir(input_dir)
    if f.endswith(".tif") and not f.endswith("_cogd.tif")
]

output_dir = os.path.join(input_dir, dataset_name)
root_cogs_dir = os.path.join(output_dir, "cogs")
stac_dir = os.path.join(output_dir, "stac")
os.makedirs(root_cogs_dir, exist_ok=True)
os.makedirs(stac_dir, exist_ok=True)

catalog = pystac.Catalog(
    id="skope-catalog",
    description=ds_meta.get("description", f"STAC Catalog for {dataset_name} dataset."),
)
lookup_dict = {}

for input_path in input_paths:
    var_name = os.path.basename(input_path).split(".")[0]
    print(f"\nProcessing variable: {var_name}")

    cogs_var_dir = os.path.join(root_cogs_dir, var_name)
    partial_path_base = os.path.join(dataset_name, "cogs", var_name)
    os.makedirs(cogs_var_dir, exist_ok=True)

    collection = stac_builder.build_collection(var_name, dataset_start_datetime)

    stac_builder.process_variable(
        paths_dict={
            "input_path": input_path,
            "cogs_var_dir": cogs_var_dir,
            "partial_path_base": partial_path_base,
            "var_name": var_name,
        },
        stac_collection=collection,
        lookup_dict=lookup_dict,
        window=max_bands_per_slice,
        trunc=trunc_to_uint16,
        start_dt=dataset_start_datetime,
        time_delta=dataset_time_delta,
    )

    updated_extracted = metadata.validate_else_add_extracted_info(ds_meta, var_name, collection.extra_fields)
    any_metadata_updated = any_metadata_updated or updated_extracted

    collection.update_extent_from_items()
    catalog.add_child(collection)

print("\nSaving STAC Catalog")
stac_builder.save_catalog(catalog, stac_dir)

print("Saving lookup dictionary")
lookup_file_path = os.path.join(output_dir, "lookup.json")
with open(lookup_file_path, "w") as f:
    json.dump(lookup_dict, f, indent=2)

if any_metadata_updated:
    print(f"Saving updated metadata back to {metadata_file_path}")
    with open(metadata_file_path, "w") as f:
        yaml.dump(yaml_content, f, default_flow_style=False, sort_keys=False)

print(f"\nDone!")
print(f"  STAC catalog: {stac_dir}")
print(f"  COG slices:   {root_cogs_dir}")
print(f"  Lookup dict:  {lookup_file_path}")
