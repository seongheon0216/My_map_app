import streamlit as st
import geopandas as gpd
import matplotlib.pyplot as plt
import os
from shapely.geometry import box
import cartopy.crs as ccrs
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
import matplotlib.ticker as mticker

# 페이지 설정
st.set_page_config(page_title="Map Generator Pro", layout="wide")
st.title("🗺️ Map Generator")
st.sidebar.header("Settings")

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
    st.subheader("1. Projection Type")
    # 평면(Flat)과 곡면(Curved) 선택 메뉴 추가
    proj_type = st.radio("Select Style", ("Flat (Straight Lines)", "Curved (Spherical View)"))
    
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
        options=[5, 10, 15, 20, 25, 30],
        value=5
    )

# 2. 지도 생성 로직
if world_land is not None:
    # --- 투영법 결정 ---
    if proj_type == "Curved (Spherical View)":
        # 곡면 모드: Albers Equal Area
        target_crs = ccrs.AlbersEqualArea(
            central_longitude=(lon_min + lon_max) / 2,
            central_latitude=(lat_min + lat_max) / 2,
            standard_parallels=(lat_min, lat_max)
        )
        fig, ax = plt.subplots(figsize=(10, 8), dpi=300, subplot_kw={'projection': target_crs})
        world_land_projected = world_land.to_crs(target_crs)
    else:
        # 평면 모드: PlateCarree (직선 위경도)
        target_crs = ccrs.PlateCarree()
        fig, ax = plt.subplots(figsize=(10, 8), dpi=300, subplot_kw={'projection': target_crs})
        world_land_projected = world_land

    ax.set_facecolor('#FFFFFF')

    # 육지 그리기
    world_land_projected.plot(ax=ax, color='#E0E0E0', edgecolor='none')

    # 범위 설정
    ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())

    # 격자선 처리
    if show_grid == 'Y':
        gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=True,
                          linestyle='-', linewidth=0.5, color='#AAAAAA', zorder=0)
        
        gl.top_labels = False
        gl.right_labels = False
        gl.xformatter = LONGITUDE_FORMATTER
        gl.yformatter = LATITUDE_FORMATTER
        gl.xlocator = mticker.MultipleLocator(grid_interval)
        gl.ylocator = mticker.MultipleLocator(grid_interval)
        
        # 평면 모드일 때 라벨 위치가 겹치는 현상 방지
        gl.rotate_labels = False 
    else:
        # 격자를 안 그릴 때도 외곽선은 유지
        ax.spines['geo'].set_visible(True)

    # 3. 결과 표시
    st.pyplot(fig)

    # 4. 다운로드
    import io
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches='tight', pad_inches=0.1, facecolor='#FFFFFF')
    st.download_button(
        label=f"📥 Download {proj_type.split()[0]} Map (PNG)",
        data=buf.getvalue(),
        file_name="map_generator_output.png",
        mime="image/png"
    )
else:
    st.error("Data file not found.")
