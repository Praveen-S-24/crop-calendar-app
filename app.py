import streamlit as st
import rasterio
import folium
from streamlit_folium import st_folium
import numpy as np

st.set_page_config(page_title="Crop Growth & Soil App", layout="wide")
st.title("🌾 Crop Growth & Soil Detection App")

# Paths to datasets inside repo
ndvi_path = "ocm2_ndvi_filt_16to30_jun2021_v01_01.tif"   # <-- upload this file to repo
soil_paths = {
    "Clayey": "fclayey.asc",
    "Clay Skeletal": "fclayskeletal.asc",
    "Loamy": "floamy.asc",
    "Sandy": "fsandy.asc"
}

try:
    with rasterio.open(ndvi_path) as ndvi_ds:
        ndvi_data = ndvi_ds.read(1)
        ndvi_transform = ndvi_ds.transform
        ndvi_nodata = ndvi_ds.nodata
        ndvi_bounds = ndvi_ds.bounds

    # Map
    center_lat = (ndvi_bounds.top + ndvi_bounds.bottom) / 2
    center_lon = (ndvi_bounds.left + ndvi_bounds.right) / 2
    m = folium.Map(location=[center_lat, center_lon], zoom_start=7)
    st_map = st_folium(m, width=700, height=500)

    if st_map and st_map.get("last_clicked"):
        lon, lat = st_map["last_clicked"]["lng"], st_map["last_clicked"]["lat"]

        # NDVI value
        row, col = ~ndvi_transform * (lon, lat)
        row, col = int(row), int(col)
        ndvi_value = ndvi_data[row, col]

        if ndvi_nodata is not None and ndvi_value == ndvi_nodata:
            st.error("Clicked outside NDVI valid data")
        else:
            if ndvi_value > 1:
                ndvi_value = ndvi_value / 10000.0
            ndvi_value = np.clip(ndvi_value, 0, 1)

            if ndvi_value < 0.3:
                growth_stage = "🌱 Bare / Early Sowing"
                stage_color = "red"
            elif 0.3 <= ndvi_value < 0.6:
                growth_stage = "🌿 Active Growth"
                stage_color = "orange"
            else:
                growth_stage = "🌾 Healthy / Maturity"
                stage_color = "green"

            # Soil detection from multiple rasters
            soil_type = "Unknown"
            for sname, spath in soil_paths.items():
                try:
                    with rasterio.open(spath) as sds:
                        srow, scol = ~sds.transform * (lon, lat)
                        srow, scol = int(srow), int(scol)
                        sval = sds.read(1)[srow, scol]
                        if sval == 1:  # presence flag
                            soil_type = sname
                            break
                except Exception:
                    continue

            # Show results
            st.subheader("📌 Results")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("NDVI", f"{ndvi_value:.2f}")
                st.markdown(f"<p style='color:{stage_color};font-size:20px'>{growth_stage}</p>", unsafe_allow_html=True)
            with col2:
                st.metric("Soil Type", soil_type)
                st.markdown("🌍 Location: {:.4f}, {:.4f}".format(lat, lon))

except Exception as e:
    st.error(f"Error loading rasters: {e}")
