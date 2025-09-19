import streamlit as st
import rasterio
import folium
from streamlit_folium import st_folium
import os
from pyproj import Transformer
import numpy as np

# -------------------------------
# Page config
# -------------------------------
st.set_page_config(layout="wide", page_title="🌱 Crop Calendar", page_icon="🌾")
st.markdown("<h1 style='text-align:center; color:#006400;'>🌱 Crop Calendar with NDVI & Soil Info</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:gray;'>Click inside the green area to get NDVI, Soil Type, Depth, Growth Stage & Yield Potential.</p>", unsafe_allow_html=True)

# -------------------------------
# Paths
# -------------------------------
base_path = os.path.join(os.path.dirname(__file__), "data")

# NDVI raster
ndvi_file = "ocm2_ndvi_filt_16to30_jun2021_v01_01.tif"
ndvi_path = os.path.join(base_path, ndvi_file)
if not os.path.exists(ndvi_path):
    st.error(f"❌ NDVI file missing: {ndvi_file}")
else:
    ndvi_ds = rasterio.open(ndvi_path)
    ndvi_nodata = ndvi_ds.nodata

# Soil rasters (categorical)
soil_files = {
    "Sandy": "fsandy.asc",
    "Loamy": "floamy.asc",
    "Clayey": "fclayey.asc",
    "Clay Skeletal": "fclayskeletal.asc"
}
soil_layers = {}
soil_nodata = {}
for name, fname in soil_files.items():
    path = os.path.join(base_path, fname)
    if not os.path.exists(path):
        st.error(f"❌ Missing soil file: {fname}")
    else:
        ds = rasterio.open(path)
        soil_layers[name] = ds
        soil_nodata[name] = ds.nodata

# Soil depth rasters
depth_files = {
    "0-25 cm": "fsoildep0_25.asc",
    "25-50 cm": "fsoildep25_50.asc",
    "50-75 cm": "fsoildep50_75.asc",
    "75-100 cm": "fsoildep75_100.asc"
}
depth_layers = {}
depth_nodata = {}
for name, fname in depth_files.items():
    path = os.path.join(base_path, fname)
    if not os.path.exists(path):
        st.error(f"❌ Missing depth file: {fname}")
    else:
        ds = rasterio.open(path)
        depth_layers[name] = ds
        depth_nodata[name] = ds.nodata

# -------------------------------
# Map with NDVI coverage
# -------------------------------
st.markdown("### 🌍 Select a Location")
m = folium.Map(location=[22.0, 80.0], zoom_start=5)

# Show NDVI bounds
left, bottom, right, top = ndvi_ds.bounds
folium.Rectangle(
    bounds=[[bottom, left], [top, right]],
    color="green",
    fill=True,
    fill_opacity=0.2,
    popup="NDVI Coverage"
).add_to(m)

m.add_child(folium.LatLngPopup())
map_data = st_folium(m, width=700, height=500)

# -------------------------------
# Helper: read raster value at lat/lon
# -------------------------------
def get_raster_value(ds, lon, lat, nodata=None):
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
            if nodata is not None and val == nodata:
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

    # Check inside NDVI bounds
    if left <= lon <= right and bottom <= lat <= top:
        st.markdown(f"### 📍 Selected Location: Latitude {lat:.4f}, Longitude {lon:.4f}")

        # NDVI value (scale 0-1)
        ndvi_val = get_raster_value(ndvi_ds, lon, lat, ndvi_nodata)
        if np.isnan(ndvi_val):
            ndvi_val = 0
        elif ndvi_val > 1:
            ndvi_val = ndvi_val / 100.0

        # Soil type (categorical check)
        soil_type = "Unknown"
        soil_score = 0
        for sname, ds in soil_layers.items():
            val = get_raster_value(ds, lon, lat, soil_nodata[sname])
            if val == 1:  # presence
                soil_type = sname
                soil_score = val
                break

        # Depth layer (categorical)
        depth_layer = "Unknown"
        depth_val = 0
        for dname, ds in depth_layers.items():
            val = get_raster_value(ds, lon, lat, depth_nodata[dname])
            if val > 0:
                depth_layer = dname
                depth_val = val
                break

        # -------------------------------
        # Growth stage & yield
        # -------------------------------
        if ndvi_val < 0.2:
            stage = "Bare / Early sowing 🌱"
            ndvi_color = "🔴"
            yield_potential = "Very Low 🔴" if soil_type == "Sandy" else "Low 🟠"
        elif 0.2 <= ndvi_val < 0.5:
            stage = "Active Growth 🌿"
            ndvi_color = "🟠"
            if soil_type == "Sandy":
                yield_potential = "Low to Medium 🟠"
            elif soil_type == "Loamy":
                yield_potential = "Medium 🟡"
            else:
                yield_potential = "Medium to High 🟢"
        else:
            stage = "Healthy / Maturity 🌾"
            ndvi_color = "🟢"
            yield_potential = "Medium 🟡" if soil_type == "Sandy" else "High 🟢"

        # -------------------------------
        # Display results with gradient
        # -------------------------------
        st.markdown(
            f"""
            <div style="
                background: linear-gradient(to bottom, #e0ffe0, #c0ffc0);
                padding:20px; border-radius:15px; border: 2px solid #90ee90;
                text-align:center;
            ">
            <h3>🌿 NDVI: {ndvi_val:.3f} {ndvi_color}</h3>
            <h3>🪨 Soil Type: {soil_type} (Score: {soil_score})</h3>
            <h3>📏 Soil Depth Layer: {depth_layer} ({depth_val})</h3>
            <h3>🌱 Growth Stage: {stage}</h3>
            <h3>🌾 Yield Potential: {yield_potential}</h3>
            </div>
            """, unsafe_allow_html=True
        )
    else:
        st.warning("⚠️ Clicked outside NDVI coverage. Please click inside the green area!")
