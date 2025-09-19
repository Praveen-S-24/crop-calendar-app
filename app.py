import streamlit as st
import rasterio
import folium
from streamlit_folium import st_folium
import os
from pyproj import Transformer
import numpy as np
from shapely.geometry import box
import geopandas as gpd

# -------------------------------
# Page config
# -------------------------------
st.set_page_config(layout="wide", page_title="🌱 Crop Calendar", page_icon="🌾")
st.markdown(
    "<h1 style='text-align:center; color:#006400;'>🌱 Crop Calendar with NDVI & Soil Info</h1>",
    unsafe_allow_html=True
)
st.markdown(
    "<p style='text-align:center; color:gray;'>Click inside the green area to get NDVI, Soil Type, Depth, and Yield Potential.</p>",
    unsafe_allow_html=True
)

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

# Soil rasters
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
# Map
# -------------------------------
st.markdown("### 🌍 Select a Location")

# Create folium map
m = folium.Map(location=[22.0, 80.0], zoom_start=5)

# Add raster coverage bounds overlay (NDVI)
left, bottom, right, top = ndvi_ds.bounds
bounds = [[bottom, left], [top, right]]
folium.Rectangle(
    bounds=bounds,
    color="green",
    fill=True,
    fill_opacity=0.2,
    popup="NDVI Coverage"
).add_to(m)

m.add_child(folium.LatLngPopup())
map_data = st_folium(m, width=700, height=500)

# -------------------------------
# Function to read raster value at lat/lon
# -------------------------------
def get_raster_value(ds, lon, lat, nodata=None):
    try:
        # Transform coordinates if CRS is different
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

    # Check if click is inside NDVI bounds
    if left <= lon <= right and bottom <= lat <= top:
        st.markdown(f"### 📍 Selected Location: Latitude {lat:.4f}, Longitude {lon:.4f}")

        try:
            # NDVI
            ndvi_val = get_raster_value(ndvi_ds, lon, lat, ndvi_nodata)
            if np.isnan(ndvi_val):
                ndvi_val = 0
            if ndvi_val > 1:
                ndvi_val = ndvi_val / 100.0

            # Soil type
            soil_vals = {name: get_raster_value(ds, lon, lat, soil_nodata[name]) for name, ds in soil_layers.items()}
            if all(np.isnan(v) for v in soil_vals.values()):
                soil_type = "Unknown"
                soil_score = 0
            else:
                soil_type = max(soil_vals, key=lambda k: 0 if np.isnan(soil_vals[k]) else soil_vals[k])
                soil_score = 0 if np.isnan(soil_vals[soil_type]) else soil_vals[soil_type]

            # Soil depth
            depth_vals = {name: get_raster_value(ds, lon, lat, depth_nodata[name]) for name, ds in depth_layers.items()}
            if all(np.isnan(v) for v in depth_vals.values()):
                depth_layer = "Unknown"
                depth_val = 0
            else:
                depth_layer = max(depth_vals, key=lambda k: 0 if np.isnan(depth_vals[k]) else depth_vals[k])
                depth_val = 0 if np.isnan(depth_vals[depth_layer]) else depth_vals[depth_layer]

            # Growth stage & yield
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

            # Display
            st.markdown(
                f"""
                <div style="
                    background: linear-gradient(to bottom, #e0ffe0, #c0ffc0);
                    padding:20px; border-radius:15px; border: 2px solid #90ee90;
                    text-align:center;
                ">
                <h3>🌿 NDVI: {ndvi_val:.3f} {ndvi_color}</h3>
                <h3>🪨 Soil Type: {soil_type} (Score: {soil_score:.1f})</h3>
                <h3>📏 Soil Depth Layer: {depth_layer} ({depth_val:.1f} units)</h3>
                <h3>🌱 Growth Stage: {stage}</h3>
                <h3>🌾 Yield Potential: {yield_potential}</h3>
                </div>
                """, unsafe_allow_html=True
            )

        except Exception as e:
            st.error(f"❌ Error reading raster: {e}")
    else:
        st.warning("⚠️ Clicked outside NDVI coverage. Please click inside the green area!")
