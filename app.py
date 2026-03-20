import streamlit as st
import geopandas as gpd
import matplotlib.pyplot as plt
import os
from shapely.geometry import box
from matplotlib.ticker import MultipleLocator

# 페이지 설정
st.set_page_config(page_title="수능 지도 생성기", layout="wide")
st.title("🗺️ 수능/교과서 스타일 지도 생성기")
st.sidebar.header("설정값 입력")

# 데이터 경로 (파일들이 app.py와 같은 폴더에 있어야 함)
current_folder = os.path.dirname(os.path.abspath(__file__))
land_path = os.path.join(current_folder, "ne_10m_land.shp")

@st.cache_data # 데이터를 매번 새로 읽지 않도록 캐싱하여 속도 향상
def load_data():
    if os.path.exists(land_path):
        return gpd.read_file(land_path)
    return None

world_land = load_data()

# 1. 사이드바에서 입력 받기
with st.sidebar:
    lon_min = st.number_input("최소 경도 (W:- / E:+)", value=110.0)
    lon_max = st.number_input("최대 경도 (W:- / E:+)", value=150.0)
    lat_min = st.number_input("최소 위도 (S:- / Lat:+)", value=20.0)
    lat_max = st.number_input("최대 위도 (S:- / Lat:+)", value=55.0)
    
    show_grid = st.radio("실선 격자선 표시 여부", ("Y", "N"))
    grid_interval = st.slider("격자 간격 (도 단위)", 5, 30, 10)

# 2. 지도 생성 로직
if world_land is not None:
    scope = box(lon_min, lat_min, lon_max, lat_max)
    target_land = world_land.clip(scope)

    fig, ax = plt.subplots(figsize=(10, 8), dpi=300)
    ax.set_facecolor('#FFFFFF') # 바다: 흰색

    if not target_land.empty:
        target_land.plot(ax=ax, color='#E0E0E0', edgecolor='none') # 육지: 회색

    ax.set_xlim(lon_min, lon_max)
    ax.set_ylim(lat_min, lat_max)

    if show_grid == 'Y':
        ax.grid(True, linestyle='-', linewidth=0.5, color='#AAAAAA', zorder=0)
        
        def lon_formatter(x, pos):
            if x > 0: return f'{int(x)}°E'
            elif x < 0: return f'{int(abs(x))}°W'
            else: return '0°'

        def lat_formatter(x, pos):
            if x > 0: return f'{int(x)}°N'
            elif x < 0: return f'{int(abs(x))}°S'
            else: return 'EQ'

        ax.xaxis.set_major_formatter(plt.FuncFormatter(lon_formatter))
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lat_formatter))
        ax.xaxis.set_major_locator(MultipleLocator(grid_interval))
        ax.yaxis.set_major_locator(MultipleLocator(grid_interval))
    else:
        ax.set_axis_off()

    # 3. 웹 화면에 지도 표시
    st.pyplot(fig)

    # 4. 다운로드 버튼 추가
    import io
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches='tight', pad_inches=0.1, facecolor='#FFFFFF')
    st.download_button(
        label="📥 생성된 지도 PNG 다운로드",
        data=buf.getvalue(),
        file_name="custom_map.png",
        mime="image/png"
    )
else:
    st.error("데이터 파일을 찾을 수 없습니다. 폴더 구성을 확인해주세요.")