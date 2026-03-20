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
st.set_page_config(page_title="High-Res Map Pro", layout="wide")
st.title("🗺️ Universal High-Res Map Generator (Fixed Ratio)")

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
    lon_min = st.number_input("Min Longitude", value=115.0)
    lon_max = st.number_input("Max Longitude", value=145.0)
    lat_min = st.number_input("Min Latitude", value=25.0)
    lat_max = st.number_input("Max Latitude", value=55.0)
    
    st.divider()
    
    st.subheader("📏 Grid Settings (Individual)")
    show_grid = st.radio("Show Grid Lines", ("Y", "N"), index=0)
    lon_interval = st.select_slider("Longitude Interval (deg)", options=[1, 2, 5, 10, 20], value=10)
    lat_interval = st.select_slider("Latitude Interval (deg)", options=[1, 2, 5, 10, 20], value=10)

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

        # --- [핵심 수정] 완벽한 비율 계산 로직 및 수동 보정 ---
        # 위도 보정 계수 (cos)
        aspect = np.cos(np.radians(center_lat))
        
        # 기본 가로 길이를 충분히 넓게 설정 (부채꼴 퍼짐 효과 반영)
        fig_width = 12
        
        # --- 🛠️ 수동 비율 보정 (Curved 모드 전용) ---
        if proj_choice == "Curved":
            # 데이터 거리 비율을 바탕으로 세로 길이를 계산하되,
            base_fig_height = fig_width * (lat_diff / (lon_diff * aspect))
            # 사용자님이 원하시는 '위아래로 눌린 비율'을 위해 강제로 세로 길이를 30% 줄임 (0.7 곱함)
            fig_height = base_fig_height * 0.7
        else:
            # Flat 모드는 기존 보정 유지
            fig_height = fig_width * (lat_diff / (lon_diff * aspect))
        
        # 도화지 생성 (화면 로딩 속도를 위해 dpi=90)
        fig = plt.figure(figsize=(fig_width, min(fig_height, 15)), dpi=90)
        ax = fig.add_subplot(1, 1, 1, projection=target_crs)

        # 지도 시각화 설정 (Meteorological 디자인 스타일 반영)
        ax.set_facecolor('#FFFFFF') # 배경색 흰색

        # 육지 그리기 (얇고 부드러운 해안선 스타일)
        world_land_clipped.plot(ax=ax, transform=ccrs.PlateCarree(), 
                                color='#E0E0E0', edgecolor='#AAAAAA', linewidth=0.3)
        
        # 출력 범위 고정
        ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())

        # 격자선 처리 ( météorologique 스타일 )
        if show_grid == 'Y':
            gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=True, 
                              linestyle='--', linewidth=0.5, color='#AAAAAA', alpha=0.7)
            gl.top_labels = gl.right_labels = False
            gl.xformatter, gl.yformatter = LONGITUDE_FORMATTER, LATITUDE_FORMATTER
            
            # 위경도 간격 개별 적용
            gl.xlocator = mticker.MultipleLocator(lon_interval)
            gl.ylocator = mticker.MultipleLocator(lat_interval)
            
            # 폰트 스타일 조정
            gl.xlabel_style = {'size': 12, 'color': 'black'}
            gl.ylabel_style = {'size': 12, 'color': 'black'}

        # 5. 결과 표시 및 고해상도 다운로드
        st.pyplot(fig, clear_figure=True)

        # 다운로드 시에만 300 DPI 렌더링 (일러스트급 화질)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches='tight', dpi=300, facecolor='#FFFFFF', pad_inches=0.1)
        
        st.download_button(
            label=f"📥 Download {proj_choice} Map (300 DPI)",
            data=buf.getvalue(),
            file_name=f"map_{proj_choice.lower()}_fixed.png",
            mime="image/png"
        )
else:
    st.error("⚠️ 데이터 파일을 찾을 수 없습니다.")
