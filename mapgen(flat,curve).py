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

# 1. 페이지 설정 및 제목
st.set_page_config(page_title="High-Res Map Generator", layout="wide")
st.title("🗺️ Professional Map Generator")
st.markdown("---")

# 2. 데이터 로드 (캐싱 적용)
current_folder = os.path.dirname(os.path.abspath(__file__))
land_path = os.path.join(current_folder, "ne_10m_land.shp")

@st.cache_data
def load_data():
    if os.path.exists(land_path):
        # 10m 고해상도 데이터를 기본으로 사용
        return gpd.read_file(land_path)
    return None

world_land = load_data()

# 3. 사이드바 설정 (사용자 입력)
with st.sidebar:
    st.header("🛠️ Settings")
    
    st.subheader("1. Projection Type")
    proj_choice = st.radio("Select Style", ("Flat", "Curved"), help="Flat: PlateCarree / Curved: Albers Equal Area")
    
    st.divider()
    
    st.subheader("2. Map Range")
    lon_min = st.number_input("Min Longitude", value=124.0, format="%.2f")
    lon_max = st.number_input("Max Longitude", value=132.0, format="%.2f")
    lat_min = st.number_input("Min Latitude", value=33.0, format="%.2f")
    lat_max = st.number_input("Max Latitude", value=39.0, format="%.2f")
    
    st.divider()
    
    st.subheader("3. Grid Settings")
    show_grid = st.radio("Show Grid Lines", ("Y", "N"), index=0)
    grid_interval = st.select_slider(
        "Grid Interval (degrees)",
        options=[1, 2, 5, 10, 15, 20, 25, 30],
        value=5
    )

# 4. 메인 로직 실행
if world_land is not None:
    # 위도 범위 및 중심 계산
    lat_diff = lat_max - lat_min
    center_lon = (lon_min + lon_max) / 2
    center_lat = (lat_min + lat_max) / 2

    # --- [에러 방지] Curved 모드 한계 체크 ---
    if proj_choice == "Curved" and lat_diff >= 120:
        st.error(f"❌ Curved 모드는 위도 범위를 120도 이내로 설정해주세요. (현재 차이: {lat_diff:.1f}도)")
        st.info("💡 전 세계 수준의 광범위한 지도는 'Flat' 모드를 사용하면 에러 없이 생성됩니다.")
    else:
        # --- [속도 최적화] Clipping ---
        # 화면에 보이는 부분만 미리 잘라내어 10m 데이터의 연산량을 최소화함
        clip_box = box(lon_min - 1, lat_min - 1, lon_max + 1, lat_max + 1)
        world_land_clipped = world_land.clip(clip_box)

        # --- 투영법 설정 ---
        if proj_choice == "Curved":
            # Albers 투영 시 위도 범위에 맞춘 표준 위도(Standard Parallels) 자동 설정
            p1 = lat_min + (lat_diff * 0.25)
            p2 = lat_min + (lat_diff * 0.75)
            target_crs = ccrs.AlbersEqualArea(central_longitude=center_lon, 
                                               central_latitude=center_lat, 
                                               standard_parallels=(p1, p2))
        else:
            # Flat 모드: 직선 위경도 투영
            target_crs = ccrs.PlateCarree()

        # --- [왜곡 보정] 가로세로 비율 설정 ---
        # Flat 모드에서 위도에 따라 가로로 늘어나는 현상을 방지하기 위해 figsize를 동적 조절
        if proj_choice == "Flat":
            aspect = 1 / np.cos(np.radians(center_lat))
            data_ratio = (lon_max - lon_min) / (lat_max - lat_min)
            fig_width = 10
            fig_height = fig_width / (data_ratio / aspect)
            # 화면 미리보기는 속도를 위해 dpi=80
            fig, ax = plt.subplots(figsize=(fig_width, min(fig_height, 15)), dpi=80, subplot_kw={'projection': target_crs})
        else:
            fig, ax = plt.subplots(figsize=(10, 10), dpi=80, subplot_kw={'projection': target_crs})

        # --- 지도 시각화 설정 ---
        ax.set_facecolor('#FFFFFF') # 배경색 흰색

        # 육지 그리기 (10m 정밀도 유지)
        world_land_clipped.plot(ax=ax, transform=ccrs.PlateCarree(), 
                                color='#E0E0E0', edgecolor='#AAAAAA', linewidth=0.3)

        # 맵 범위 고정
        ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())

        # 격자선 처리 (실선 스타일)
        if show_grid == 'Y':
            gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=True, 
                              linestyle='-', linewidth=0.5, color='#AAAAAA', alpha=0.7)
            gl.top_labels = False
            gl.right_labels = False
            gl.xformatter = LONGITUDE_FORMATTER
            gl.yformatter = LATITUDE_FORMATTER
            gl.xlocator = mticker.MultipleLocator(grid_interval)
            gl.ylocator = mticker.MultipleLocator(grid_interval)
        else:
            ax.spines['geo'].set_visible(True)

        # 5. 화면 표시 및 다운로드
        st.pyplot(fig)

        # 다운로드 시에만 300 DPI로 고화질 렌더링 (메모리 절약형)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches='tight', dpi=300, facecolor='#FFFFFF')
        
        st.download_button(
            label=f"📥 Download {proj_choice} Map (High-Res 300 DPI)",
            data=buf.getvalue(),
            file_name=f"map_{proj_choice.lower()}_300dpi.png",
            mime="image/png"
        )
else:
    st.error("⚠️ 데이터 파일(ne_10m_land.shp)을 찾을 수 없습니다. 경로를 확인해주세요.")
