import streamlit as st
import rasterio
import folium
from streamlit_folium import st_folium
import os
from pyproj import Transformer

# --- Page config ---
st.set_page_config(layout="wide", page_title="🌱 Crop Calendar", page_icon="🌾")
st.markdown("<h1 style='text-align:center; color:green;'>🌱 Crop Calendar</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:gray;'>Click on the map to get NDVI, Soil Type, Growth Stage, and Yield Potential</p>", unsafe_allow_html=True)

# --- Load raster datasets ---
base_path = os.path.dirname(__file__)
ndvi_file = "ocm2_ndvi_filt_16to30_jun2021_v01_01.tif"
ndvi_path = os.path.join(base_path, ndvi_file)
if not os.path.exists(ndvi_path):
    st.error(f"❌ NDVI file missing: {ndvi_file}")
else:
    ndvi_ds = rasterio.open(ndvi_path)

soil_files = {"Sandy": "fsandy.asc", "Loamy": "floamy.asc", "Clayey": "fclayey.asc", "Clay Skeletal": "fclayskeletal.asc"}
soil_layers = {}
for name, filename in soil_files.items():
    path = os.path.join(base_path, filename)
    if not os.path.exists(path):
        st.error(f"❌ Missing soil file: {filename}")
    else:
        soil_layers[name] = rasterio.open(path)

# --- Map ---
st.markdown("### 🌍 Select a Location")
m = folium.Map(location=[22.0, 80.0], zoom_start=5)
m.add_child(folium.LatLngPopup())
map_data = st_folium(m, width=700, height=500)

# --- Handle click ---
if map_data and map_data.get("last_clicked"):
    lat = map_data["last_clicked"]["lat"]
    lon = map_data["last_clicked"]["lng"]
    st.markdown(f"### 📍 Selected Location: Latitude {lat:.4f}, Longitude {lon:.4f}")

    try:
        # Transform coordinates
        if ndvi_ds.crs.to_string() != "EPSG:4326":
            transformer = Transformer.from_crs("EPSG:4326", ndvi_ds.crs, always_xy=True)
            x, y = transformer.transform(lon, lat)
        else:
            x, y = lon, lat

        row, col = ndvi_ds.index(x, y)
        height, width = ndvi_ds.read(1).shape

        if 0 <= row < height and 0 <= col < width:
            # Read NDVI with nodata handling and scaling
            ndvi_band = ndvi_ds.read(1)
            nodata = ndvi_ds.nodata
            ndvi_val = ndvi_band[row, col]
            if ndvi_val == nodata:
                st.warning("⚠️ NDVI value at this location is missing")
                ndvi_val = 0
            elif ndvi_val > 1:  # scale if raster uses 0-10000
                ndvi_val = ndvi_val / 10000
            ndvi_val = max(0, min(ndvi_val, 1))  # clamp 0-1
            st.write(f"🔹 Raw NDVI value: {ndvi_val:.3f}")

            # Extract soil type
            soil_vals = {}
            for name, ds in soil_layers.items():
                if ds.crs.to_string() != "EPSG:4326":
                    transformer = Transformer.from_crs("EPSG:4326", ds.crs, always_xy=True)
                    x_s, y_s = transformer.transform(lon, lat)
                else:
                    x_s, y_s = lon, lat
                r, c = ds.index(x_s, y_s)
                h, w = ds.read(1).shape
                soil_vals[name] = ds.read(1)[r, c] if 0 <= r < h and 0 <= c < w else 0
            soil_type = max(soil_vals, key=soil_vals.get)

            # Growth stage & yield
            if ndvi_val < 0.3:
                stage = "Bare / Early sowing 🌱"
                stage_color = "red"
                yield_potential = "Very Low 🔴" if soil_type == "Sandy" else "Low 🟠"
            elif ndvi_val < 0.6:
                stage = "Active Growth 🌿"
                stage_color = "orange"
                if soil_type == "Sandy":
                    yield_potential = "Low to Medium 🟠"
                elif soil_type == "Loamy":
                    yield_potential = "Medium 🟡"
                else:
                    yield_potential = "Medium to High 🟢"
            else:
                stage = "Healthy / Maturity 🌾"
                stage_color = "green"
                yield_potential = "Medium 🟡" if soil_type == "Sandy" else "High 🟢"

            # Display results in columns
            st.markdown("### Results")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("🌿 NDVI", f"{ndvi_val:.3f}")
            col2.metric("🪨 Soil Type", soil_type)
            col3.markdown(f"**🌱 Growth Stage:** <span style='color:{stage_color};'>{stage}</span>", unsafe_allow_html=True)
            col4.markdown(f"**🌾 Yield Potential:** {yield_potential}", unsafe_allow_html=True)
        else:
            st.error("⚠️ Clicked location is outside NDVI raster bounds!")

    except Exception as e:
        st.error(f"❌ Error reading raster: {e}")
