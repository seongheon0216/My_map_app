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
    # 지구본(Globe) 옵션 추가
    proj_type = st.radio("Select Style", ("Flat (Straight)", "Curved (Conic)", "Globe (Spherical)"))
    
    st.divider()
    
    st.subheader("2. Map Center & Range")
    # 지구본 모드일 때는 '범위'보다 '어느 지점을 중심으로 볼 것인가'가 중요합니다.
    cent_lon = st.number_input("Center Longitude", value=127.0)
    cent_lat = st.number_input("Center Latitude", value=37.0)
    
    # 지도를 얼마나 크게 볼지 결정 (범위)
    extent_val = st.slider("View Range (Degrees)", 5, 180, 40)
    
    st.divider()
    
    st.subheader("3. Grid Settings")
    show_grid = st.radio("Show Grid Lines", ("Y", "N"))
    grid_interval = st.select_slider(
        "Grid Interval (degrees)",
        options=[5, 10, 15, 20, 30, 45, 90],
        value=15
    )

# 2. 지도 생성 로직
if world_land is not None:
    # --- 투영법 결정 ---
    if proj_type == "Globe (Spherical)":
        # 지구본 모드: Orthographic (정사 도법)
        target_crs = ccrs.Orthographic(central_longitude=cent_lon, central_latitude=cent_lat)
        world_land_projected = world_land.to_crs(target_crs)
    elif proj_type == "Curved (Conic)":
        # 곡면 모드: Albers Equal Area (부채꼴)
        target_crs = ccrs.AlbersEqualArea(central_longitude=cent_lon, central_latitude=cent_lat)
        world_land_projected = world_land.to_crs(target_crs)
    else:
        # 평면 모드: PlateCarree (직선)
        target_crs = ccrs.PlateCarree(central_longitude=cent_lon)
        world_land_projected = world_land

    fig, ax = plt.subplots(figsize=(10, 10), dpi=300, subplot_kw={'projection': target_crs})
    ax.set_facecolor('#FFFFFF') # 바다색 (원하면 #E0F7FA 같은 하늘색으로 변경 가능)

    # 육지 그리기
    world_land_projected.plot(ax=ax, color='#E0E0E0', edgecolor='#AAAAAA', linewidth=0.3)

    # 범위 설정
    if proj_type == "Globe (Spherical)":
        # 지구본 모드에서는 원형 테두리를 그려줍니다.
        ax.set_global() # 전체 지구를 대상으로 함
        # 하지만 사용자가 입력한 범위만큼 '줌인' 효과를 줍니다.
        ax.set_extent([cent_lon-extent_val, cent_lon+extent_val, cent_lat-extent_val, cent_lat+extent_val], crs=ccrs.PlateCarree())
    else:
        ax.set_extent([cent_lon-extent_val, cent_lon+extent_val, cent_lat-extent_val, cent_lat+extent_val], crs=ccrs.PlateCarree())

    # 격자선 처리
    if show_grid == 'Y':
        gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=(proj_type != "Globe (Spherical)"),
                          linestyle='-', linewidth=0.5, color='#AAAAAA', zorder=0)
        gl.xlocator = mticker.MultipleLocator(grid_interval)
        gl.ylocator = mticker.MultipleLocator(grid_interval)
        
        if proj_type != "Globe (Spherical)":
            gl.top_labels = False
            gl.right_labels = False
            gl.xformatter = LONGITUDE_FORMATTER
            gl.yformatter = LATITUDE_FORMATTER

    # 3. 결과 표시
    st.pyplot(fig)

    # 4. 다운로드
    import io
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches='tight', pad_inches=0.1, facecolor='#FFFFFF')
    st.download_button(
        label=f"📥 Download {proj_type.split()[0]} Map",
        data=buf.getvalue(),
        file_name="map_output.png",
        mime="image/png"
    )
else:
    st.error("Data file not found.")
