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

# 1. 페이지 설정
st.set_page_config(page_title="Curved Weather Map", layout="wide")
st.title("🎡 Curved Grid Map Generator")

# 2. 데이터 로드
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
    proj_choice = st.radio("Select Style", ("Curved", "Flat"))
    
    st.divider()
    
    st.subheader("📍 Map Range")
    lon_min = st.number_input("Min Longitude", value=90.0)
    lon_max = st.number_input("Max Longitude", value=150.0)
    lat_min = st.number_input("Min Latitude", value=-20.0)
    lat_max = st.number_input("Max Latitude", value=20.0)
    
    st.divider()
    
    st.subheader("📏 Grid Intervals")
    show_grid = st.radio("Show Grid Lines", ("Y", "N"), index=0)
    lon_interval = st.slider("Lon Interval", 1, 30, 10)
    lat_interval = st.slider("Lat Interval", 1, 30, 10)

# 4. 지도 생성 로직
if world_land is not None:
    lat_diff = lat_max - lat_min
    lon_diff = lon_max - lon_min
    center_lon = (lon_min + lon_max) / 2
    center_lat = (lat_min + lat_max) / 2

    # --- [핵심] 곡선 격자를 만드는 투영법 설정 ---
    if proj_choice == "Curved":
        # 적도를 포함해도 에러가 나지 않도록 표준 위도를 입력 범위 밖으로 넓게 잡습니다.
        # 이렇게 하면 격자가 부채꼴로 예쁘게 휩니다.
        std_p1 = lat_min - 20 if lat_min > -70 else -90
        std_p2 = lat_max + 20 if lat_max < 70 else 90
        
        target_crs = ccrs.AlbersEqualArea(central_longitude=center_lon, 
                                           central_latitude=center_lat,
                                           standard_parallels=(std_p1, std_p2))
    else:
        target_crs = ccrs.PlateCarree()

    # --- 비율 보정 (가로로 눌린 느낌 재현) ---
    cos_lat = np.cos(np.radians(center_lat))
    # Curved 모드일 때 조금 더 납작하게 보이도록 보정 계수(0.7) 추가
    aspect_ratio = (lon_diff * cos_lat) / lat_diff
    fig_width = 12
    fig_height = fig_width / aspect_ratio
    if proj_choice == "Curved":
        fig_height *= 0.7  # 가로로 더 눌린 느낌을 줌

    fig = plt.figure(figsize=(fig_width, min(fig_height, 15)), dpi=100)
    ax = fig.add_subplot(1, 1, 1, projection=target_crs)
    ax.set_facecolor('#FFFFFF')

    # 육지 데이터 클리핑 및 그리기
    clip_box = box(lon_min - 10, lat_min - 10, lon_max + 10, lat_max + 10)
    world_land_clipped = world_land.clip(clip_box)
    world_land_clipped.plot(ax=ax, transform=ccrs.PlateCarree(), 
                            color='#E0E0E0', edgecolor='#AAAAAA', linewidth=0.5)
    
    # 범위 설정
    ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())

    # --- [핵심] 격자선 설정 ---
    if show_grid == 'Y':
        # n_steps를 높여서 선이 매끄러운 곡선이 되도록 함
        gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=True, 
                          linestyle='-', linewidth=0.6, color='#888888', alpha=0.6,
                          x_inline=False, y_inline=False)
        gl.top_labels = gl.right_labels = False
        gl.xformatter, gl.yformatter = LONGITUDE_FORMATTER, LATITUDE_FORMATTER
        gl.xlocator = mticker.MultipleLocator(lon_interval)
        gl.ylocator = mticker.MultipleLocator(lat_interval)

    st.pyplot(fig, clear_figure=True)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches='tight', dpi=300)
    st.download_button(label="📥 Download Map", data=buf.getvalue(), file_name="curved_map.png")
