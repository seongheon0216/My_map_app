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

# 1. 페이지 설정 및 제목
st.set_page_config(page_title="Universal High-Res Map", layout="wide")
st.title("🌍 Universal High-Res Map Generator (Fixed Ratio)")

# 2. 데이터 로드 (전세계 데이터)
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
    proj_choice = st.radio("Select Style", ("Flat", "Curved"), help="Flat: PlateCarree / Curved: Albers Equal Area")
    
    st.divider()
    
    st.subheader("📍 Coordinates (Anywhere)")
    lon_min = st.number_input("Min Longitude", value=115.0)
    lon_max = st.number_input("Max Longitude", value=145.0)
    lat_min = st.number_input("Min Latitude", value=25.0)
    lat_max = st.number_input("Max Latitude", value=55.0)
    
    st.divider()
    
    st.subheader("📏 Grid & Design")
    show_grid = st.radio("Show Grid Lines", ("Y", "N"), index=0)
    grid_interval = st.select_slider("Interval (deg)", options=[1, 2, 5, 10], value=5)

# 4. 지도 생성 로직
if world_land is not None:
    lat_diff = lat_max - lat_min
    lon_diff = lon_max - lon_min
    center_lon = (lon_min + lon_max) / 2
    center_lat = (lat_min + lat_max) / 2

    # [보안 장치] Curved 모드 위도 한계 체크 (이전과 동일)
    if proj_choice == "Curved" and lat_diff >= 120:
        st.error(f"❌ Curved 모드는 위도 범위를 120도 이내로 설정해주세요.")
    else:
        # [속도 최적화] Clipping
        clip_box = box(lon_min - 1, lat_min - 1, lon_max + 1, lat_max + 1)
        world_land_clipped = world_land.clip(clip_box)

        # --- 투영법 설정 ---
        if proj_choice == "Curved":
            # 표준 위도 안전 설정
            p1 = lat_min + (lat_diff * 0.25)
            p2 = lat_min + (lat_diff * 0.75)
            target_crs = ccrs.AlbersEqualArea(central_longitude=center_lon, 
                                               central_latitude=center_lat, 
                                               standard_parallels=(p1, p2))
        else:
            target_crs = ccrs.PlateCarree()

        # --- [핵심 수정] 가로세로 비율(figsize) 설정 ---
        # Flat 모드와 Curved 모드 모두에 대해 수학적으로 비율을 계산합니다.
        data_ratio = lon_diff / lat_diff
        
        # 위도에 따른 왜곡 보정값 계산
        aspect = 1 / np.cos(np.radians(center_lat))
        
        fig_width = 10
        # Curved 모드와 Flat 모드 모두 이 aspect 값을 활용해 최종 세로 비율을 결정합니다.
        # 이렇게 하면 Curved 모드에서 가로로 구겨지거나 Flat 모드에서 늘어지는 현상이 사라집니다.
        fig_height = fig_width / (data_ratio / aspect)
        
        # 화면 미리보기는 속도를 위해 dpi=80
        fig, ax = plt.subplots(figsize=(fig_width, min(fig_height, 15)), dpi=80, subplot_kw={'projection': target_crs})

        # --- 지도 시각화 설정 ---
        ax.set_facecolor('#FFFFFF') # 배경색 흰색

        # 육지 그리기 (10m 정밀도 유지)
        world_land_clipped.plot(ax=ax, transform=ccrs.PlateCarree(), 
                                color='#E0E0E0', edgecolor='#AAAAAA', linewidth=0.3)
        
        # 맵 범위 고정
        ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())

        # 격자선 처리 ( météorologique 스타일 )
        if show_grid == 'Y':
            gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=True, 
                              linestyle='-', linewidth=0.5, color='#AAAAAA', alpha=0.7)
            gl.top_labels = gl.right_labels = False
            gl.xformatter, gl.yformatter = LONGITUDE_FORMATTER, LATITUDE_FORMATTER
            gl.xlocator = mticker.MultipleLocator(grid_interval)
            gl.ylocator = mticker.MultipleLocator(grid_interval)

        # 5. 결과 표시 및 고해상도 다운로드
        st.pyplot(fig)

        # 다운로드 시에만 300 DPI 렌더링
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches='tight', dpi=300, facecolor='#FFFFFF')
        
        st.download_button(label="📥 Download High-Res Map (300 DPI)", 
                           data=buf.getvalue(), 
                           file_name=f"map_output.png", 
                           mime="image/png")
else:
    st.error("⚠️ 데이터 파일을 찾을 수 없습니다.")
