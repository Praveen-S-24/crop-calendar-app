import streamlit as st
import rasterio
import folium
from streamlit_folium import st_folium
import os
from pyproj import Transformer
from rasterio.crs import CRS
import numpy as np

st.set_page_config(layout="wide")
st.title("🌱 Crop Calendar with NDVI + Soil + Depth")
st.write("Click on the map to get NDVI, Soil Type, Soil Depth, and Yield Potential.")

# -------------------------------
# Paths
# -------------------------------
base_path = os.path.dirname(__file__)
ndvi_file = "ocm2_ndvi_filt_16to30_jun2021_v01_01.tif"
ndvi_path = os.path.join(base_path, ndvi_file)

soil_files = {
    "Sandy": "fsandy.asc",
    "Loamy": "floamy.asc",
    "Clayey": "fclayey.asc",
    "Clay Skeletal": "fclayskeletal.asc"
}

depth_files = {
    "0-25": "fsoildep0_25.asc",
    "25-50": "fsoildep25_50.asc",
    "50-75": "fsoildep50_75.asc",
    "75-100": "fsoildep75_100.asc"
}

# -------------------------------
# Helper function
# -------------------------------
def get_raster_value(raster_path, lon, lat):
    """Get raster value at lat/lon; handles missing CRS, NoData, and out-of-bounds."""
    if not os.path.exists(raster_path):
        return None
    try:
        with rasterio.open(raster_path) as ds:
            # Set CRS if missing
            if ds.crs is None:
                ds.crs = CRS.from_epsg(4326)

            # Transform coordinates if needed
            if ds.crs.to_string() != "EPSG:4326":
                transformer = Transformer.from_crs("EPSG:4326", ds.crs, always_xy=True)
                x, y = transformer.transform(lon, lat)
            else:
                x, y = lon, lat

            row, col = ds.index(x, y)
            array = ds.read(1)
            
            # Handle out-of-bounds
            if 0 <= row < array.shape[0] and 0 <= col < array.shape[1]:
                val = array[row, col]
                # Treat NoData as None
                if val == ds.nodata or val is np.nan:
                    return None
                return val
            else:
                return None
    except Exception:
        return None

# -------------------------------
# Interactive map
# -------------------------------
m = folium.Map(location=[22.0, 80.0], zoom_start=5)
m.add_child(folium.LatLngPopup())
map_data = st_folium(m, width=700, height=500)

# -------------------------------
# Handle map click
# -------------------------------
if map_data and map_data.get("last_clicked"):
    lat = map_data["last_clicked"]["lat"]
    lon = map_data["last_clicked"]["lng"]
    st.write(f"📍 Selected Location: Latitude {lat:.4f}, Longitude {lon:.4f}")

    # --- NDVI ---
    ndvi_val = get_raster_value(ndvi_path, lon, lat)
    if ndvi_val is not None and ndvi_val > 2:  # likely scaled
        ndvi_val = ndvi_val / 100  # adjust if dataset is scaled

    # --- Soil textures ---
    soil_vals = {name: get_raster_value(os.path.join(base_path, f), lon, lat)
                 for name, f in soil_files.items()}
    # Filter None values
    soil_vals = {k: v for k, v in soil_vals.items() if v is not None}
    soil_type = max(soil_vals, key=soil_vals.get) if soil_vals else "Unknown"

    # --- Soil depth ---
    depth_vals = {name: get_raster_value(os.path.join(base_path, f), lon, lat)
                  for name, f in depth_files.items()}
    depth_vals = {k: v for k, v in depth_vals.items() if v is not None}
    soil_depth = max(depth_vals, key=depth_vals.get) if depth_vals else "Unknown"

    # --- Display values ---
    st.write(f"🌿 NDVI: {ndvi_val:.3f}" if ndvi_val is not None else "NDVI: Unknown")
    st.write(f"🪨 Soil Type: {soil_type}")
    st.write(f"📏 Soil Depth Layer: {soil_depth} cm")

    # --- Growth stage & yield ---
    if ndvi_val is None or soil_type == "Unknown":
        stage = "Unknown"
        yield_potential = "Unknown"
    elif ndvi_val < 0.2:
        stage = "Bare / Early sowing"
        yield_potential = "Very Low" if soil_type == "Sandy" else "Low"
    elif 0.2 <= ndvi_val < 0.5:
        stage = "Active Growth"
        if soil_type == "Sandy":
            yield_potential = "Low to Medium"
        elif soil_type == "Loamy":
            yield_potential = "Medium"
        else:
            yield_potential = "Medium to High"
    else:
        stage = "Healthy / Maturity"
        yield_potential = "Medium" if soil_type == "Sandy" else "High"

    st.success(f"🌱 Growth Stage: {stage}")
    st.subheader(f"🌾 Yield Potential: {yield_potential}")
