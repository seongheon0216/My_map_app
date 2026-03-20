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
st.set_page_config(page_title="Pro Weather Map Gen", layout="wide")
st.title("🌍 Professional Weather Map Generator")

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
    st.header("🛠️ Map Control")
    proj_choice = st.radio("Style", ("Curved", "Flat"))
    
    st.divider()
    
    st.subheader("📍 Range Settings")
    lon_min = st.number_input("Min Longitude", value=90.0)
    lon_max = st.number_input("Max Longitude", value=150.0)
    lat_min = st.number_input("Min Latitude", value=-30.0)
    lat_max = st.number_input("Max Latitude", value=30.0)
    
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

    # --- [비율 보정 알고리즘] ---
    # 위도에 따른 실제 물리적 거리 보정 (cos 계산)
    # 적도 근처(0도)일수록 1에 가깝고 고위도로 갈수록 작아짐
    cos_lat = np.cos(np.radians(center_lat))
    
    # 도화지의 가로 세로 비율 계산
    # 가로(lon_diff)에 cos_lat을 곱해 실제 시각적 비율을 맞춤
    aspect_ratio = (lon_diff * cos_lat) / lat_diff
    
    fig_width = 12
    # aspect_ratio에 맞춰 높이를 결정 (너무 길어지지 않게 6~12 사이 조절)
    fig_height = fig_width / aspect_ratio
    fig_height = max(5, min(fig_height, 15))

    # --- 투영법 선택 (에러 방지형) ---
    if proj_choice == "Curved":
        # 적도 통과 시에도 안전한 Miller 투영법 (곡선미는 살리되 에러는 없음)
        target_crs = ccrs.Miller(central_longitude=center_lon)
    else:
        target_crs = ccrs.PlateCarree()

    fig = plt.figure(figsize=(fig_width, fig_height), dpi=100)
    ax = fig.add_subplot(1, 1, 1, projection=target_crs)
    ax.set_facecolor('#FFFFFF')

    # 육지 그리기 (정밀 클리핑)
    clip_box = box(lon_min - 10, lat_min - 10, lon_max + 10, lat_max + 10)
    world_land_clipped = world_land.clip(clip_box)
    
    # 육지 색상은 기상 지도 스타일로 (연회색 바탕에 회색 테두리)
    world_land_clipped.plot(ax=ax, transform=ccrs.PlateCarree(), 
                            color='#E5E5E5', edgecolor='#888888', linewidth=0.5)
    
    # 맵 범위 확정
    ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())

    # 격자선 설정 (실선, 전문 기상 지도 스타일)
    if show_grid == 'Y':
        gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=True, 
                          linestyle='-', linewidth=0.6, color='#AAAAAA', alpha=0.5)
        gl.top_labels = gl.right_labels = False
        gl.xformatter, gl.yformatter = LONGITUDE_FORMATTER, LATITUDE_FORMATTER
        gl.xlocator = mticker.MultipleLocator(lon_interval)
        gl.ylocator = mticker.MultipleLocator(lat_interval)
        gl.xlabel_style = {'size': 11}
        gl.ylabel_style = {'size': 11}

    # 결과 출력
    st.pyplot(fig, clear_figure=True)

    # 300 DPI 저장용
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches='tight', dpi=300, facecolor='#FFFFFF')
    st.download_button(label="📥 Download Map (300 DPI)", data=buf.getvalue(), file_name="weather_map.png")
else:
    st.error("데이터 파일을 찾을 수 없습니다.")
