import streamlit as st
import rasterio
import folium
from streamlit_folium import st_folium
import os
import numpy as np
from pyproj import Transformer

st.set_page_config(layout="wide")
st.title("🌱 Crop Calendar with NDVI + Soil Info")
st.write("Click on the map to get NDVI, Soil Type, and Yield Potential.")

# -------------------------------
# Paths to raster datasets
# -------------------------------
base_path = os.path.dirname(__file__)

# NDVI raster (tif)
ndvi_file = "ocm2_ndvi_filt_16to30_jun2021_v01_01.tif"
ndvi_path = os.path.join(base_path, ndvi_file)
if not os.path.exists(ndvi_path):
    st.error(f"NDVI file missing: {ndvi_file}")
else:
    ndvi_ds = rasterio.open(ndvi_path)

# Soil layers (ASC files from Bhuvan)
soil_files = {
    "Sandy": "fsandy.asc",
    "Loamy": "floamy.asc",
    "Clayey": "fclayey.asc",
    "Clay Skeletal": "fclayskeletal.asc"
}

soil_layers = {}
for name, filename in soil_files.items():
    path = os.path.join(base_path, filename)
    if not os.path.exists(path):
        st.error(f"Missing soil file: {filename}")
    else:
        soil_layers[name] = rasterio.open(path).read(1)

# -------------------------------
# Map for pinning location
# -------------------------------
m = folium.Map(location=[22.0, 80.0], zoom_start=5)
m.add_child(folium.LatLngPopup())
map_data = st_folium(m, width=700, height=500)

# -------------------------------
# When user clicks on map
# -------------------------------
if map_data and map_data.get("last_clicked"):
    lat = map_data["last_clicked"]["lat"]
    lon = map_data["last_clicked"]["lng"]
    st.write(f"📍 Selected Location: Latitude {lat:.4f}, Longitude {lon:.4f}")

    try:
        # Convert lat/lon to raster CRS
        if ndvi_ds.crs.to_string() != "EPSG:4326":
            transformer = Transformer.from_crs("EPSG:4326", ndvi_ds.crs, always_xy=True)
            x, y = transformer.transform(lon, lat)
            row, col = ndvi_ds.index(x, y)
        else:
            row, col = ndvi_ds.index(lon, lat)

        # NDVI value
        ndvi_val = ndvi_ds.read(1)[row, col]

        # -------------------------------
        # Extract soil type (dominant layer)
        # -------------------------------
        soil_vals = {name: layer[row, col] for name, layer in soil_layers.items()}
        soil_type = max(soil_vals, key=soil_vals.get)

        st.write(f"🌿 NDVI: {ndvi_val:.3f}")
        st.write(f"🪨 Soil Type: {soil_type}")

        # -------------------------------
        # Yield / Growth Stage Estimation
        # -------------------------------
        if ndvi_val < 0.2:
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

    except Exception as e:
        st.error(f"Error reading raster: {e}")
