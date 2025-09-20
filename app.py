import streamlit as st
import rasterio
from rasterio.enums import Resampling
import folium
from streamlit_folium import st_folium
from pyproj import Transformer
import numpy as np
import os

# -------------------------------
# Page config
# -------------------------------
st.set_page_config(layout="wide", page_title="🌱 Crop Calendar", page_icon="🌾")
st.title("🌱 Crop Calendar with NDVI, Soil & Depth Info")
st.write("Click on the map to get NDVI, Soil Type, Depth, Growth Stage & Yield Potential.")

# -------------------------------
# Paths
# -------------------------------
base_path = os.path.join(os.path.dirname(__file__), "data")

# NDVI raster
ndvi_file = "ocm2_ndvi_filt_16to30_jun2021_v01_01.tif"
ndvi_path = os.path.join(base_path, ndvi_file)
if not os.path.exists(ndvi_path):
    st.error(f"NDVI file missing: {ndvi_file}")
else:
    ndvi_ds = rasterio.open(ndvi_path)
    ndvi_nodata = ndvi_ds.nodata

# Soil rasters
soil_files = {
    "Sandy": "fsandy.asc",
    "Loamy": "floamy.asc",
    "Clayey": "fclayey.asc",
    "Clay Skeletal": "fclayskeletal.asc"
}
soil_layers = {}
for name, fname in soil_files.items():
    path = os.path.join(base_path, fname)
    if os.path.exists(path):
        soil_layers[name] = rasterio.open(path)

# Depth rasters
depth_files = {
    "0-25 cm": "fsoildep0_25.asc",
    "25-50 cm": "fsoildep25_50.asc",
    "50-75 cm": "fsoildep50_75.asc",
    "75-100 cm": "fsoildep75_100.asc"
}
depth_layers = {}
for name, fname in depth_files.items():
    path = os.path.join(base_path, fname)
    if os.path.exists(path):
        depth_layers[name] = rasterio.open(path)

# -------------------------------
# Map
# -------------------------------
st.markdown("### 🌍 Select a Location")
m = folium.Map(location=[22.0, 80.0], zoom_start=5)
m.add_child(folium.LatLngPopup())
map_data = st_folium(m, width=700, height=500)

# -------------------------------
# Helper: Read raster at lat/lon
# -------------------------------
def get_value(ds, lon, lat):
    try:
        if ds.crs and ds.crs.to_string() != "EPSG:4326":
            transformer = Transformer.from_crs("EPSG:4326", ds.crs, always_xy=True)
            x, y = transformer.transform(lon, lat)
        else:
            x, y = lon, lat
        row, col = ds.index(x, y)
        arr = ds.read(1)
        h, w = arr.shape
        if 0 <= row < h and 0 <= col < w:
            val = arr[row, col]
            if ds.nodata is not None and val == ds.nodata:
                return np.nan
            return val
        return np.nan
    except:
        return np.nan

# -------------------------------
# Process click
# -------------------------------
if map_data and map_data.get("last_clicked"):
    lat = map_data["last_clicked"]["lat"]
    lon = map_data["last_clicked"]["lng"]
    st.markdown(f"### 📍 Selected Location: Latitude {lat:.4f}, Longitude {lon:.4f}")

    # NDVI
    ndvi_val = get_value(ndvi_ds, lon, lat)
    if ndvi_val is None or np.isnan(ndvi_val):
        ndvi_val = 0
    elif ndvi_val > 1:
        ndvi_val = ndvi_val / 100  # scale 0-1

    # Soil type
    soil_type = "Unknown"
    for name, ds in soil_layers.items():
        val = get_value(ds, lon, lat)
        if val == 1:
            soil_type = name
            break

    # Depth layer
    depth_layer = "Unknown"
    for name, ds in depth_layers.items():
        val = get_value(ds, lon, lat)
        if val > 0:
            depth_layer = name
            break

    # Growth stage & yield
    if ndvi_val < 0.2:
        stage = "Bare / Early sowing 🌱"
        yield_potential = "Very Low 🔴" if soil_type == "Sandy" else "Low 🟠"
    elif 0.2 <= ndvi_val < 0.5:
        stage = "Active Growth 🌿"
        if soil_type == "Sandy":
            yield_potential = "Low to Medium 🟠"
        elif soil_type == "Loamy":
            yield_potential = "Medium 🟡"
        else:
            yield_potential = "Medium to High 🟢"
    else:
        stage = "Healthy / Maturity 🌾"
        yield_potential = "Medium 🟡" if soil_type == "Sandy" else "High 🟢"

    # Display
    st.markdown(
        f"""
        <div style="
            padding:20px; border-radius:15px; border:2px solid #90ee90;
            background: linear-gradient(to bottom, #f0fff0, #c0ffc0); text-align:center;
        ">
        <h3>🌿 NDVI: {ndvi_val:.3f}</h3>
        <h3>🪨 Soil Type: {soil_type}</h3>
        <h3>📏 Soil Depth Layer: {depth_layer}</h3>
        <h3>🌱 Growth Stage: {stage}</h3>
        <h3>🌾 Yield Potential: {yield_potential}</h3>
        </div>
        """, unsafe_allow_html=True
    )
