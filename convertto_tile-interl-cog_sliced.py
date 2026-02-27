# converts multiband GTiffs/COGs to COGs that are TILE interleaved, tiled (128x128 blocks), compressed (ZSTD pred 2), with overviews.
# needs gdal 3.12+ 

# Step 1: set input, output directories, and decide whether to truncate data type to UInt16
# script processes all input files ending with ".tif" but not "_cogd.tif" in the input directory
# output cogs are written to output_dir, with same name as input but ending in "_cogd.tif" instead of ".tif"
# comparison tables (input vs new COG) are printed to console and written to output_dir as "size_comparisons.csv" and "band_metric_comparisons.csv"

input_dir = "data"
output_dir = "data/cogs"


# Step 2: set parameters
# trunc_to_uint16: truncate data type to UInt16? set to False to keep original data type
# n_slices: number of slices to divide the input file into for intermediate COG creation
# run_sanity_checks: run comparisons between input GTiff and new COG, including validation of COG and comparison of band 
#          metrics (mean, max, min) between input and new COG
# rel_tol: relative tolerance for flagging differences in band metrics between input and COG; flagged if abs(input metric - COG metric) > tol,
#          where tol = max value in original file's band 1 * rel_tol
# n_mid_bands: number of intermediate bands to select to perform input file vs new COG comparison, in addition to the first and last bands
#          these are evenly spaced through the band range of the input. eg, n_mid_bands=1, then bands 1, middle, and last are compared.

trunc_to_uint16 = True
n_slices = 16 
run_sanity_checks = True
rel_tol = 1e-5
n_mid_bands = 1

# Step 3: run the script!

# -----------------------------------------------------------------------------------------------------------------
import os
import shutil
import tempfile
from osgeo import gdal
from rioxarray import open_rasterio
from pandas import DataFrame, concat
import rio_cogeo

gdal.UseExceptions()
gdal.SetCacheMax(4608 * 1024 * 1024) # 4.5 GB
gdal.SetConfigOption("GDAL_NUM_THREADS", "ALL_CPUS")


