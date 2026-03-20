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

# 페이지 설정
st.set_page_config(page_title="Pro Map Generator", layout="wide")
st.title("🗺️ Pro Map Generator (Flat & Curved)")
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
    proj_choice = st.radio("Select Style", ("Flat", "Curved"))
    
    st.divider()
    
    st.subheader("2. Map Range")
    lon_min = st.number_input("Min Longitude", value=115.0)
    lon_max = st.number_input("Max Longitude", value=145.0)
    lat_min = st.number_input("Min Latitude", value=25.0)
    lat_max = st.number_input("Max Latitude", value=50.0)
    
    st.divider()
    
    st.subheader("3. Grid Settings")
    show_grid = st.radio("Show Grid Lines", ("Y", "N"), index=0)
    grid_interval = st.select_slider(
        "Grid Interval (degrees)",
        options=[5, 10, 15, 20, 25, 30],
        value=5
    )
# ... (앞부분 동일)

# 2. 지도 생성 로직
if world_land is not None:
    # 위도 범위 체크 (Albers 투영법의 한계 극복)
    lat_diff = lat_max - lat_min
    
    if proj_choice == "Curved" and lat_diff >= 120:
        # 위도 차이가 120도 이상이면 Albers 투영이 깨질 확률이 매우 높음
        st.warning("⚠️ Curved 모드에서는 위도 범위를 조금 더 좁게 설정해주세요. (전 세계를 보려면 Flat 모드 권장)")
    else:
        # 기존 로직 실행
        center_lon = (lon_min + lon_max) / 2
        center_lat = (lat_min + lat_max) / 2

        # Clipping 및 투영 설정 (이전과 동일)
        clip_box = box(lon_min - 1, lat_min - 1, lon_max + 1, lat_max + 1)
        world_land_clipped = world_land.clip(clip_box)

        if proj_choice == "Curved":
            p1 = lat_min + (lat_diff * 0.25)
            p2 = lat_min + (lat_diff * 0.75)
            target_crs = ccrs.AlbersEqualArea(central_longitude=center_lon, 
                                               central_latitude=center_lat, 
                                               standard_parallels=(p1, p2))
        else:
            target_crs = ccrs.PlateCarree()

        # ... (이하 지도 그리기 및 다운로드 로직 동일)
# 2. 지도 생성 로직
if world_land is not None:
    # 중심 및 위도 범위 계산
    center_lon = (lon_min + lon_max) / 2
    center_lat = (lat_min + lat_max) / 2
    lat_diff = lat_max - lat_min

    # --- 핵심 1: 강력한 Clipping (계산량 감소 및 속도 향상) ---
    # 화면에 보일 범위만 미리 잘라내서 계산 부하를 줄입니다.
    # 여유분을 1도 정도 두어 해안선이 끊기지 않게 합니다.
    clip_box = box(lon_min - 1, lat_min - 1, lon_max + 1, lat_max + 1)
    world_land = world_land.clip(clip_box)

    # --- 투영법 결정 ---
    if proj_choice == "Curved":
        # --- 핵심 2: 표준 위도(Standard Parallels) 안전 설정 ---
        # 적도를 가로지르는 범위에서도 에러가 나지 않도록 위도 범위의 1/4, 3/4 지점을 기준으로 설정
        p1 = lat_min + (lat_diff * 0.25)
        p2 = lat_min + (lat_diff * 0.75)
        
        target_crs = ccrs.AlbersEqualArea(central_longitude=center_lon, 
                                           central_latitude=center_lat, 
                                           standard_parallels=(p1, p2))
    else:
        # Flat 모드: 직선 위경도
        target_crs = ccrs.PlateCarree()

    # --- 도화지 및 비율 보정 ---
    # Flat 모드일 때 위도에 따른 늘어짐 방지
    if proj_choice == "Flat":
        aspect = 1 / np.cos(np.radians(center_lat))
        data_ratio = (lon_max - lon_min) / (lat_max - lat_min)
        fig_width = 10
        fig_height = fig_width / (data_ratio / aspect)
        fig, ax = plt.subplots(figsize=(fig_width, min(fig_height, 15)), dpi=85, subplot_kw={'projection': target_crs})
    else:
        fig, ax = plt.subplots(figsize=(10, 10), dpi=85, subplot_kw={'projection': target_crs})

    ax.set_facecolor('#FFFFFF')

    # 육지 그리기 (잘려진 데이터라 빠름)
    world_land.plot(ax=ax, transform=ccrs.PlateCarree(), color='#E0E0E0', edgecolor='#AAAAAA', linewidth=0.3)

    # 범위 설정 (반드시 PlateCarree 좌표로 설정해야 왜곡이 없음)
    ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())

    # 격자선 설정 (실선 '-' / 미리보기는 draw_labels=True)
    if show_grid == 'Y':
        gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=True, 
                          linestyle='-', linewidth=0.5, color='#AAAAAA')
        
        gl.top_labels = False
        gl.right_labels = False
        gl.xformatter = LONGITUDE_FORMATTER
        gl.yformatter = LATITUDE_FORMATTER
        gl.xlocator = mticker.MultipleLocator(grid_interval)
        gl.ylocator = mticker.MultipleLocator(grid_interval)
    else:
        # 격자를 안 그릴 때도 외곽선은 유지
        ax.spines['geo'].set_visible(True)

    # 3. 결과 표시
    st.pyplot(fig)

    # 4. 일러스트용 고해상도 다운로드 (300 DPI)
    # 버튼을 누르는 순간 렌더링되도록 버퍼 활용
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches='tight', dpi=300, facecolor='#FFFFFF')
    
    st.download_button(
        label=f"📥 Download {proj_choice} Map (300 DPI PNG)",
        data=buf.getvalue(),
        file_name=f"map_{proj_choice.lower()}_highres.png",
        mime="image/png"
    )
else:
    st.error("Data file not found.")
