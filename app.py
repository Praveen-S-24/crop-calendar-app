import streamlit as st
import folium
from streamlit_folium import st_folium
import rasterio
from rasterio.plot import show
import numpy as np

# ------------------------------
# Utility: Read raster value
# ------------------------------
def get_raster_value(raster_path, lat, lon):
    try:
        with rasterio.open(raster_path) as src:
            row, col = src.index(lon, lat)  # lon, lat order!
            value = src.read(1)[row, col]
            if value == src.nodata:
                return None
            return float(value)
    except Exception:
        return None

# ------------------------------
# Load raster files (replace with your files in /data/)
# ------------------------------
soil_rasters = {
    "Sandy": "data/soil_sandy.tif",
    "Loamy": "data/soil_loamy.tif",
    "Clayey": "data/soil_clayey.tif",
    "Clay Skeletal": "data/soil_clay_skeletal.tif"
}

depth_rasters = {
    "0-25 cm": "data/depth_0_25.tif",
    "25-50 cm": "data/depth_25_50.tif",
    "50-75 cm": "data/depth_50_75.tif",
    "75-100 cm": "data/depth_75_100.tif"
}

# ------------------------------
# Streamlit UI
# ------------------------------
st.set_page_config(page_title="Crop Calendar App", layout="wide")
st.title("🌾 Crop Calendar App (NDVI + Soil + Depth)")

st.write("Select a location on the map to get NDVI, Soil, and Depth info.")

# Folium map
m = folium.Map(location=[20.5937, 78.9629], zoom_start=5)
map_data = st_folium(m, width=700, height=500)

if map_data["last_clicked"] is not None:
    lat = map_data["last_clicked"]["lat"]
    lon = map_data["last_clicked"]["lng"]

    st.subheader(f"📍 Selected Location: Latitude {lat:.4f}, Longitude {lon:.4f}")

    # ------------------------------
    # Soil data
    # ------------------------------
    soil_scores = {}
    for soil_type, path in soil_rasters.items():
        val = get_raster_value(path, lat, lon)
        soil_scores[soil_type] = val

    best_soil = max(soil_scores, key=lambda x: soil_scores[x] if soil_scores[x] is not None else -1)
    st.write(f"🪨 Soil Type: {best_soil} (Score: {soil_scores[best_soil]})")

    # ------------------------------
    # Depth data
    # ------------------------------
    depth_scores = {}
    for depth, path in depth_rasters.items():
        val = get_raster_value(path, lat, lon)
        depth_scores[depth] = val

    best_depth = max(depth_scores, key=lambda x: depth_scores[x] if depth_scores[x] is not None else -1)
    st.write(f"📏 Soil Depth Layer: {best_depth} ({depth_scores[best_depth]})")

    # ------------------------------
    # Placeholder NDVI
    # ------------------------------
    ndvi_value = np.random.uniform(0, 1)  # later replace with real NDVI
    st.write(f"🌿 NDVI: {ndvi_value:.3f}")

    # ------------------------------
    # Growth Stage Logic
    # ------------------------------
    if ndvi_value < 0.2:
        stage = "Bare / Early sowing 🌱"
        yield_status = "Very Low 🔴"
    elif ndvi_value < 0.5:
        stage = "Vegetative 🌿"
        yield_status = "Medium 🟡"
    else:
        stage = "Reproductive 🌾"
        yield_status = "High 🟢"

    st.write(f"🌱 Growth Stage: {stage}")
    st.write(f"🌾 Yield Potential: {yield_status}")
