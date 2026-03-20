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
st.title("🌍 Universal Map Generator (Fixed Ratio & Grid)")

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
    lon_interval = st.select_slider("Longitude Interval (deg)", options=[1, 2, 5, 10, 15, 30], value=5)
    lat_interval = st.select_slider("Latitude Interval (deg)", options=[1, 2, 5, 10, 15, 30], value=5)

# 4. 지도 생성 로직
if world_land is not None:
    lat_diff = lat_max - lat_min
    lon_diff = lon_max - lon_min
    center_lon = (lon_min + lon_max) / 2
    center_lat = (lat_min + lat_max) / 2

    # [가드] Curved 모드 위도 한계 체크
    if proj_choice == "Curved" and lat_diff >= 120:
        st.error(f"❌ Curved 모드는 위도 범위를 120도 이내로 설정해야 합니다. (현재: {lat_diff:.1f}도)")
    else:
        # Clipping (속도 최적화)
        clip_box = box(lon_min - 2, lat_min - 2, lon_max + 2, lat_max + 2)
        world_land_clipped = world_land.clip(clip_box)

        # 🛠️ [비율 보정 핵심] 공통 aspect 계산
        aspect = 1 / np.cos(np.radians(center_lat))
        data_ratio = (lon_diff / lat_diff) / aspect
        fig_width = 12

        # --- 투영법 및 도화지 설정 ---
        if proj_choice == "Curved":
            p1 = lat_min + (lat_diff * 0.25)
            p2 = lat_min + (lat_diff * 0.75)
            target_crs = ccrs.AlbersEqualArea(central_longitude=center_lon, 
                                               central_latitude=center_lat, 
                                               standard_parallels=(p1, p2))
            # Curved 모드도 데이터 비율에 맞춰 세로 길이를 조절 (세로 늘어짐 방지)
            fig_height = fig_width / data_ratio
            fig = plt.figure(figsize=(fig_width, min(fig_height, 15)), dpi=100)
        else:
            target_crs = ccrs.PlateCarree()
            fig_height = fig_width / data_ratio
            fig = plt.figure(figsize=(fig_width, min(fig_height, 15)), dpi=100)

        # 🛠️ 여기서부터 그리기 로직이 들여쓰기 안에 포함되어야 합니다.
        ax = fig.add_subplot(1, 1, 1, projection=target_crs)
        ax.set_facecolor('#FFFFFF')

        # 육지 그리기
        world_land_clipped.plot(ax=ax, transform=ccrs.PlateCarree(), 
                                color='#E0E0E0', edgecolor='#AAAAAA', linewidth=0.3)
        
        # 맵 범위 고정
        ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())

        # 격자선 개별 설정 (실선 적용)
        if show_grid == 'Y':
            gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=True, 
                              linestyle='-', linewidth=0.5, color='#AAAAAA', alpha=0.7)
            gl.top_labels = gl.right_labels = False
            gl.xformatter, gl.yformatter = LONGITUDE_FORMATTER, LATITUDE_FORMATTER
            gl.xlocator = mticker.MultipleLocator(lon_interval)
            gl.ylocator = mticker.MultipleLocator(lat_interval)

        # 결과 표시
        st.pyplot(fig, clear_figure=True)

        # 다운로드 (300 DPI)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches='tight', dpi=300, facecolor='#FFFFFF')
        st.download_button(label="📥 Download Map (300 DPI)", data=buf.getvalue(), file_name="custom_map.png")
else:
    st.error("⚠️ 데이터 파일이 없습니다.")
