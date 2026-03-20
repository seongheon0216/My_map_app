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
st.set_page_config(page_title="Stable Curved Map", layout="wide")
st.title("🎡 Stable Curved Grid Map (Error-Free)")

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
    lat_min = st.number_input("Min Latitude", value=-30.0)
    lat_max = st.number_input("Max Latitude", value=30.0)
    
    st.divider()
    
    st.subheader("📏 Grid Intervals (Fixed Steps)")
    show_grid = st.radio("Show Grid Lines", ("Y", "N"), index=0)
    # 🛠️ 요청사항: 위경도 간격 분리 및 5, 10, 15 고정
    lon_interval = st.select_slider("Longitude Interval", options=[5, 10, 15, 30], value=10)
    lat_interval = st.select_slider("Latitude Interval", options=[5, 10, 15, 30], value=10)

# 4. 지도 생성 로직
if world_land is not None:
    lat_diff = lat_max - lat_min
    lon_diff = lon_max - lon_min
    center_lon = (lon_min + lon_max) / 2
    center_lat = (lat_min + lat_max) / 2

    # --- [핵심] 위도 범위에 따른 에러 방지 로직 ---
    if proj_choice == "Curved":
        # 🛠️ 위도 간격이 넓을 때(예: 60도 이상) 발생하는 수학적 충돌 방지
        # 표준 위도(parallels)를 실제 범위보다 안쪽으로 좁혀서 안정성을 확보합니다.
        p1 = lat_min + (lat_diff * 0.1)
        p2 = lat_max - (lat_diff * 0.1)
        
        # 적도 대칭(-30 ~ 30 등)일 때 무한대 발산 에러 방지용 미세 보정
        if abs(p1 + p2) < 0.1: p1 -= 0.5 
        
        # LambertConformal이 Albers보다 광범위 위도에서 에러에 강합니다.
        target_crs = ccrs.LambertConformal(central_longitude=center_lon, 
                                           central_latitude=center_lat,
                                           standard_parallels=(p1, p2))
    else:
        target_crs = ccrs.PlateCarree()

    # --- 도화지 비율 보정 ---
    cos_lat = np.cos(np.radians(center_lat))
    aspect = (lon_diff * cos_lat) / lat_diff
    fig_width = 12
    fig_height = fig_width / aspect
    if proj_choice == "Curved": fig_height *= 0.8
    
    fig = plt.figure(figsize=(fig_width, min(fig_height, 15)), dpi=100)
    ax = fig.add_subplot(1, 1, 1, projection=target_crs)
    ax.set_facecolor('#FFFFFF')

    # 육지 그리기
    clip_box = box(lon_min - 10, lat_min - 10, lon_max + 10, lat_max + 10)
    world_land_clipped = world_land.clip(clip_box)
    world_land_clipped.plot(ax=ax, transform=ccrs.PlateCarree(), 
                            color='#E5E5E5', edgecolor='#888888', linewidth=0.5)
    
    ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())

    # --- 격자선 설정 (요청하신 개별 간격 적용) ---
    if show_grid == 'Y':
        gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=True, 
                          linestyle='-', linewidth=0.6, color='#AAAAAA', alpha=0.5)
        gl.top_labels = gl.right_labels = False
        gl.xformatter, gl.yformatter = LONGITUDE_FORMATTER, LATITUDE_FORMATTER
        gl.xlocator = mticker.MultipleLocator(lon_interval)
        gl.ylocator = mticker.MultipleLocator(lat_interval)

    # 5. 결과 표시
    st.pyplot(fig, clear_figure=True)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches='tight', dpi=300)
    st.download_button(label="📥 Download Map", data=buf.getvalue(), file_name="stable_map.png")
else:
    st.error("데이터 파일을 확인해주세요.")
