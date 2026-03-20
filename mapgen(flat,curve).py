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
st.set_page_config(page_title="Ultimate Curved Map", layout="wide")
st.title("🎡 Ultimate Curved Grid Map")

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
    lon_min = st.number_input("Min Longitude", value=120.0)
    lon_max = st.number_input("Max Longitude", value=135.0)
    lat_min = st.number_input("Min Latitude", value=-20.0)
    lat_max = st.number_input("Max Latitude", value=20.0)
    
    st.divider()
    
    st.subheader("📏 Grid Intervals")
    show_grid = st.radio("Show Grid Lines", ("Y", "N"), index=0)
    lon_interval = st.slider("Lon Interval", 1, 30, 5)
    lat_interval = st.slider("Lat Interval", 1, 30, 5)

# 4. 지도 생성 로직
if world_land is not None:
    center_lon = (lon_min + lon_max) / 2
    center_lat = (lat_min + lat_max) / 2

    # --- [핵심] 투영법 설정 ---
    if proj_choice == "Curved":
        # Orthographic은 지구본을 바라보는 시점으로, 어떤 위도에서도 격자가 곡선으로 나옵니다.
        # 적도를 통과해도 절대 에러가 나지 않는 가장 강력한 곡선 투영법입니다.
        target_crs = ccrs.Orthographic(central_longitude=center_lon, 
                                       central_latitude=center_lat)
    else:
        target_crs = ccrs.PlateCarree()

    # 도화지 비율 설정 (가로로 긴 기상 지도 스타일)
    fig = plt.figure(figsize=(12, 8), dpi=100)
    ax = fig.add_subplot(1, 1, 1, projection=target_crs)
    ax.set_facecolor('#FFFFFF')

    # 육지 데이터 그리기
    clip_box = box(lon_min - 10, lat_min - 10, lon_max + 10, lat_max + 10)
    world_land_clipped = world_land.clip(clip_box)
    world_land_clipped.plot(ax=ax, transform=ccrs.PlateCarree(), 
                            color='#E0E0E0', edgecolor='#AAAAAA', linewidth=0.5)
    
    # 맵 범위 고정
    ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())

    # 격자선 설정 (곡선미 극대화)
    if show_grid == 'Y':
        gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=True, 
                          linestyle='-', linewidth=0.6, color='#888888', alpha=0.6)
        gl.top_labels = gl.right_labels = False
        gl.xformatter, gl.yformatter = LONGITUDE_FORMATTER, LATITUDE_FORMATTER
        gl.xlocator = mticker.MultipleLocator(lon_interval)
        gl.ylocator = mticker.MultipleLocator(lat_interval)
        # 라벨 스타일
        gl.xlabel_style = {'size': 10}
        gl.ylabel_style = {'size': 10}

    st.pyplot(fig, clear_figure=True)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches='tight', dpi=300)
    st.download_button(label="📥 Download Map", data=buf.getvalue(), file_name="final_curved_map.png")
else:
    st.error("⚠️ 데이터 파일이 없습니다.")
