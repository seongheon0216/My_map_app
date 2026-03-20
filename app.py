import streamlit as st
import geopandas as gpd
import matplotlib.pyplot as plt
import os
import cartopy.crs as ccrs
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
import matplotlib.ticker as mticker

# 페이지 설정
st.set_page_config(page_title="Map Generator Pro", layout="wide")
st.title("🗺️ Map Generator")

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
    # 다시 Flat과 Curved를 선택할 수 있게 복구했습니다.
    proj_choice = st.radio("Select Style", ("Flat (Straight)", "Curved (Conic)"))
    
    st.divider()
    
    st.subheader("2. Map Range")
    lon_min = st.number_input("Min Longitude", value=115.0)
    lon_max = st.number_input("Max Longitude", value=145.0)
    lat_min = st.number_input("Min Latitude", value=25.0)
    lat_max = st.number_input("Max Latitude", value=50.0)
    
    st.divider()
    
    st.subheader("3. Grid Settings")
    show_grid = st.radio("Show Grid Lines", ("Y", "N"))
    grid_interval = st.select_slider(
        "Grid Interval (degrees)",
        options=[5, 10, 15, 20, 30, 45, 90],
        value=5
    )

# 2. 지도 생성 로직
if world_land is not None:
    # 수치 안정성 보정
    actual_lon_min, actual_lon_max = max(lon_min, -179.9), min(lon_max, 179.9)
    actual_lat_min, actual_lat_max = max(lat_min, -89.9), min(lat_max, 89.9)
    
    lon_range = lon_max - lon_min
    lat_range = lat_max - lat_min
    center_lon = (lon_min + lon_max) / 2
    center_lat = (lat_min + lat_max) / 2

    # --- 투영법 결정 로직 ---
    # 조건: 범위가 매우 넓으면(전지구급) 무조건 Globe로 변환
    if lon_range >= 180 or lat_range >= 90:
        st.info("🌐 Wide range detected. Switching to Globe view.")
        target_crs = ccrs.Orthographic(central_longitude=center_lon, central_latitude=center_lat)
        is_globe = True
    # 그 외에는 사용자가 선택한 스타일 적용
    elif proj_choice == "Curved (Conic)":
        target_crs = ccrs.AlbersEqualArea(central_longitude=center_lon, central_latitude=center_lat)
        is_globe = False
    else:
        target_crs = ccrs.PlateCarree()
        is_globe = False

    # 도화지 생성
    fig, ax = plt.subplots(figsize=(10, 8), dpi=300, subplot_kw={'projection': target_crs})
    ax.set_facecolor('#FFFFFF')

    # 육지 데이터 투영 및 그리기
    world_land_projected = world_land.to_crs(target_crs) if is_globe or proj_choice == "Curved (Conic)" else world_land
    world_land_projected.plot(ax=ax, color='#E0E0E0', edgecolor='#AAAAAA', linewidth=0.3)

    # 범위 설정
    if is_globe:
        ax.set_global()
        if lon_range < 350:
            ax.set_extent([actual_lon_min, actual_lon_max, actual_lat_min, actual_lat_max], crs=ccrs.PlateCarree())
    else:
        ax.set_extent([actual_lon_min, actual_lon_max, actual_lat_min, actual_lat_max], crs=ccrs.PlateCarree())

    # 격자선 처리
    if show_grid == 'Y':
        # 지구본일 때는 라벨을 숨김 (에러 방지 및 깔끔함)
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
    import io
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches='tight', pad_inches=0.1, facecolor='#FFFFFF')
    st.download_button(
        label=f"📥 Download Map (PNG)",
        data=buf.getvalue(),
        file_name="custom_map.png",
        mime="image/png"
    )
else:
    st.error("Data file not found.")
