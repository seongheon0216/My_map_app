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
st.title("🗺️ Map Generator (Auto-Switching)")

# 1. 데이터 경로 설정 (상대 경로 보강)
current_folder = os.path.dirname(os.path.abspath(__file__))

def get_data_path(filename):
    return os.path.join(current_folder, filename)

@st.cache_data
def load_and_fix_data(path, is_globe=False):
    if os.path.exists(path):
        try:
            gdf = gpd.read_file(path)
            if is_globe:
                # --- 핵심: 지구본 모드일 때 대륙 삼각형 깨짐 방지 ---
                # 폴리곤의 꼬인 부분을 수학적으로 펴주는 작업 (buffer 0)
                gdf['geometry'] = gdf['geometry'].buffer(0)
            return gdf
        except Exception as e:
            st.error(f"Error loading {os.path.basename(path)}: {e}")
    return None

# 2. 사이드바 설정
with st.sidebar:
    st.subheader("1. Projection Style")
    proj_choice = st.radio("Select Style", ("Flat (Straight)", "Curved (Conic)"))
    
    st.divider()
    
    st.subheader("2. Map Range")
    lon_min = st.number_input("Min Longitude", value=115.0, min_value=-180.0, max_value=180.0)
    lon_max = st.number_input("Max Longitude", value=145.0, min_value=-180.0, max_value=180.0)
    lat_min = st.number_input("Min Latitude", value=25.0, min_value=-90.0, max_value=90.0)
    lat_max = st.number_input("Max Latitude", value=50.0, min_value=-90.0, max_value=90.0)
    
    st.divider()
    
    st.subheader("3. Grid Settings")
    show_grid = st.radio("Show Grid Lines", ("Y", "N"), index=0)
    grid_interval = st.select_slider("Grid Interval", options=[5, 10, 15, 20, 25, 30], value=5)

# 3. 로직 처리
lon_range = abs(lon_max - lon_min)
lat_range = abs(lat_max - lat_min)
is_max_range = lon_range >= 179.0 or lat_range >= 89.0

# 데이터 선택 로드
target_path = get_data_path("ne_110m_land.shp" if is_max_range else "ne_10m_land.shp")
world_land = load_and_fix_data(target_path, is_globe=is_max_range)

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

    # 도화지 생성 (1:1 비율 고정으로 찌그러짐 방지)
    fig, ax = plt.subplots(figsize=(10, 10), dpi=300, subplot_kw={'projection': target_crs})
    ax.set_facecolor('#FFFFFF')

    # 육지 그리기
    try:
        world_land_projected = world_land.to_crs(target_crs)
        world_land_projected.plot(ax=ax, color='#E0E0E0', edgecolor='#AAAAAA', linewidth=0.3)
    except:
        world_land.plot(ax=ax, color='#E0E0E0', edgecolor='#AAAAAA', linewidth=0.3)

    # 범위 설정
    if is_max_range:
        ax.set_global()
    else:
        ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())

    # 격자선
    if show_grid == 'Y':
        gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=not is_max_range,
                          linestyle='--', linewidth=0.5, color='#AAAAAA')
        gl.xlocator = mticker.MultipleLocator(grid_interval)
        gl.ylocator = mticker.MultipleLocator(grid_interval)
        if not is_max_range:
            gl.top_labels, gl.right_labels = False, False
            gl.xformatter, gl.yformatter = LONGITUDE_FORMATTER, LATITUDE_FORMATTER

    st.pyplot(fig)

    # 다운로드
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches='tight', pad_inches=0.1)
    st.download_button("📥 Download Map", data=buf.getvalue(), file_name="map.png")
else:
    st.error(f"파일을 찾을 수 없습니다: {os.path.basename(target_path)}")
