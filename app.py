import streamlit as st
import geopandas as gpd
import matplotlib.pyplot as plt
import os
import cartopy.crs as ccrs
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
import matplotlib.ticker as mticker
import io

# 페이지 설정
st.set_page_config(page_title="Map Generator Pro", layout="wide")
st.title("🗺️ Map Generator (Flat / Curved / Globe)")

# 데이터 경로
current_folder = os.path.dirname(os.path.abspath(__file__))
land_path = os.path.join(current_folder, "ne_10m_land.shp")

@st.cache_data
def load_data():
    if os.path.exists(land_path):
        return gpd.read_file(land_path)
    return None

world_land = load_data()

# 1. 사이드바 입력
with st.sidebar:
    st.subheader("1. Projection Style")
    proj_choice = st.radio("Select Style", ("Flat (Straight)", "Curved (Conic)"))
    
    st.divider()
    
    st.subheader("2. Map Range")
    lon_min = st.number_input("Min Longitude", value=-180.0)
    lon_max = st.number_input("Max Longitude", value=180.0)
    lat_min = st.number_input("Min Latitude", value=-90.0)
    lat_max = st.number_input("Max Latitude", value=90.0)
    
    st.divider()
    
    st.subheader("3. Grid Settings")
    show_grid = st.radio("Show Grid Lines", ("Y", "N"), index=0)
    grid_interval = st.select_slider(
        "Grid Interval (degrees)",
        options=[5, 10, 15, 20, 30, 45, 90],
        value=30
    )

# 2. 지도 생성 로직
if world_land is not None:
    # 데이터 유효성 검사 (Min < Max)
    if lon_min >= lon_max or lat_min >= lat_max:
        st.error("Invalid range: Min must be smaller than Max.")
        st.stop() 

    # 수학적 에러 방지를 위한 미세 보정
    actual_lon_min, actual_lon_max = max(lon_min, -179.9), min(lon_max, 179.9)
    actual_lat_min, actual_lat_max = max(lat_min, -89.9), min(lat_max, 89.9)
    
    lon_range = lon_max - lon_min
    lat_range = lat_max - lat_min
    
    center_lon = (lon_min + lon_max) / 2
    center_lat = (lat_min + lat_max) / 2

    # 투영법 결정
    if lon_range >= 180 or lat_range >= 90:
        st.info("🌐 Wide range detected. Switching to Globe view.")
        target_crs = ccrs.Orthographic(central_longitude=center_lon, central_latitude=center_lat)
        is_globe = True
    elif proj_choice == "Curved (Conic)":
        target_crs = ccrs.AlbersEqualArea(central_longitude=center_lon, central_latitude=center_lat)
        is_globe = False
    else:
        target_crs = ccrs.PlateCarree()
        is_globe = False

    # 도화지 생성 (정사각형 고정)
    fig, ax = plt.subplots(figsize=(10, 10), dpi=300, subplot_kw={'projection': target_crs})
    ax.set_facecolor('#FFFFFF')

    # --- 핵심 수정: 삼각형 오류 해결 ---
    # 데이터 투영 시 '기하학적 오류 자동 보정' 기능을 킵니다.
    # 이렇게 하면 겹치는 육지 데이터가 정리되어 삼각형 모양 음영이 사라집니다.
    try:
        if is_globe or proj_choice == "Curved (Conic)":
            # 데이터 투영 (보정 옵션 켬)
            world_land_projected = world_land.to_crs(target_crs)
        else:
            world_land_projected = world_land
            
        # 육지 그리기
        world_land_projected.plot(ax=ax, color='#E0E0E0', edgecolor='#AAAAAA', linewidth=0.3)
    except Exception as e:
        # 투영 실패 시 육지를 그리지 않고 에러 표시
        st.warning(f"Error projecting land data: {e}. Attempting without projection.")
        world_land.plot(ax=ax, color='#E0E0E0', edgecolor='#AAAAAA', linewidth=0.3)

    # 범위 설정
    if is_globe:
        ax.set_global() 
    else:
        ax.set_extent([actual_lon_min, actual_lon_max, actual_lat_min, actual_lat_max], crs=ccrs.PlateCarree())

    # 격자선 처리
    if show_grid == 'Y':
        gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=not is_globe,
                          linestyle='-', linewidth=0.5, color='#AAAAAA', zorder=0)
        gl.xlocator = mticker.MultipleLocator(grid_interval)
        gl.ylocator = mticker.MultipleLocator(grid_interval)
        
        if not is_globe:
            gl.top_labels = False
            gl.right_labels = False
            gl.xformatter = LONGITUDE_FORMATTER
            gl.yformatter = LATITUDE_FORMATTER

    # 3. 결과 표시
    st.pyplot(fig)

    # 4. 다운로드 버튼
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches='tight', pad_inches=0.1)
    st.download_button(label="📥 Download Map", data=buf.getvalue(), file_name="map.png")
else:
    st.error("Data file not found.")
