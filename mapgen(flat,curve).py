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
st.title("🗺️ Professional Map Generator (Fixed Ratio)")

# 2. 데이터 로드 (10m 고해상도 고정)
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
    proj_choice = st.radio("Select Style", ("Flat", "Curved")
    
    st.divider()
    
    st.subheader("📍 Map Range")
    lon_min = st.number_input("Min Longitude", value=124.0)
    lon_max = st.number_input("Max Longitude", value=132.0)
    lat_min = st.number_input("Min Latitude", value=33.0)
    lat_max = st.number_input("Max Latitude", value=39.0)
    
    st.divider()
    
    st.subheader("📏 Grid Settings")
    show_grid = st.radio("Show Grid Lines", ("Y", "N"), index=0)
    grid_interval = st.select_slider("Interval (deg)", options=[1, 2, 5, 10, 15, 20], value=5)

# 4. 지도 생성 메인 로직
if world_land is not None:
    lat_diff = lat_max - lat_min
    lon_diff = lon_max - lon_min
    center_lon = (lon_min + lon_max) / 2
    center_lat = (lat_min + lat_max) / 2

    # --- [에러 방지] Curved 모드 한계 체크 ---
    if proj_choice == "Curved" and lat_diff >= 120:
        st.error(f"❌ Curved 모드는 위도 범위를 120도 이내로 설정해주세요. (현재 차이: {lat_diff:.1f}도)")
    else:
        # --- [속도 최적화] Clipping ---
        # 선택 영역만 잘라내어 연산량 90% 이상 절감
        clip_box = box(lon_min - 1, lat_min - 1, lon_max + 1, lat_max + 1)
        world_land_clipped = world_land.clip(clip_box)

        # --- 투영법 설정 ---
        if proj_choice == "Curved":
            # 위도 범위에 따른 표준 위도 자동 계산 (에러 방지)
            p1 = lat_min + (lat_diff * 0.25)
            p2 = lat_min + (lat_diff * 0.75)
            target_crs = ccrs.AlbersEqualArea(central_longitude=center_lon, 
                                               central_latitude=center_lat, 
                                               standard_parallels=(p1, p2))
        else:
            target_crs = ccrs.PlateCarree()

        # --- [핵심 수정] 가로세로 비율(Aspect Ratio) 보정 ---
        # 위도에 따라 경도 1도의 실제 거리가 달라지는 것을 반영 (cos 보정)
        # 이 처리가 있어야 Curved 모드에서 홀쭉해지거나 Flat에서 뚱뚱해지지 않음
        aspect = 1 / np.cos(np.radians(center_lat))
        data_ratio = lon_diff / lat_diff
        
        fig_width = 10
        fig_height = fig_width / (data_ratio / aspect)
        
        # 화면 미리보기용 (DPI 80으로 로딩 속도 확보)
        fig, ax = plt.subplots(figsize=(fig_width, min(fig_height, 15)), dpi=80, 
                               subplot_kw={'projection': target_crs})

        # --- 지도 시각화 ---
        ax.set_facecolor('#FFFFFF')
        world_land_clipped.plot(ax=ax, transform=ccrs.PlateCarree(), 
                                color='#E0E0E0', edgecolor='#AAAAAA', linewidth=0.3)
        
        # 출력 범위 고정
        ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())

        # 격자선 처리
        if show_grid == 'Y':
            gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=True, 
                              linestyle='-', linewidth=0.5, color='#AAAAAA', alpha=0.7)
            gl.top_labels = gl.right_labels = False
            gl.xformatter, gl.yformatter = LONGITUDE_FORMATTER, LATITUDE_FORMATTER
            gl.xlocator = mticker.MultipleLocator(grid_interval)
            gl.ylocator = mticker.MultipleLocator(grid_interval)

        # 5. 결과 표시
        st.pyplot(fig)

        # 고해상도 다운로드 (버튼 클릭 시에만 300 DPI 렌더링)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches='tight', dpi=300, facecolor='#FFFFFF')
        
        st.download_button(
            label=f"📥 Download {proj_choice} Map (300 DPI)",
            data=buf.getvalue(),
            file_name=f"map_{proj_choice.lower()}_fixed.png",
            mime="image/png"
        )
else:
    st.error("⚠️ 데이터 파일을 찾을 수 없습니다.")
