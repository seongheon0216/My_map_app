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
st.title("🗺️ Map Generator")

# 데이터 경로 설정
current_folder = os.path.dirname(os.path.abspath(__file__))
land_10m = os.path.join(current_folder, "ne_10m_land.shp")
land_110m = os.path.join(current_folder, "ne_110m_land.shp")

@st.cache_data
def load_data(path):
    if os.path.exists(path):
        return gpd.read_file(path)
    return None

# 1. 사이드바 입력 설정
with st.sidebar:
    st.subheader("1. Projection Style")
    proj_choice = st.radio("Select Style", ("Flat", "Curved"))
    
    st.divider()
    
    st.subheader("2. Map Range")
    lon_min = st.number_input("Min Longitude", value=115.0, min_value=-180.0, max_value=180.0)
    lon_max = st.number_input("Max Longitude", value=145.0, min_value=-180.0, max_value=180.0)
    lat_min = st.number_input("Min Latitude", value=25.0, min_value=-90.0, max_value=90.0)
    lat_max = st.number_input("Max Latitude", value=50.0, min_value=-90.0, max_value=90.0)
    
    st.divider()
    
    st.subheader("3. Grid Settings")
    show_grid = st.radio("Show Grid Lines", ("Y", "N"), index=0)
    grid_interval = st.select_slider(
        "Grid Interval (degrees)",
        options=[5, 10, 15, 20, 25, 30],
        value=5
    )

# 2. 로직 처리
lon_range = lon_max - lon_min
lat_range = lat_max - lat_min
# 경도 180도 또는 위도 90도 이상 차이 나면 '최대 범위'로 간주
is_max_range = lon_range >= 179.9 or lat_range >= 89.9

# 파일 선택 및 데이터 로드
if is_max_range:
    world_land = load_data(land_110m)
    st.info("🌐 Max range detected: Using 110m globe data.")
else:
    world_land = load_data(land_10m)

if world_land is not None:
    center_lon = (lon_min + lon_max) / 2
    center_lat = (lat_min + lat_max) / 2

    # 투영법 결정
    if is_max_range:
        target_crs = ccrs.Orthographic(central_longitude=center_lon, central_latitude=center_lat)
    elif proj_choice == "Curved (Conic)":
        target_crs = ccrs.AlbersEqualArea(central_longitude=center_lon, central_latitude=center_lat)
    else:
        target_crs = ccrs.PlateCarree()

    # 도화지 생성 (정사각형 비율로 찌그러짐 방지)
    fig, ax = plt.subplots(figsize=(10, 10), dpi=300, subplot_kw={'projection': target_crs})
    ax.set_facecolor('#FFFFFF')

    # 육지 그리기
    world_land_projected = world_land.to_crs(target_crs)
    world_land_projected.plot(ax=ax, color='#E0E0E0', edgecolor='#AAAAAA', linewidth=0.3)

    # 범위 설정
    if is_max_range:
        ax.set_global()
    else:
        ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())

    # 격자선 설정
    if show_grid == 'Y':
        gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=not is_max_range,
                          linestyle='--', linewidth=0.5, color='#AAAAAA')
        gl.xlocator = mticker.MultipleLocator(grid_interval)
        gl.ylocator = mticker.MultipleLocator(grid_interval)
        if not is_max_range:
            gl.top_labels = False
            gl.right_labels = False
            gl.xformatter = LONGITUDE_FORMATTER
            gl.yformatter = LATITUDE_FORMATTER

    st.pyplot(fig)

    # 다운로드 기능
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches='tight', pad_inches=0.1)
    st.download_button(label="📥 Download Map", data=buf.getvalue(), file_name="custom_map.png")
else:
    st.error("Data file not found. Please ensure .shp files are in the repository.")error("Data file not found.")
