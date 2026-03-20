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

# 페이지 설정
st.set_page_config(page_title="Ultra Fast Map Generator", layout="wide")
st.title("🚀 Optimized Map Generator (Fast Curved Mode)")

# 데이터 경로
current_folder = os.path.dirname(os.path.abspath(__file__))
land_10m = os.path.join(current_folder, "ne_10m_land.shp")
land_110m = os.path.join(current_folder, "ne_110m_land.shp")

@st.cache_data
def load_data(path):
    if not os.path.exists(path): return None
    return gpd.read_file(path)

# 1. 사이드바 설정
with st.sidebar:
    st.subheader("1. Projection Style")
    proj_choice = st.radio("Select Style", ("Flat", "Curved", "Sphere"))
    
    st.divider()
    
    st.subheader("2. Map Range / Center")
    lon_min = st.number_input("Min Longitude", value=124.0)
    lon_max = st.number_input("Max Longitude", value=132.0)
    lat_min = st.number_input("Min Latitude", value=33.0)
    lat_max = st.number_input("Max Latitude", value=39.0)
    
    st.divider()
    
    st.subheader("3. Grid Settings")
    show_grid = st.radio("Show Grid Lines", ("Y", "N"), index=0)
    grid_interval = st.select_slider("Grid Interval", options=[5, 10, 15, 20, 25, 30], value=5)

# 2. 로직 처리
center_lon = (lon_min + lon_max) / 2
center_lat = (lat_min + lat_max) / 2

# 데이터 선택 (Sphere만 110m, 나머지는 10m)
target_path = land_110m if proj_choice == "Sphere" else land_10m
world_land = load_data(target_path)

if world_land is not None:
    # --- 핵심 1: 강력한 Clipping (계산량 감소) ---
    if proj_choice != "Sphere":
        # 현재 화면 범위보다 아주 살짝만 넓게 잘라내어 CPU 부하를 방지합니다.
        clip_margin = 1.0 
        clip_box = box(lon_min - clip_margin, lat_min - clip_margin, 
                       lon_max + clip_margin, lat_max + clip_margin)
        # 잘라낸 데이터만 가지고 다음 단계로 넘어갑니다.
        world_land = world_land.clip(clip_box)

    # --- 투영법 설정 ---
    if proj_choice == "Sphere":
        target_crs = ccrs.Orthographic(central_longitude=center_lon, central_latitude=center_lat)
    elif proj_choice == "Curved":
        # Curved 모드는 연산이 무거우므로 미리 잘린 데이터만 사용하게 됨
        target_crs = ccrs.AlbersEqualArea(central_longitude=center_lon, central_latitude=center_lat)
    else:
        target_crs = ccrs.PlateCarree()

    # --- 핵심 2: 미리보기 DPI 최적화 ---
    # 화면 로딩 속도를 위해 미리보기 DPI를 70~80으로 유지합니다.
    if proj_choice == "Flat":
        aspect = 1 / np.cos(np.radians(center_lat))
        data_ratio = (lon_max - lon_min) / (lat_max - lat_min)
        fig_width = 10
        fig_height = fig_width / (data_ratio / aspect)
        fig, ax = plt.subplots(figsize=(fig_width, min(fig_height, 15)), dpi=75, subplot_kw={'projection': target_crs})
    else:
        fig, ax = plt.subplots(figsize=(10, 10), dpi=75, subplot_kw={'projection': target_crs})

    ax.set_facecolor('#FFFFFF')

    # 육지 그리기 (이미 클리핑된 상태라 훨씬 빠름)
    world_land.plot(ax=ax, transform=ccrs.PlateCarree(), color='#E0E0E0', edgecolor='#AAAAAA', linewidth=0.3)

    if proj_choice == "Sphere":
        ax.set_global()
    else:
        ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())

    # 격자선 (실선)
    if show_grid == 'Y':
        draw_labs = True if proj_choice != "Sphere" else False
        gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=draw_labs, linestyle='-', linewidth=0.5, color='#AAAAAA')
        gl.xlocator = mticker.MultipleLocator(grid_interval)
        gl.ylocator = mticker.MultipleLocator(grid_interval)
        if draw_labs:
            gl.top_labels = gl.right_labels = False
            gl.xformatter, gl.yformatter = LONGITUDE_FORMATTER, LATITUDE_FORMATTER

    # 화면 로딩
    st.pyplot(fig)

    # 고해상도 다운로드 (300 DPI)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches='tight', dpi=300)
    st.download_button("📥 Download 300 DPI Image", data=buf.getvalue(), file_name="map_highres.png")

else:
    st.error("Data files not found.")
