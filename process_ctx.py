import os
import tempfile
os.environ.setdefault('MPLCONFIGDIR', os.path.join(tempfile.gettempdir(), 'matplotlib'))

import numpy as np
import matplotlib.pyplot as plt

ctx_file = "ctx_image_N10_066297_1615.IMG"

if not os.path.exists(ctx_file):
    print(f"File not found: {ctx_file}. Please run mola.py first.")
    exit(1)

print(f"Loading CTX visual image: {ctx_file}...")

# CTX PDS image parameters from the embedded header:
HEADER_BYTES = 5056
LINES = 52224        # Total image rows
LINE_SAMPLES = 5056  # Total columns (swath width)

# Use memory mapping to read high-resolution sections without overloading RAM
raw_img = np.memmap(ctx_file, dtype=np.uint8, mode='r', offset=HEADER_BYTES, shape=(LINES, LINE_SAMPLES))

print("Image dimensions: 5,056 x 52,224 pixels (~264 MB)")

# 1. Extract a high-detail full-resolution section (2048 x 2048 pixels)
row_start = 24000
col_start = 1500
detail_crop = np.array(raw_img[row_start:row_start + 2048, col_start:col_start + 2048])

# Contrast stretch (2nd to 98th percentile) for optimal visual clarity
p2, p98 = np.percentile(detail_crop, (2, 98))
if p98 > p2:
    detail_stretched = np.clip((detail_crop.astype(np.float32) - p2) / (p98 - p2) * 255.0, 0, 255).astype(np.uint8)
else:
    detail_stretched = detail_crop

# Plot and save high-detail Martian surface view
fig, ax = plt.subplots(figsize=(10, 10))
ax.imshow(detail_stretched, cmap='gray')
ax.set_title("Mars Reconnaissance Orbiter (MRO) CTX High-Res Surface Detail (~6 m/pixel)", fontsize=12, pad=10)
ax.set_xlabel("Pixel Column")
ax.set_ylabel("Pixel Row")

output_detail_png = "mars_ctx_detail.png"
plt.savefig(output_detail_png, dpi=150, bbox_inches='tight')
plt.close(fig)
print(f"High-resolution detail image saved to: {output_detail_png}")

# 2. Extract downsampled overview of the orbital strip (every 32nd row, 4th column)
print("Generating orbital strip overview...")
overview = np.array(raw_img[::32, ::4])
p2, p98 = np.percentile(overview, (2, 98))
if p98 > p2:
    overview_stretched = np.clip((overview.astype(np.float32) - p2) / (p98 - p2) * 255.0, 0, 255).astype(np.uint8)
else:
    overview_stretched = overview

fig, ax = plt.subplots(figsize=(6, 12))
ax.imshow(overview_stretched, cmap='gray', aspect='auto')
ax.set_title("MRO CTX Full Orbital Strip Overview", fontsize=11, pad=10)
ax.set_xlabel("Downsampled Columns (x4)")
ax.set_ylabel("Downsampled Rows (x32)")

output_strip_png = "mars_ctx_strip.png"
plt.savefig(output_strip_png, dpi=150, bbox_inches='tight')
plt.close(fig)
print(f"Orbital strip overview saved to: {output_strip_png}")
print("\nCTX processing completed successfully!")
