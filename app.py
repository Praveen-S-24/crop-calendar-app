import rasterio

paths = [
    "data/fsandy.asc",
    "data/floamy.asc",
    "data/fclayey.asc",
    "data/fclayskeletal.asc",
    "data/fsoildep0_25.asc"
]

for path in paths:
    with rasterio.open(path) as src:
        print(path, "→ CRS:", src.crs, "Bounds:", src.bounds)
