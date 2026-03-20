import streamlit as st
import geopandas as gpd
import matplotlib.pyplot as plt
import os
import cartopy.crs as ccrs
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
import matplotlib.ticker as mticker

# 페이지 설정
st.set_page_config(page_title="Auto Map Generator", layout="wide")
st.title("🗺️ Auto Map Generator (Flat & Globe)")
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
    st.subheader("1. Map Range (Degrees)")
    # 사용자가 직접 위경도 범위를 입력합니다.
    lon_min = st.number_input("Min Longitude", value=115.0)
    lon_max = st.number_input("Max Longitude", value=145.0)
    lat_min = st.number_input("Min Latitude", value=25.0)
    lat_max = st.number_input("Max Latitude", value=50.0)
    
    st.divider()
    
    st.subheader("2. Grid Settings")
    show_grid = st.radio("Show Grid Lines", ("Y", "N"))
    grid_interval = st.select_slider(
        "Grid Interval (degrees)",
        options=[5, 10, 15, 20, 30, 45, 90],
        value=5
    )

# 2. 지도 생성 로직
if world_land is not None:
    # --- 핵심: 자동 범위 감지 및 투영법 결정 ---
    lon_range = lon_max - lon_min
    lat_range = lat_max - lat_min
    
    # 입력한 경도 범위가 180도 이상이거나 위도 범위가 90도 이상이면 자동으로 지구본 모드
    if lon_range >= 180 or lat_range >= 90:
        st.info("🌐 Wide range detected. Automatic Globe projection.")
        target_crs = ccrs.Orthographic(
            central_longitude=(lon_min + lon_max) / 2,
            central_latitude=(lat_min + lat_max) / 2
        )
        world_land_projected = world_land.to_crs(target_crs)
        fig, ax = plt.subplots(figsize=(10, 10), dpi=300, subplot_kw={'projection': target_crs})
        ax.set_global() # 전체 지구를 대상으로 함
        # 사용자가 입력한 범위로 '줌' 효과
        ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())
    else:
        # 평소에는 평면 모드: PlateCarree (직선 위경도)
        target_crs = ccrs.PlateCarree()
        fig, ax = plt.subplots(figsize=(10, 8), dpi=300, subplot_kw={'projection': target_crs})
        world_land_projected = world_land
        # 사용자가 입력한 범위로 '줌' 효과
        ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())

    ax.set_facecolor('#FFFFFF')

    # 육지 그리기
    world_land_projected.plot(ax=ax, color='#E0E0E0', edgecolor='#AAAAAA', linewidth=0.3)

    # 격자선 처리
    if show_grid == 'Y':
        # 지구본 모드일 때는 라벨을 숨기거나 조정
        draw_labels_bool = (lon_range < 180 and lat_range < 90)
        gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=draw_labels_bool,
                          linestyle='-', linewidth=0.5, color='#AAAAAA', zorder=0)
        gl.xlocator = mticker.MultipleLocator(grid_interval)
        gl.ylocator = mticker.MultipleLocator(grid_interval)
        
        if draw_labels_bool:
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
        label=f"📥 Download Auto Map",
        data=buf.getvalue(),
        file_name="auto_map_generator_output.png",
        mime="image/png"
    )
else:
    st.error("Data file not found.")
