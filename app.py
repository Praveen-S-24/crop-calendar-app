import streamlit as st
import rasterio
import folium
from streamlit_folium import st_folium

# Soil file mapping
SOIL_FILES = {
    "floamy.asc": "Loamy",
    "fsandy.asc": "Sandy",
    "fclayey.asc": "Clayey",
    "fclayskeletal.asc": "Clay Skeletal"
}

# --- Function to get NDVI value ---
def get_ndvi(lat, lon, ndvi_path="ocm2_ndvi_filt_16to30_jun2021_v01_01.tif"):
    try:
        with rasterio.open(ndvi_path) as src:
            row, col = src.index(lon, lat)
            val = src.read(1)[row, col]

            if val == src.nodata:
                return None

            # Scale NDVI if in raw format
            if val > 1:
                val = val / 10000.0

            # Clamp between 0–1
            val = max(0, min(1, val))
            return val
    except Exception:
        return None

# --- Function to classify NDVI ---
def classify_growth_stage(ndvi):
    if ndvi is None:
        return "No Data", "⚪"
    elif ndvi < 0.3:
        return "Bare / Early Sowing", "🌱"
    elif ndvi < 0.6:
        return "Active Growth", "🌿"
    else:
        return "Healthy / Maturity", "🌾"

# --- Function to get soil type ---
def get_soil_type(lat, lon):
    for fpath, label in SOIL_FILES.items():
        try:
            with rasterio.open(fpath) as src:
                row, col = src.index(lon, lat)
                val = src.read(1)[row, col]
                if val != src.nodata:
                    return label
        except Exception:
            continue
    return "Unknown"

# --- Streamlit UI ---
st.set_page_config(page_title="Crop Growth App", layout="wide")
st.title("🌍 Crop Growth & Soil Detection App")

# Map setup
m = folium.Map(location=[20, 78], zoom_start=5)
st_map = st_folium(m, height=500, width=700)

if st_map and st_map.get("last_clicked"):
    lat, lon = st_map["last_clicked"]["lat"], st_map["last_clicked"]["lng"]

    # Get NDVI
    ndvi = get_ndvi(lat, lon)
    growth_stage, emoji = classify_growth_stage(ndvi)

    # Get Soil
    soil = get_soil_type(lat, lon)

    # Show results
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📌 Results")
        st.markdown(f"**NDVI:** {ndvi if ndvi is not None else 'No Data'}")
        st.markdown(f"**Growth Stage:** {emoji} {growth_stage}")
    with col2:
        st.subheader("🌱 Soil Info")
        st.markdown(f"**Soil Type:** {soil}")
        st.markdown(f"**Location:** {lat:.4f}, {lon:.4f}")
