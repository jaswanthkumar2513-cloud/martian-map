import struct
import numpy as np
import os

def save_grayscale_bmp(filename, arr):
    """Saves a 2D uint8 numpy array as a standard Windows BMP file."""
    h, w = arr.shape
    row_padding = (4 - (w % 4)) % 4
    row_stride = w + row_padding
    pixel_data_size = row_stride * h
    offset = 14 + 40 + 1024
    file_size = offset + pixel_data_size
    
    # 14-byte BMP Header
    bmp_header = struct.pack('<2sIHHI', b'BM', file_size, 0, 0, offset)
    
    # 40-byte DIB Header (negative height = top-down raster)
    dib_header = struct.pack('<IiiHHIIiiII', 40, w, -h, 1, 8, 0, pixel_data_size, 2835, 2835, 256, 0)
    
    # 256-color Grayscale Palette
    palette = bytearray()
    for i in range(256):
        palette.extend((i, i, i, 0))
        
    with open(filename, 'wb') as f:
        f.write(bmp_header)
        f.write(dib_header)
        f.write(palette)
        if row_padding == 0:
            f.write(arr.tobytes())
        else:
            pad = b'\x00' * row_padding
            for r in range(h):
                f.write(arr[r].tobytes())
                f.write(pad)
    print(f"Saved: {filename} ({w}x{h})")

def convert_ctx():
    ctx_file = "ctx_image_N10_066297_1615.IMG"
    if not os.path.exists(ctx_file):
        print(f"Missing {ctx_file}")
        return
        
    print("\n--- Processing CTX Image ---")
    # Memory map the 264MB raw image file without loading it all into memory
    # Header is 5056 bytes, image is 52224 lines x 5056 samples, 8-bit unsigned
    img = np.memmap(ctx_file, dtype=np.uint8, mode='r', offset=5056, shape=(52224, 5056))
    
    # 1. High-resolution crop (2048 x 2048) from the middle of the swath
    start_row = 25000
    start_col = 1500
    crop = np.array(img[start_row:start_row+2048, start_col:start_col+2048])
    # Stretch contrast slightly for better viewing
    p2, p98 = np.percentile(crop, (2, 98))
    if p98 > p2:
        crop_stretched = np.clip((crop.astype(np.float32) - p2) / (p98 - p2) * 255.0, 0, 255).astype(np.uint8)
    else:
        crop_stretched = crop
    save_grayscale_bmp("ctx_surface_crop_highres.bmp", crop_stretched)
    
    # 2. Downsampled overview of the entire CTX orbital strip (every 32nd row, 4th column)
    overview = np.array(img[::32, ::4])
    p2, p98 = np.percentile(overview, (2, 98))
    if p98 > p2:
        overview_stretched = np.clip((overview.astype(np.float32) - p2) / (p98 - p2) * 255.0, 0, 255).astype(np.uint8)
    else:
        overview_stretched = overview
    save_grayscale_bmp("ctx_orbital_strip_overview.bmp", overview_stretched)

def convert_mola():
    mola_file = "mola_elevation_megt90n000eb.img"
    if not os.path.exists(mola_file):
        print(f"Missing {mola_file}")
        return
        
    print("\n--- Processing MOLA Global Elevation Map ---")
    # 2880 rows x 5760 cols, 16-bit signed big-endian integer elevation in meters
    elev = np.fromfile(mola_file, dtype='>i2').reshape((2880, 5760))
    print(f"Mars Elevation Range: Min = {elev.min()} m, Max = {elev.max()} m")
    
    # Downsample by 2x for a convenient 2880x1440 global map
    elev_sub = elev[::2, ::2].astype(np.float32)
    
    # Normalize elevation to 0-255 (grayscale where dark = low basins, bright = high volcanoes)
    min_elev, max_elev = -8200.0, 21200.0
    norm = np.clip((elev_sub - min_elev) / (max_elev - min_elev) * 255.0, 0, 255).astype(np.uint8)
    save_grayscale_bmp("mola_mars_global_elevation.bmp", norm)

if __name__ == "__main__":
    convert_ctx()
    convert_mola()
    print("\nAll done! BMP images created successfully.")
