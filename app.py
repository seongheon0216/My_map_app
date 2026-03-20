import streamlit as st
import geopandas as gpd
import matplotlib.pyplot as plt
import os
import cartopy.crs as ccrs
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
import matplotlib.ticker as mticker
import io
from shapely.geometry import Polygon

# 페이지 설정
st.set_page_config(page_title="Professional Map Generator", layout="wide")
st.title("🗺️ Map Generator (Auto-Switching)")

# 데이터 경로 설정
current_folder = os.path.dirname(os.path.abspath(__file__))
land_10m = os.path.join(current_folder, "ne_10m_land.shp")
land_110m = os.path.join(current_folder, "ne_110m_land.shp")

@st.cache_data
def load_and_fix_data(path, is_globe=False):
    if not os.path.exists(path):
        return None
    try:
        gdf = gpd.read_file(path)
        # 모든 도형을 유효하게 교정
        gdf['geometry'] = gdf.geometry.buffer(0)
        return gdf
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

# 1. 사이드바 입력
with st.sidebar:
    st.subheader("1. Projection Style")
    proj_choice = st.radio("Select Style", ("Flat (Straight)", "Curved (Conic)"))
    
    st.divider()
    
    st.subheader("2. Map Range")
    lon_min = st.number_input("Min Longitude", value=-180.0, min_value=-180.0, max_value=180.0)
    lon_max = st.number_input("Max Longitude", value=180.0, min_value=-180.0, max_value=180.0)
    lat_min = st.number_input("Min Latitude", value=-90.0, min_value=-90.0, max_value=90.0)
    lat_max = st.number_input("Max Latitude", value=90.0, min_value=-90.0, max_value=90.0)
    
    st.divider()
    
    st.subheader("3. Grid Settings")
    show_grid = st.radio("Show Grid Lines", ("Y", "N"), index=0)
    grid_interval = st.select_slider(
        "Grid Interval (degrees)",
        options=[5, 10, 15, 20, 25, 30],
        value=30
    )

# 2. 로직 처리
lon_range = abs(lon_max - lon_min)
lat_range = abs(lat_max - lat_min)
# 전체 범위를 커버하거나 지구가 둥글게 보여야 할 때
is_max_range = lon_range >= 170.0 or lat_range >= 85.0

# 데이터 로드
target_path = land_110m if is_max_range else land_10m
world_land = load_and_fix_data(target_path, is_globe=is_max_range)

if world_land is not None:
    # 중심 좌표 계산
    center_lon = (lon_min + lon_max) / 2
    center_lat = (lat_min + lat_max) / 2

    # 투영법 결정
    if is_max_range:
        target_crs = ccrs.Orthographic(central_longitude=center_lon, central_latitude=center_lat)
    elif proj_choice == "Curved (Conic)":
        target_crs = ccrs.AlbersEqualArea(central_longitude=center_lon, central_latitude=center_lat)
    else:
        target_crs = ccrs.PlateCarree()

    # 도화지 생성
    fig, ax = plt.subplots(figsize=(10, 10), dpi=300, subplot_kw={'projection': target_crs})
    ax.set_facecolor('#FFFFFF')

    # 육지 그리기 (도형 꼬임 방지를 위한 전처리 포함)
    try:
        # 데이터 출력
        world_land.plot(ax=ax, transform=ccrs.PlateCarree(), 
                        color='#E0E0E0', edgecolor='#AAAAAA', linewidth=0.3)
    except Exception as e:
        st.warning(f"Display error: {e}")

    # 범위 설정 (ValueError 방지 로직)
    if is_max_range:
        ax.set_global()
    else:
        # 미세하게 범위를 좁혀 에러 방지
        ax.set_extent([lon_min + 0.01, lon_max - 0.01, lat_min + 0.01, lat_max - 0.01], 
                      crs=ccrs.PlateCarree())

    # 격자선 설정
    if show_grid == 'Y':
        # linestyle='-' 로 실선 설정
        gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=not is_max_range,
                          linestyle='-', linewidth=0.5, color='#AAAAAA', alpha=0.5)
        gl.xlocator = mticker.MultipleLocator(grid_interval)
        gl.ylocator = mticker.MultipleLocator(grid_interval)
        
        if not is_max_range:
            gl.top_labels = False
            gl.right_labels = False
            gl.xformatter = LONGITUDE_FORMATTER
            gl.yformatter = LATITUDE_FORMATTER

    st.pyplot(fig)

    # 다운로드 버튼
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches='tight', pad_inches=0.1)
    st.download_button(label="📥 Download Map", data=buf.getvalue(), file_name="custom_map.png")
else:
    st.error("Data file not found. Please check your GitHub repository.")
