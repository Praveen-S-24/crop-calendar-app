import streamlit as st
import rasterio
import folium
from streamlit_folium import st_folium
import numpy as np
import os

st.set_page_config(page_title="Crop Growth & Soil App", layout="wide")

st.title("🌾 Crop Growth & Soil Detection App")

# File uploader for rasters
st.sidebar.header("Upload Data")
ndvi_file = st.sidebar.file_uploader("Upload NDVI raster (.tif)", type=["tif", "tiff"])
soil_file = st.sidebar.file_uploader("Upload Soil raster (.tif)", type=["tif", "tiff"])

if ndvi_file and soil_file:
    with rasterio.open(ndvi_file) as ndvi_ds:
        ndvi_data = ndvi_ds.read(1)
        ndvi_transform = ndvi_ds.transform
        ndvi_nodata = ndvi_ds.nodata
        ndvi_bounds = ndvi_ds.bounds

    with rasterio.open(soil_file) as soil_ds:
        soil_data = soil_ds.read(1)
        soil_transform = soil_ds.transform
        soil_nodata = soil_ds.nodata
        soil_bounds = soil_ds.bounds

    # Show map
    center_lat = (ndvi_bounds.top + ndvi_bounds.bottom) / 2
    center_lon = (ndvi_bounds.left + ndvi_bounds.right) / 2
    m = folium.Map(location=[center_lat, center_lon], zoom_start=8)
    st_map = st_folium(m, width=700, height=500)

    if st_map and st_map.get("last_clicked"):
        lon, lat = st_map["last_clicked"]["lng"], st_map["last_clicked"]["lat"]

        # Convert lat/lon to NDVI pixel
        try:
            row, col = ~ndvi_transform * (lon, lat)
            row, col = int(row), int(col)
            ndvi_value = ndvi_data[row, col]

            if ndvi_nodata is not None and ndvi_value == ndvi_nodata:
                raise ValueError("Clicked outside NDVI valid data")

            # Scale NDVI if needed (e.g. 0–10000 → 0–1)
            if ndvi_value > 1:
                ndvi_value = ndvi_value / 10000.0

            ndvi_value = np.clip(ndvi_value, 0, 1)

            # Growth stage classification
            if ndvi_value < 0.3:
                growth_stage = "🌱 Bare / Early Sowing"
                stage_color = "red"
            elif 0.3 <= ndvi_value < 0.6:
                growth_stage = "🌿 Active Growth"
                stage_color = "orange"
            else:
                growth_stage = "🌾 Healthy / Maturity"
                stage_color = "green"

            # Soil type
            srow, scol = ~soil_transform * (lon, lat)
            srow, scol = int(srow), int(scol)
            soil_value = soil_data[srow, scol]

            if soil_nodata is not None and soil_value == soil_nodata:
                soil_type = "Unknown"
            else:
                soil_type = f"Soil class {soil_value}"

            # Show results
            st.subheader("📌 Results for Selected Location")
            col1, col2 = st.columns(2)

            with col1:
                st.metric("NDVI", f"{ndvi_value:.2f}")
                st.markdown(f"<p style='color:{stage_color};font-size:20px'>{growth_stage}</p>", unsafe_allow_html=True)

            with col2:
                st.metric("Soil Type", soil_type)
                st.markdown("🌍 Location: {:.4f}, {:.4f}".format(lat, lon))

        except Exception as e:
            st.error(f"Error reading raster: {e}")

else:
    st.info("⬅️ Please upload both NDVI and Soil raster files to begin.")

