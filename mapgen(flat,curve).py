import streamlit as st
import geopandas as gpd
import matplotlib.pyplot as plt
import os
import io
import cartopy.crs as ccrs
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
import matplotlib.ticker as mticker
import numpy as np
from shapely.geometry import box

# 1. 페이지 설정
st.set_page_config(page_title="Universal High-Res Map Pro", layout="wide")
st.title("🌍 Universal High-Res Map (Correct Shape)")

# 2. 데이터 로드
current_folder = os.path.dirname(os.path.abspath(__file__))
land_path = os.path.join(current_folder, "ne_10m_land.shp")

@st.cache_data
def load_data():
    if os.path.exists(land_path):
        return gpd.read_file(land_path)
    return None

world_land = load_data()

# 3. 사이드바 설정
with st.sidebar:
    st.header("🛠️ Settings")
    proj_choice = st.radio("Select Style", ("Curved", "Flat"))
    
    st.divider()
    
    st.subheader("📍 Map Range")
    lon_min = st.number_input("Min Longitude", value=115.0)
    lon_max = st.number_input("Max Longitude", value=145.0)
    lat_min = st.number_input("Min Latitude", value=25.0)
    lat_max = st.number_input("Max Latitude", value=55.0)
    
    st.divider()
    
    st.subheader("📏 Grid Settings (Individual)")
    show_grid = st.radio("Show Grid Lines", ("Y", "N"), index=0)
    lon_interval = st.select_slider("Longitude Interval", options=[1, 2, 5, 10, 20], value=10)
    lat_interval = st.select_slider("Latitude Interval", options=[1, 2, 5, 10, 20], value=10)

# 4. 지도 생성 로직
if world_land is not None:
    lat_diff = lat_max - lat_min
    lon_diff = lon_max - lon_min
    center_lon = (lon_min + lon_max) / 2
    center_lat = (lat_min + lat_max) / 2

    # Clipping
    clip_box = box(lon_min - 2, lat_min - 2, lon_max + 2, lat_max + 2)
    world_land_clipped = world_land.clip(clip_box)

    # --- 투영법 설정 ---
    if proj_choice == "Curved":
        p1 = lat_min + (lat_diff * 0.25)
        p2 = lat_min + (lat_diff * 0.75)
        target_crs = ccrs.AlbersEqualArea(central_longitude=center_lon, 
                                           central_latitude=center_lat, 
                                           standard_parallels=(p1, p2))
        
        # 🛠️ [핵심] Curved는 땅 모양 보정을 아예 제거 (순정 비율 사용)
        # 대신 도화지만 약간 가로로 긴 형태(12x9)로 잡아 안정감을 줌
        fig = plt.figure(figsize=(12, 9), dpi=90)
        
    else:
        target_crs = ccrs.PlateCarree()
        # Flat은 땅이 옆으로 퍼지므로 수동 보정(aspect) 유지
        aspect = 1 / np.cos(np.radians(center_lat))
        fig_width = 12
        fig_height = fig_width / ((lon_diff / lat_diff) / aspect)
        fig = plt.figure(figsize=(fig_width, min(fig_height, 15)), dpi=90)

    ax = fig.add_subplot(1, 1, 1, projection=target_crs)
    ax.set_facecolor('#FFFFFF')

    # 육지 그리기
    world_land_clipped.plot(ax=ax, transform=ccrs.PlateCarree(), 
                            color='#E0E0E0', edgecolor='#AAAAAA', linewidth=0.3)
    
    # 맵 범위 고정
    ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())

    # 격자선 설정
    if show_grid == 'Y':
        gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=True, 
                          linestyle='--', linewidth=0.5, color='#AAAAAA', alpha=0.7)
        gl.top_labels = gl.right_labels = False
        gl.xformatter, gl.yformatter = LONGITUDE_FORMATTER, LATITUDE_FORMATTER
        gl.xlocator = mticker.MultipleLocator(lon_interval)
        gl.ylocator = mticker.MultipleLocator(lat_interval)

    # 결과 표시
    st.pyplot(fig, clear_figure=True)

    # 다운로드 (300 DPI)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches='tight', dpi=300, facecolor='#FFFFFF')
    st.download_button(label="📥 Download Map (300 DPI)", data=buf.getvalue(), file_name="map.png")
