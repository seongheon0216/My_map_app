import streamlit as st
import geopandas as gpd
import matplotlib.pyplot as plt
import os
import cartopy.crs as ccrs
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
import matplotlib.ticker as mticker
import io
import numpy as np

# 페이지 설정
st.set_page_config(page_title="High-Res Map Generator", layout="wide")
st.title("Map Generator")

# 데이터 경로
current_folder = os.path.dirname(os.path.abspath(__file__))
land_10m = os.path.join(current_folder, "ne_10m_land.shp")
land_110m = os.path.join(current_folder, "ne_110m_land.shp")

@st.cache_data
def load_data(path):
    if not os.path.exists(path): return None
    # 10m 데이터는 무거우므로 로딩 시 캐싱을 확실히 활용합니다.
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

# 2. 중심점 및 데이터 선택
center_lon = (lon_min + lon_max) / 2
center_lat = (lat_min + lat_max) / 2

# Flat/Curved는 10m(상세), Sphere는 110m(구형 최적화) 사용
target_path = land_110m if proj_choice == "Sphere" else land_10m
world_land = load_data(target_path)

if world_land is not None:
    # --- 투영법 설정 ---
    if proj_choice == "Sphere":
        target_crs = ccrs.Orthographic(central_longitude=center_lon, central_latitude=center_lat)
    elif proj_choice == "Curved":
        target_crs = ccrs.AlbersEqualArea(central_longitude=center_lon, central_latitude=center_lat)
    else:
        target_crs = ccrs.PlateCarree()

    # --- 가로세로 비율 보정 (Flat 모드) ---
    if proj_choice == "Flat":
        aspect = 1 / np.cos(np.radians(center_lat))
        data_ratio = (lon_max - lon_min) / (lat_max - lat_min)
        fig_width = 10
        fig_height = fig_width / (data_ratio / aspect)
        # 화면 출력용 Fig 생성 (DPI 낮춤)
        fig, ax = plt.subplots(figsize=(fig_width, min(fig_height, 15)), dpi=80, subplot_kw={'projection': target_crs})
    else:
        fig, ax = plt.subplots(figsize=(10, 10), dpi=80, subplot_kw={'projection': target_crs})

    ax.set_facecolor('#FFFFFF')

    # 육지 그리기
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

    # 3. 화면 표시 (미리보기는 저해상도로 빠르게)
    st.pyplot(fig)

    # 4. 고해상도 다운로드 로직
    # 버튼을 누르는 순간 300 DPI로 다시 렌더링하여 메모리에 담습니다.
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches='tight', dpi=300)
    
    st.download_button(
        label="📥 Download Illustrator-Ready Map (300 DPI)",
        data=buf.getvalue(),
        file_name="map_highres.png",
        mime="image/png"
    )
else:
    st.error("Data file not found.")
