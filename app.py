import streamlit as st
import rasterio
import folium
from streamlit_folium import st_folium
import os
from pyproj import Transformer
from rasterio.crs import CRS
import numpy as np

# -------------------------------
# PAGE CONFIG & STYLES
# -------------------------------
st.set_page_config(layout="wide")
st.markdown("""
    <style>
    /* Green gradient background */
    .stApp {
        background: linear-gradient(to bottom, #e0f7e9, #a8e6a3);
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🌱 Crop Calendar with NDVI + Soil + Depth")
st.write("Click on the map to get NDVI, Soil Type, Soil Depth, Growth Stage, and Yield Potential.")

# -------------------------------
# PATHS
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
# HELPER FUNCTIONS
# -------------------------------
def get_raster_value_nearest(raster_path, lon, lat):
    """Return raster value; check nearest pixel if clicked pixel is NoData."""
    if not os.path.exists(raster_path):
        return None
    try:
        with rasterio.open(raster_path) as ds:
            if ds.crs is None:
                ds.crs = CRS.from_epsg(4326)

            if ds.crs.to_string() != "EPSG:4326":
                transformer = Transformer.from_crs("EPSG:4326", ds.crs, always_xy=True)
                x, y = transformer.transform(lon, lat)
            else:
                x, y = lon, lat

            row, col = ds.index(x, y)
            array = ds.read(1)

            # Check clicked pixel
            if 0 <= row < array.shape[0] and 0 <= col < array.shape[1]:
                val = array[row, col]
                if val == ds.nodata or val is np.nan:
                    # Search 3x3 window around pixel
                    r0, r1 = max(row-1,0), min(row+2,array.shape[0])
                    c0, c1 = max(col-1,0), min(col+2,array.shape[1])
                    window = array[r0:r1, c0:c1]
                    valid = window[window != ds.nodata]
                    return valid.max() if valid.size>0 else None
                return val
            else:
                return None
    except:
        return None

# -------------------------------
# INTERACTIVE MAP
# -------------------------------
m = folium.Map(location=[22.0, 80.0], zoom_start=5)
m.add_child(folium.LatLngPopup())
map_data = st_folium(m, width=800, height=500)

# -------------------------------
# HANDLE CLICK
# -------------------------------
if map_data and map_data.get("last_clicked"):
    lat = map_data["last_clicked"]["lat"]
    lon = map_data["last_clicked"]["lng"]
    st.markdown(f"### 📍 Selected Location: Latitude {lat:.4f}, Longitude {lon:.4f}")

    # --- NDVI ---
    ndvi_val = get_raster_value_nearest(ndvi_path, lon, lat)
    if ndvi_val is not None and ndvi_val > 2:
        ndvi_val = ndvi_val / 100  # adjust scaled NDVI
    if ndvi_val is not None:
        ndvi_val = max(0, min(ndvi_val, 1))  # clip 0-1

    # --- Soil texture ---
    soil_vals = {name: get_raster_value_nearest(os.path.join(base_path, f), lon, lat)
                 for name, f in soil_files.items()}
    soil_vals = {k: v for k, v in soil_vals.items() if v is not None}
    soil_type = max(soil_vals, key=soil_vals.get) if soil_vals else "Unknown"

    # --- Soil depth ---
    depth_vals = {name: get_raster_value_nearest(os.path.join(base_path, f), lon, lat)
                  for name, f in depth_files.items()}
    depth_vals = {k: v for k, v in depth_vals.items() if v is not None}
    soil_depth = max(depth_vals, key=depth_vals.get) if depth_vals else "Unknown"

    # --- Display info ---
    st.markdown(f"🌿 **NDVI:** {ndvi_val:.3f}" if ndvi_val is not None else "NDVI: Unknown")
    st.markdown(f"🪨 **Soil Type:** {soil_type}")
    st.markdown(f"📏 **Soil Depth Layer:** {soil_depth} cm")

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

    st.success(f"🌱 **Growth Stage:** {stage}")
    st.subheader(f"🌾 **Yield Potential:** {yield_potential}")
