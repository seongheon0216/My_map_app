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
st.set_page_config(page_title="Universal Map Generator", layout="wide")
st.title("Map Generator(Flat/Curved)")

# 2. 데이터 로드 (10m 전세계 데이터)
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
    st.header("🛠️ Region Settings")
    proj_choice = st.radio("Select Style", ("Curved", "Flat"))
    
    st.divider()
    
    st.subheader("📍 Coordinates (Anywhere in the world)")
    lon_min = st.number_input("Min Longitude", value=120.0) # 예: 한국 기준
    lon_max = st.number_input("Max Longitude", value=135.0)
    lat_min = st.number_input("Min Latitude", value=30.0)
    lat_max = st.number_input("Max Latitude", value=45.0)
    
    st.divider()
    
    st.subheader("📏 Grid & Design")
    grid_interval = st.select_slider("Interval (deg)", options=[5, 10, 15, 20, 25, 30, 45], value=5)
    coast_width = st.slider("Coastline Width", 0.1, 1.0, 0.3)

# 4. 지도 생성 로직
if world_land is not None:
    lat_diff = lat_max - lat_min
    lon_diff = lon_max - lon_min
    center_lon = (lon_min + lon_max) / 2
    center_lat = (lat_min + lat_max) / 2

    # [보안 장치] Curved 모드 위도 한계 체크
    if proj_choice == "Curved" and lat_diff >= 120:
        st.error("❌ Curved 모드에서는 위도 범위를 120도 이내로 설정해주세요. (전세계는 Flat 권장)")
    else:
        # [속도 최적화] Clipping - 전세계 데이터 중 필요한 부분만 추출
        clip_box = box(lon_min - 2, lat_min - 2, lon_max + 2, lat_max + 2)
        world_land_clipped = world_land.clip(clip_box)

        # --- 투영법 설정 ---
        if proj_choice == "Curved":
            # 어떤 위도에서든 에러가 나지 않는 표준 위도 자동 계산
            p1 = lat_min + (lat_diff * 0.25)
            p2 = lat_min + (lat_diff * 0.75)
            target_crs = ccrs.AlbersEqualArea(central_longitude=center_lon, 
                                               central_latitude=center_lat, 
                                               standard_parallels=(p1, p2))
            
            # Curved 모드 도화지 비율 최적화 (가로 압축 방지)
            fig_width = 10
            aspect_adjust = np.cos(np.radians(center_lat)) 
            fig_height = (fig_width / (lon_diff / lat_diff)) * aspect_adjust
            fig, ax = plt.subplots(figsize=(fig_width, min(fig_height, 15)), dpi=85, subplot_kw={'projection': target_crs})
        
        else:
            target_crs = ccrs.PlateCarree()
            # Flat 모드 수동 비율 보정 (위도에 따른 가로 늘어짐 방지)
            aspect = 1 / np.cos(np.radians(center_lat))
            data_ratio = lon_diff / lat_diff
            fig_width = 10
            fig_height = fig_width / (data_ratio / aspect)
            fig, ax = plt.subplots(figsize=(fig_width, min(fig_height, 15)), dpi=85, subplot_kw={'projection': target_crs})

        # --- 그리기 ---
        ax.set_facecolor('#FFFFFF')
        world_land_clipped.plot(ax=ax, transform=ccrs.PlateCarree(), 
                                color='#E0E0E0', edgecolor='#AAAAAA', linewidth=coast_width)
        
        ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())

        # 격자선
        gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=True, 
                          linestyle='--', linewidth=0.5, color='#AAAAAA', alpha=0.7)
        gl.top_labels = gl.right_labels = False
        gl.xformatter, gl.yformatter = LONGITUDE_FORMATTER, LATITUDE_FORMATTER
        gl.xlocator = mticker.MultipleLocator(grid_interval)
        gl.ylocator = mticker.MultipleLocator(grid_interval)

        # 5. 결과 표시 및 저장
        st.pyplot(fig)

        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches='tight', dpi=300, facecolor='#FFFFFF')
        st.download_button(label="📥 Download High-Res Map (300 DPI)", 
                           data=buf.getvalue(), 
                           file_name=f"map_output.png", 
                           mime="image/png")
else:
    st.error("⚠️ 데이터 파일을 찾을 수 없습니다.")
