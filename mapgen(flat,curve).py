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
st.set_page_config(page_title="Universal High-Res Map Pro", layout="wide")
st.title("Map Generator (Flat/Curved)")

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
    proj_choice = st.radio("Select Style", ("Flat", "Curved"))
    
    st.divider()
    
    st.subheader("📍 Map Range")
    lon_min = st.number_input("Min Longitude", value=120.0)
    lon_max = st.number_input("Max Longitude", value=135.0)
    lat_min = st.number_input("Min Latitude", value=30.0)
    lat_max = st.number_input("Max Latitude", value=45.0)
    
    st.divider()
    
    st.subheader("📏 Grid Settings (Individual)")
    show_grid = st.radio("Show Grid Lines", ("Y", "N"), index=0)
    # 위도와 경도 간격을 따로 설정
    lon_interval = st.select_slider("Longitude Interval (deg)", options=[5, 10, 15, 30, 45, 90], value=5)
    lat_interval = st.select_slider("Latitude Interval (deg)", options=[5, 10, 15, 30, 45], value=5)

# 4. 지도 생성 메인 로직
if world_land is not None:
    lat_diff = lat_max - lat_min
    lon_diff = lon_max - lon_min
    center_lon = (lon_min + lon_max) / 2
    center_lat = (lat_min + lat_max) / 2

    if proj_choice == "Curved" and lat_diff >= 120:
        st.error(f"❌ Curved 모드는 위도 범위를 120도 이내로 설정해주세요.")
    else:
        # Clipping
        clip_box = box(lon_min - 2, lat_min - 2, lon_max + 2, lat_max + 2)
        world_land_clipped = world_land.clip(clip_box)

        # --- 투영법 설정 ---
        if proj_choice == "Curved":
            p1 = lat_min + (lat_diff * 0.25)
            p2 = lat_min + (lat_diff * 0.75)
            target_crs = ccrs.AlbersEqualArea(central_longitude=center_lon, 
                                               central_latitude=center_lat, 
                                               standard_parallels=(p1, p2))
        else:
            target_crs = ccrs.PlateCarree()

        # --- 🛠️ [핵심] 완벽한 비율 계산 로직 ---
        # 위도 보정 계수 (cos)
        aspect = np.cos(np.radians(center_lat))
        
        # 도화지의 가로세로 비율을 데이터의 실제 거리 비율과 일치시킴
        # Curved 모드에서 '홀쭉함'을 방지하기 위해 가로 길이를 보정함
        fig_width = 12
        fig_height = fig_width * (lat_diff / (lon_diff * aspect))
        
        # 도화지 생성
        fig = plt.figure(figsize=(fig_width, min(fig_height, 15)), dpi=100)
        ax = fig.add_subplot(1, 1, 1, projection=target_crs)

        ax.set_facecolor('#FFFFFF')
        world_land_clipped.plot(ax=ax, transform=ccrs.PlateCarree(), 
                                color='#E0E0E0', edgecolor='#AAAAAA', linewidth=0.3)
        
        ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())

        if show_grid == 'Y':
            gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=True, 
                              linestyle='--', linewidth=0.5, color='#AAAAAA', alpha=0.7)
            gl.top_labels = gl.right_labels = False
            gl.xformatter, gl.yformatter = LONGITUDE_FORMATTER, LATITUDE_FORMATTER
            
            # 🛠️ 위경도 간격 개별 적용
            gl.xlocator = mticker.MultipleLocator(lon_interval)
            gl.ylocator = mticker.MultipleLocator(lat_interval)

        # 출력
        st.pyplot(fig, clear_figure=True)

        # 5. 다운로드 (300 DPI)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches='tight', dpi=300, facecolor='#FFFFFF')
        
        st.download_button(
            label=f"📥 Download {proj_choice} Map (300 DPI)",
            data=buf.getvalue(),
            file_name=f"map_{proj_choice.lower()}.png",
            mime="image/png"
        )
else:
    st.error("⚠️ 데이터 파일을 찾을 수 없습니다.")
