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
st.set_page_config(page_title="Universal Map Pro", layout="wide")
st.title("🌍 Universal Map Generator (Error-Free Version)")

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
    lon_min = st.number_input("Min Longitude", value=90.0)
    lon_max = st.number_input("Max Longitude", value=150.0)
    lat_min = st.number_input("Min Latitude", value=-20.0)
    lat_max = st.number_input("Max Latitude", value=20.0)
    
    st.divider()
    
    st.subheader("📏 Grid Settings")
    show_grid = st.radio("Show Grid Lines", ("Y", "N"), index=0)
    lon_interval = st.select_slider("Longitude Interval", options=[1, 2, 5, 10, 15, 30], value=10)
    lat_interval = st.select_slider("Latitude Interval", options=[1, 2, 5, 10, 15, 30], value=10)

# 4. 지도 생성 로직
if world_land is not None:
    lat_diff = lat_max - lat_min
    lon_diff = lon_max - lon_min
    center_lon = (lon_min + lon_max) / 2
    center_lat = (lat_min + lat_max) / 2

    # --- [에러 방지 핵심] 범위에 따른 투영법 강제 보정 ---
    if proj_choice == "Curved":
        # 적도를 포함하거나 위도 범위가 60도 이상이면 Mercator 기반 곡선 투영법 사용
        if lat_min * lat_max <= 0 or lat_diff > 60:
            target_crs = ccrs.Mercator(central_longitude=center_lon)
        else:
            p1, p2 = lat_min + lat_diff * 0.2, lat_max - lat_diff * 0.2
            target_crs = ccrs.LambertConformal(central_longitude=center_lon, 
                                               central_latitude=center_lat,
                                               standard_parallels=(p1, p2))
    else:
        target_crs = ccrs.PlateCarree()

    # --- 도화지 비율(figsize) 보정 ---
    # 위도 보정 계수 (적도 부근에서 대륙 찌그러짐 방지)
    aspect = 1 / np.cos(np.radians(center_lat))
    fig_width = 12
    # 수동 비율 조정: Curved 모드일 때 위아래가 길어지지 않게 강제로 0.8배 압축
    fig_height = (fig_width / ((lon_diff / lat_diff) / aspect))
    if proj_choice == "Curved":
        fig_height *= 0.8 

    fig = plt.figure(figsize=(fig_width, min(fig_height, 15)), dpi=100)
    ax = fig.add_subplot(1, 1, 1, projection=target_crs)
    ax.set_facecolor('#FFFFFF')

    # 데이터 클리핑 및 그리기
    clip_box = box(lon_min - 5, lat_min - 5, lon_max + 5, lat_max + 5)
    world_land_clipped = world_land.clip(clip_box)
    
    world_land_clipped.plot(ax=ax, transform=ccrs.PlateCarree(), 
                            color='#E0E0E0', edgecolor='#AAAAAA', linewidth=0.3)
    
    ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())

    # 격자선 처리 (실선)
    if show_grid == 'Y':
        gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=True, 
                          linestyle='-', linewidth=0.5, color='#AAAAAA', alpha=0.7)
        gl.top_labels = gl.right_labels = False
        gl.xformatter, gl.yformatter = LONGITUDE_FORMATTER, LATITUDE_FORMATTER
        gl.xlocator = mticker.MultipleLocator(lon_interval)
        gl.ylocator = mticker.MultipleLocator(lat_interval)

    st.pyplot(fig, clear_figure=True)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches='tight', dpi=300, facecolor='#FFFFFF')
    st.download_button(label="📥 Download Map", data=buf.getvalue(), file_name="map.png")
else:
    st.error("⚠️ 데이터 파일이 없습니다.")
