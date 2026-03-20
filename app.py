import streamlit as st
import geopandas as gpd
import matplotlib.pyplot as plt
import os
import cartopy.crs as ccrs
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
import matplotlib.ticker as mticker
import io
import numpy as np
from shapely.geometry import box

st.set_page_config(page_title="Fast Detail Map", layout="wide")
st.title("⚡ Flat & Curved Detail Map (10m)")

# 데이터 경로 (10m 고정)
current_folder = os.path.dirname(os.path.abspath(__file__))
land_10m = os.path.join(current_folder, "ne_10m_land.shp")

@st.cache_data
def load_data(path):
    if not os.path.exists(path): return None
    return gpd.read_file(path)

with st.sidebar:
    st.subheader("1. Style")
    proj_choice = st.radio("Select Style", ("Flat", "Curved"))
    
    st.subheader("2. Range")
    lon_min = st.number_input("Min Longitude", value=124.0)
    lon_max = st.number_input("Max Longitude", value=132.0)
    lat_min = st.number_input("Min Latitude", value=33.0)
    lat_max = st.number_input("Max Latitude", value=39.0)
    
    st.subheader("3. Grid")
    grid_interval = st.select_slider("Interval", options=[1, 5, 10], value=5)

# 로직 실행
center_lon, center_lat = (lon_min + lon_max) / 2, (lat_min + lat_max) / 2
world_land = load_data(land_10m)

if world_land is not None:
    # --- 강력한 Clipping (이게 속도의 핵심입니다) ---
    clip_box = box(lon_min - 1, lat_min - 1, lon_max + 1, lat_max + 1)
    world_land = world_land.clip(clip_box)

    # 투영법 설정
    target_crs = ccrs.AlbersEqualArea(center_lon, center_lat) if proj_choice == "Curved" else ccrs.PlateCarree()

    # 비율 보정 및 도화지 생성
    aspect = 1 / np.cos(np.radians(center_lat)) if proj_choice == "Flat" else 1.0
    data_ratio = (lon_max - lon_min) / (lat_max - lat_min)
    fig_width = 10
    fig_height = fig_width / (data_ratio / aspect)
    
    fig, ax = plt.subplots(figsize=(fig_width, min(fig_height, 15)), dpi=80, subplot_kw={'projection': target_crs})
    ax.set_facecolor('#FFFFFF')

    # 그리기
    world_land.plot(ax=ax, transform=ccrs.PlateCarree(), color='#E0E0E0', edgecolor='#AAAAAA', linewidth=0.3)
    ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())

    # 격자선 (실선)
    gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=True, linestyle='-', linewidth=0.5, color='#AAAAAA')
    gl.top_labels = gl.right_labels = False
    gl.xlocator = mticker.MultipleLocator(grid_interval)
    gl.ylocator = mticker.MultipleLocator(grid_interval)
    gl.xformatter, gl.yformatter = LONGITUDE_FORMATTER, LATITUDE_FORMATTER

    st.pyplot(fig)

    # 300 DPI 다운로드
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches='tight', dpi=300)
    st.download_button("📥 Download 300 DPI", data=buf.getvalue(), file_name="detail_map.png")
