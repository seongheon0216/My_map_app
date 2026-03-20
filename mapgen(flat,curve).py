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
st.title("🌍 Universal Map Generator (All-Range Stable)")

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
    lon_interval = st.select_slider("Longitude Interval", options=[5, 10, 15, 30, 45], value=10)
    lat_interval = st.select_slider("Latitude Interval", options=[5, 10, 15, 30, 45], value=10)

# 4. 지도 생성 로직
if world_land is not None:
    lat_diff = lat_max - lat_min
    lon_diff = lon_max - lon_min
    center_lon = (lon_min + lon_max) / 2
    center_lat = (lat_min + lat_max) / 2

    # Clipping (여유 범위 5도 부여)
    clip_box = box(lon_min - 5, lat_min - 5, lon_max + 5, lat_max + 5)
    world_land_clipped = world_land.clip(clip_box)

    # --- [핵심] 투영법 및 비율 자동 보정 로직 ---
    if proj_choice == "Curved":
        # 적도를 포함하거나 위도 차이가 큰 경우에도 에러가 없는 LambertConformal 사용
        # 표준 위도(parallels)를 입력 범위의 1/4, 3/4 지점으로 자동 설정하여 왜곡 최소화
        p1, p2 = lat_min + lat_diff * 0.2, lat_max - lat_diff * 0.2
        
        # LambertConformal은 적도 부근에서도 Albers보다 훨씬 안정적입니다.
        target_crs = ccrs.LambertConformal(central_longitude=center_lon, 
                                           central_latitude=center_lat,
                                           standard_parallels=(p1, p2))
    else:
        target_crs = ccrs.PlateCarree()

    # --- 도화지 비율(figsize) 자동 계산 ---
    # 위도에 따른 가로 확장 계수 (적도=1, 고위도=커짐)
    aspect = 1 / np.cos(np.radians(center_lat)) if abs(center_lat) < 85 else 10
    
    fig_width = 12
    # 데이터의 실제 물리적 비율을 계산하여 세로 길이를 결정 (대륙 찌그러짐 방지)
    fig_height = fig_width / ((lon_diff / lat_diff) / aspect)
    
    # 도화지 생성 (최대 높이 15로 제한)
    fig = plt.figure(figsize=(fig_width, min(fig_height, 15)), dpi=100)
    ax = fig.add_subplot(1, 1, 1, projection=target_crs)
    ax.set_facecolor('#FFFFFF')

    # 육지 그리기
    world_land_clipped.plot(ax=ax, transform=ccrs.PlateCarree(), 
                            color='#E0E0E0', edgecolor='#AAAAAA', linewidth=0.3)
    
    # 출력 범위 고정
    ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())

    # 격자선 처리 (실선)
    if show_grid == 'Y':
        gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=True, 
                          linestyle='-', linewidth=0.5, color='#AAAAAA', alpha=0.7)
        gl.top_labels = gl.right_labels = False
        gl.xformatter, gl.yformatter = LONGITUDE_FORMATTER, LATITUDE_FORMATTER
        gl.xlocator = mticker.MultipleLocator(lon_interval)
        gl.ylocator = mticker.MultipleLocator(lat_interval)

    # 5. 결과 표시 및 다운로드
    st.pyplot(fig, clear_figure=True)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches='tight', dpi=300, facecolor='#FFFFFF')
    st.download_button(label="📥 Download Map (300 DPI)", data=buf.getvalue(), file_name="map.png")

else:
    st.error("⚠️ 데이터 파일(ne_10m_land.shp)이 폴더에 없습니다.")