def slice_then_cog(input_path, cogs_dir, output_cog_name, n=16, trunc=False):
    output_path = os.path.join(cogs_dir, output_cog_name)

    # check if input file is already a valid COG with TILE interleave
    print("Checking if input file is already a valid COG with TILE interleave")
    input_valid = rio_cogeo.cog_validate(input_path, strict=True)[0]
    if input_valid:
        if rio_cogeo.cog_info(input_path).Profile["Interleave"] == "TILE":
            print(f"Input file {os.path.basename(input_path)} is already a valid COG, skipping conversion and copying it to output path: {output_path}")
            shutil.copy(input_path, output_path)
            return output_path

    # check if output COG already exists and is valid with TILE interleave
    if os.path.isfile(output_path):
        print("Output COG already exists. Checking if it is valid with TILE interleave")
        output_valid = rio_cogeo.cog_validate(output_path, strict=True)[0]
        if output_valid and rio_cogeo.cog_info(output_path).Profile["Interleave"] == "TILE":
            print(f"Final COG already exists and is valid, skipping: {output_path}")
            return output_path

    print(f"Processing file: {os.path.basename(input_path)}")
    print(f"Dividing raster into {n} slices")
    
    slice_files = []
    tmpfiles = []

    with gdal.Open(input_path) as ds:
        tot_bands = ds.RasterCount


    window = -(- tot_bands // n) # ceiling of division
    
    for s in range(n):
        suffx = f"slice_{s+1}"
        cog_file = os.path.join(cogs_dir, "slices", f"{suffx}_cogd.tif")
        if os.path.isfile(cog_file):
            print(f"Slice file already exists, skipping: {cog_file}")
            slice_files.append(cog_file)
            continue
        
        with tempfile.NamedTemporaryFile(suffix=f'_{suffx}.tif', delete=False) as tmp_block:
            slice_file = tmp_block.name
            start_band = s * window + 1
            end_band = min((s + 1) * window, tot_bands) + 1
            print(f"\nProcessing slice {s+1} with bands {start_band} to {end_band - 1}")

            selected_bands = ",".join(str(b) for b in range(start_band, end_band))
            
            # 1. Select bands → write GeoTiff. Writing the temp GeoTiff cut about 3X off the time compared to writing directly as COG.
            print("Selecting bands and writing GeoTiff file")
            trunc_data = f"set-type --datatype=UInt16 ! edit --nodata 65535 ! " if trunc else ""
            pipe_str = f"read {input_path} ! \
                    select --band={selected_bands} ! {trunc_data}\
                    write {slice_file} --format GTiff --co TILED=YES --co BLOCKXSIZE=128 --co BLOCKYSIZE=128 --overwrite"
            gdal.Run("raster", "pipeline", pipeline=pipe_str, progress=lambda p, o, d: print(f"{p*100:.0f}% ", end="", flush=True))
            
            # 2. Convert GeoTiff slice to COG
            print("\nConverting file to COG")
            gdal.Run("raster", "convert",
                    input=slice_file,
                    output=cog_file,
                    output_format="COG",
                    creation_option=["BLOCKSIZE=128", "COMPRESS=NONE", "OVERVIEWS=AUTO", "INTERLEAVE=TILE"],
                    overwrite=True)
            
            slice_files.append(cog_file)
            tmpfiles.append(slice_file)

    # Cleanup temp files
    for tmp in tmpfiles:
        os.unlink(tmp)

    # 3. Merge all COG tiles → final COG
    print("\nMerging all slices into final COG")
    files_str = " ".join(slice_files)
    input_years = str(open_rasterio(input_path, masked=True).attrs["long_name"])
    cog_pipe_str = f'stack --input={files_str} ! \
                    edit --metadata long_name="{input_years}" ! \
                    write {output_path} --format COG --co BLOCKSIZE=128 --co COMPRESS=ZSTD --co PREDICTOR=2 --co OVERVIEWS=AUTO --co INTERLEAVE=TILE --co BIGTIFF=YES --overwrite'
    gdal.Run("raster", "pipeline", pipeline=cog_pipe_str, progress=lambda p, o, d: print(f"{p*100:.0f}% ", end="", flush=True))
    
    # 4. Cleanup COG slices
    for block in slice_files:
        os.unlink(block)
        
    return output_path



# flag if greater
def fl_g(val, tol):
    return f"> tol of {tol:.4f}" if val > tol else ""
# flag if not equal
def fl_e(v1, v2):
    return "X" if v1 != v2 else ""


def sanity_checks(input_path, output_path, rel_tol = 1e-5, n_mid_bands=3):
    # 1. Validate the output COG
    validate_output = rio_cogeo.cog_validate(output_path, strict=True)
    valid = validate_output[0]
    if not valid:
        raise ValueError(f"Output COG did not pass validation: {output_path}.\nCOG errors: {validate_output[1]}\nCOG warnings: {validate_output[2]}")

    data_name = os.path.basename(input_path).split("_predscaled")[0]
    print(f"\nComparing Input and COG for {data_name}\n")

    # 2. Quick check on size and bands 
    with gdal.Open(input_path) as ds_input:
        width_input, height_input = ds_input.RasterXSize, ds_input.RasterYSize
        bands_input = ds_input.RasterCount
    with gdal.Open(output_path) as ds_cog:
        width_cog, height_cog = ds_cog.RasterXSize, ds_cog.RasterYSize
        bands_cog = ds_cog.RasterCount
    if bands_input != bands_cog: # the slicing could potentially introduce errors, which is why we check that the final COG has same number of bands as input
        raise ValueError("Input and Output COG have different number of bands.\nInput bands: {}, COG bands: {}".format(bands_input, bands_cog))
        
    size_df = DataFrame({
        "File": data_name,
        "Dim": ["Width", "Height", "Bands"],
        "Input": [width_input, height_input, bands_input],
        "COG": [width_cog, height_cog, bands_cog],
        "Flag": [fl_e(width_input, width_cog), fl_e(height_input, height_cog), fl_e(bands_input, bands_cog)]
    })

    # 3. Compute mean, max, min band metrics and compare between input and output 
    summaries_df = DataFrame(columns=("File", "Band", "Metric", "Input", "COG", "Diff", "Flag"))
    infile = open_rasterio(input_path, masked=True)
    cog = open_rasterio(output_path, masked=True)
    tol = infile.isel(band=0).max().item() * rel_tol


    sel_bands = [0]
    if n_mid_bands > 0:
        window = bands_input // (n_mid_bands + 1)
        for i in range(n_mid_bands):
            sel_bands.append(window + i * window)
    sel_bands.append(bands_input - 1)

    print(f"\nBands selected for comparison: {[b+1 for b in sel_bands]}")

    for b in sel_bands:
        print(f"Computing metrics for band {b+1}")
        input_band = infile.isel(band=b)
        cog_band = cog.isel(band=b)
        input_mean, input_max, input_min = input_band.mean().item(), input_band.max().item(), input_band.min().item()
        cog_mean, cog_max, cog_min = cog_band.mean().item(), cog_band.max().item(), cog_band.min().item()

        diff_mean, diff_max, diff_min = abs(input_mean - cog_mean), abs(input_max - cog_max), abs(input_min - cog_min)

        flag_mean, flag_max, flag_min = fl_g(diff_mean, tol), fl_g(diff_max, tol), fl_g(diff_min, tol)

        band_df = DataFrame({
            "File": data_name,
            "Band": [b+1, b+1, b+1],
            "Metric": ["Mean", "Max", "Min"],
            "Input": [round(input_mean, 2), round(input_max, 2), round(input_min, 2)],
            "COG": [round(cog_mean, 2), round(cog_max, 2), round(cog_min, 2)],
            "Diff": [diff_mean, diff_max, diff_min],
            "Flag": [flag_mean, flag_max, flag_min]
        })
        summaries_df = concat([summaries_df, band_df], ignore_index=True)

    return size_df, summaries_df




def convert_and_compare(input_dir, cogs_dir, n_slices, rel_tol=1e-5, n_mid_bands=3, trunc=False):
    input_paths = [os.path.join(input_dir, f) for f in os.listdir(input_dir) if f.endswith(".tif") and not f.endswith("_cogd.tif")]

    os.makedirs(cogs_dir, exist_ok=True)
    os.makedirs(os.path.join(cogs_dir, "slices"), exist_ok=True)
    
    size_df = DataFrame(columns = ("File", "Dim", "Input", "COG", "Flag"))
    summaries_df = DataFrame(columns=("File", "Band", "Metric", "Input", "COG", "Diff", "Flag"))

    for input_path in input_paths:
        output_cog = input_path.replace(".tif", "_cogd.tif").split("/")[-1]
        output_path = slice_then_cog(input_path, cogs_dir, output_cog, n=n_slices, trunc=trunc)
        if run_sanity_checks:
            f_size_df, f_summaries_df = sanity_checks(input_path, output_path, rel_tol=rel_tol, n_mid_bands=n_mid_bands)
            size_df = concat([size_df, f_size_df], ignore_index=True)
            summaries_df = concat([summaries_df, f_summaries_df], ignore_index=True)

    if run_sanity_checks:
        size_df.to_csv(os.path.join(cogs_dir, "size_comparisons.csv"), index=False)
        summaries_df.to_csv(os.path.join(cogs_dir, "band_metric_comparisons.csv"), index=False)

    return size_df, summaries_df




size_df, summaries_df = convert_and_compare(input_dir, output_dir, n_slices=16, rel_tol=1e-5, n_mid_bands=1, trunc=trunc_to_uint16)

print("\nSize and band count comparisons (flagged if Input and COG values are not equal):")
print(size_df)
print("\nBand metric comparisons (flagged if difference > tol):")
print(summaries_df)

