import streamlit as st
import geopandas as gpd
import matplotlib.pyplot as plt
import os
import cartopy.crs as ccrs
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
import matplotlib.ticker as mticker
import io

# 페이지 설정
st.set_page_config(page_title="Professional Map Generator", layout="wide")
st.title("🗺️ Map Generator (Flat / Curved / Sphere)")

# 데이터 경로 설정
current_folder = os.path.dirname(os.path.abspath(__file__))
land_110m = os.path.join(current_folder, "ne_110m_land.shp")

@st.cache_data
def load_and_fix_data(path):
    if not os.path.exists(path):
        return None
    try:
        gdf = gpd.read_file(path)
        # 폴리곤 유효성 교정 (삼각형 깨짐 방지)
        gdf['geometry'] = gdf.geometry.buffer(0)
        return gdf
    except:
        return None

# 1. 사이드바 설정
with st.sidebar:
    st.subheader("1. Projection Style")
    # 사용자 요청대로 3가지 옵션으로 분리
    proj_choice = st.radio("Select Style", ("Flat", "Curved", "Sphere"))
    
    st.divider()
    
    st.subheader("2. Map Range / Center")
    # Flat, Curved일 때는 범위로 작동, Sphere일 때는 중심점 계산용으로 사용
    lon_min = st.number_input("Min Longitude", value=120.0, min_value=-180.0, max_value=180.0)
    lon_max = st.number_input("Max Longitude", value=135.0, min_value=-180.0, max_value=180.0)
    lat_min = st.number_input("Min Latitude", value=30.0, min_value=-90.0, max_value=90.0)
    lat_max = st.number_input("Max Latitude", value=40.0, min_value=-90.0, max_value=90.0)
    
    st.divider()
    
    st.subheader("3. Grid Settings")
    show_grid = st.radio("Show Grid Lines", ("Y", "N"), index=0)
    grid_interval = st.select_slider("Grid Interval (degrees)", options=[5, 10, 15, 20, 25, 30], value=5)

# 2. 중심점 및 로직 처리
center_lon = (lon_min + lon_max) / 2
center_lat = (lat_min + lat_max) / 2

# 데이터 로드 (모든 모드에서 110m 사용)
world_land = load_and_fix_data(land_110m)

if world_land is not None:
    # --- 모드별 투영법 설정 ---
    if proj_choice == "Sphere":
        # 사용자가 입력한 범위의 중간 지점을 정면(수직)으로 설정
        target_crs = ccrs.Orthographic(central_longitude=center_lon, central_latitude=center_lat)
        st.info(f"🌐 Sphere Mode: Centered at {center_lon:.1f}°, {center_lat:.1f}°")
    elif proj_choice == "Curved":
        target_crs = ccrs.AlbersEqualArea(central_longitude=center_lon, central_latitude=center_lat)
    else: # Flat
        target_crs = ccrs.PlateCarree()

    # 도화지 생성
    fig, ax = plt.subplots(figsize=(10, 10), dpi=300, subplot_kw={'projection': target_crs})
    ax.set_facecolor('#FFFFFF')

    # 육지 그리기 (transform 필수)
    world_land.plot(ax=ax, transform=ccrs.PlateCarree(), 
                    color='#E0E0E0', edgecolor='#AAAAAA', linewidth=0.3)

    # 범위 설정
    if proj_choice == "Sphere":
        ax.set_global() # 지구본은 전체를 보여줌
        # 정중앙 표시 (선택 사항: 원치 않으시면 아래 줄을 삭제하세요)
        ax.plot(center_lon, center_lat, 'ro', markersize=4, transform=ccrs.PlateCarree())
    else:
        # Flat, Curved는 입력한 범위만큼 확대
        ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())

    # 격자선 설정 (실선)
    if show_grid == 'Y':
        # Sphere 모드에서는 라벨을 끄는 것이 깔끔함
        draw_labs = True if proj_choice != "Sphere" else False
        gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=draw_labs,
                          linestyle='-', linewidth=0.5, color='#AAAAAA', alpha=0.5)
        gl.xlocator = mticker.MultipleLocator(grid_interval)
        gl.ylocator = mticker.MultipleLocator(grid_interval)
        
        if draw_labs:
            gl.top_labels = False
            gl.right_labels = False
            gl.xformatter = LONGITUDE_FORMATTER
            gl.yformatter = LATITUDE_FORMATTER

    st.pyplot(fig)

    # 다운로드
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches='tight', pad_inches=0.1)
    st.download_button(label="📥 Download Map", data=buf.getvalue(), file_name="map.png")
else:
    st.error("Data file (ne_110m_land.shp) not found in repository.")
