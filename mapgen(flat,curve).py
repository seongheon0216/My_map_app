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
st.set_page_config(page_title="Ultimate Curved Map", layout="wide")
st.title("Map Generator(Flat/Curved)")

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
    lon_min = st.number_input("Min Longitude", value=120.0)
    lon_max = st.number_input("Max Longitude", value=135.0)
    lat_min = st.number_input("Min Latitude", value=30.0)
    lat_max = st.number_input("Max Latitude", value=45.0)
    
    st.divider()
    
    st.subheader("📏 Grid Intervals")
    show_grid = st.radio("Show Grid Lines", ("Y", "N"), index=0)
    lon_interval = st.select_slider("Longitude Interval", options=[5, 10, 15, 30, 45, 90], value=5)
    lat_interval = st.select_slider("Latitude Interval", options=[5, 10, 15], value=5)

# ... (상단 1~3번 섹션은 동일) ...

# 4. 지도 생성 로직
if world_land is not None:
    center_lon = (lon_min + lon_max) / 2
    center_lat = (lat_min + lat_max) / 2

    # 투영법 설정
    if proj_choice == "Curved":
        target_crs = ccrs.Orthographic(central_longitude=center_lon, 
                                       central_latitude=center_lat)
    else:
        target_crs = ccrs.PlateCarree()

    fig = plt.figure(figsize=(12, 8), dpi=100)
    ax = fig.add_subplot(1, 1, 1, projection=target_crs)
    ax.set_facecolor('#FFFFFF')

    # 육지 데이터 그리기
    clip_box = box(lon_min - 10, lat_min - 10, lon_max + 10, lat_max + 10)
    world_land_clipped = world_land.clip(clip_box)
    world_land_clipped.plot(ax=ax, transform=ccrs.PlateCarree(), 
                            color='#E0E0E0', edgecolor='#AAAAAA', linewidth=0.5)
    
    ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())

    # 격자선 설정
    if show_grid == 'Y':
        # 🛠️ 에러 방지를 위해 draw_labels=False로 설정 후 수동 제어하거나 인자를 최소화합니다.
        try:
            gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=True, 
                              linestyle='-', linewidth=0.6, color='#888888', alpha=0.6)
            gl.top_labels = gl.right_labels = False
            gl.xformatter, gl.yformatter = LONGITUDE_FORMATTER, LATITUDE_FORMATTER
            gl.xlocator = mticker.MultipleLocator(lon_interval)
            gl.ylocator = mticker.MultipleLocator(lat_interval)
        except Exception:
            # 에러 발생 시 라벨 없이 격자만 그림 (버전 호환성 대비)
            ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=False)

    # --- 🛠️ 여기서부터 순서 변경 (핵심) ---
    
    # 1. 화면에 표시하기 전에 '먼저' 버퍼에 저장합니다.
    buf = io.BytesIO()
    # facecolor='white'를 명시하여 배경이 투명하게 날아가는 것을 방지합니다.
    fig.savefig(buf, format="png", bbox_inches='tight', dpi=300, facecolor='white')
    img_bytes = buf.getvalue()

    # 2. 그 다음에 화면에 출력합니다.
    st.pyplot(fig)

    # 3. 이미 생성된 데이터를 다운로드 버튼에 연결합니다.
    st.download_button(
        label="📥 Download Map (300 DPI)", 
        data=img_bytes, 
        file_name="final_curved_map.png",
        mime="image/png"
    )

else:
    st.error("⚠️ 데이터 파일이 없습니다.")
