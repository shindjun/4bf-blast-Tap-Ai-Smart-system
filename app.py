import streamlit as st
import pandas as pd
import datetime
import matplotlib.pyplot as plt
import matplotlib

# 📌 한글 폰트 설정 (폰트깨짐 방지)
matplotlib.rcParams['font.family'] = 'NanumGothic'
matplotlib.rcParams['axes.unicode_minus'] = False

st.set_page_config(page_title="BlastTap 6.1+ AI Smart Control System", layout="wide")
st.title("🔥 BlastTap 6.1+ AI 스마트 고로조업 수지통합 시스템")

if 'log' not in st.session_state:
    st.session_state['log'] = []

# ------------------------------
# ① 장입수지 입력
# ------------------------------
st.sidebar.header("장입수지 입력")
ore_per_charge = st.sidebar.number_input("Ore 장입량 (ton/ch)", value=165.0)
coke_per_charge = st.sidebar.number_input("Coke 장입량 (ton/ch)", value=33.5)
ore_coke_ratio = st.sidebar.number_input("Ore/Coke 비율", value=5.0)
tfe_percent = st.sidebar.number_input("T.Fe (%)", value=58.0)
slag_ratio = st.sidebar.number_input("슬래그 비율 (용선:슬래그)", value=2.25)
ore_size = st.sidebar.number_input("Ore 입도 (mm)", value=20.0)
coke_size = st.sidebar.number_input("Coke 입도 (mm)", value=60.0)
reduction_efficiency = st.sidebar.number_input("환원율", value=1.0)
melting_capacity = st.sidebar.number_input("용해능력 (°CKN m²/T-P)", value=2800)

# ------------------------------
# ② 조업지수 입력
# ------------------------------
st.sidebar.header("조업지수 입력")
blast_volume = st.sidebar.number_input("송풍량 (Nm³/min)", value=4000.0)
oxygen_enrichment = st.sidebar.number_input("산소부화율 (%)", value=3.0)
humidification = st.sidebar.number_input("조습량 (g/Nm³)", value=20.0)
top_pressure = st.sidebar.number_input("노정압 (kg/cm²)", value=2.5)
blast_pressure = st.sidebar.number_input("풍압 (kg/cm²)", value=3.8)

# ------------------------------
# ③ 장입물 도달시간 입력
# ------------------------------
st.sidebar.header("장입물 도달시간 (용융전환 지연시간)")
logistic_delay = st.sidebar.number_input("장입→용융 지연시간 (분)", value=270)

# ------------------------------
# ④ 실시간 시간경과
# ------------------------------
now = datetime.datetime.now()
today_start = datetime.datetime.combine(datetime.date.today(), datetime.time(0, 0))
elapsed_minutes = (now - today_start).total_seconds() / 60
elapsed_minutes = min(elapsed_minutes, 1440)

# ------------------------------
# ⑤ 출선 실적 입력
# ------------------------------
st.sidebar.header("출선 실적 입력")
lead_start_time = st.sidebar.time_input("선행 출선 시작시각", value=datetime.time(8, 0))
follow_start_time = st.sidebar.time_input("후행 출선 시작시각", value=datetime.time(9, 0))
lead_start_dt = datetime.datetime.combine(datetime.date.today(), lead_start_time)
follow_start_dt = datetime.datetime.combine(datetime.date.today(), follow_start_time)
lead_elapsed = max((now - lead_start_dt).total_seconds() / 60, 0)
follow_elapsed = max((now - follow_start_dt).total_seconds() / 60, 0)

lead_speed = st.sidebar.number_input("선행 출선속도 (ton/min)", value=4.8)
follow_speed = st.sidebar.number_input("후행 출선속도 (ton/min)", value=4.8)
completed_taps = st.sidebar.number_input("종료된 TAP 수", value=5)
default_tap_amount = st.sidebar.number_input("평균 TAP 출선량 (ton)", value=1215.0)

# ------------------------------
# ⑥ 생성량 및 수지 계산
# ------------------------------
total_charges = completed_taps * 24  # 예시 전체 Charge 수 추정
total_ore = ore_per_charge * total_charges
total_fe = total_ore * (tfe_percent / 100)

size_effect = (20 / ore_size + 60 / coke_size) / 2
melting_effect = 1 + ((melting_capacity - 2500) / 500) * 0.05
gas_effect = 1 + (blast_volume - 4000) / 8000
oxygen_boost = 1 + (oxygen_enrichment / 10)
humidity_effect = 1 - (humidification / 100)
pressure_boost = 1 + (top_pressure - 2.5) * 0.05
blow_pressure_boost = 1 + (blast_pressure - 3.5) * 0.03

reduction_eff_total = reduction_efficiency * size_effect * melting_effect * \
                      gas_effect * oxygen_boost * humidity_effect * \
                      pressure_boost * blow_pressure_boost * 0.9

hot_metal = total_fe * reduction_eff_total
slag = hot_metal / slag_ratio
total_molten = hot_metal + slag

molten_time_minutes = logistic_delay
gen_series_value = (total_molten / molten_time_minutes) * elapsed_minutes
gen_series_value = min(gen_series_value, total_molten)

lead_in_progress = lead_speed * lead_elapsed
follow_in_progress = follow_speed * follow_elapsed
total_tapped = lead_in_progress + follow_in_progress

residual_molten = max(gen_series_value - total_tapped, 0)
residual_rate = (residual_molten / total_molten) * 100

# ------------------------------
# 📊 결과 출력
# ------------------------------
st.header("📊 AI 실시간 수지분석 결과")
st.write(f"누적 생성량: {gen_series_value:.1f} ton")
st.write(f"누적 출선량: {total_tapped:.1f} ton")
st.write(f"현재 저선량: {residual_molten:.1f} ton")
st.write(f"저선율: {residual_rate:.2f}%")

# ------------------------------
# 📊 실시간 수지 시각화
# ------------------------------
st.header("📊 실시간 수지추적 그래프")

time_labels = [i for i in range(0, int(elapsed_minutes)+1, 15)]
gen_series = [(total_molten / molten_time_minutes) * t for t in time_labels]
gen_series = [min(g, total_molten) for g in gen_series]
tap_series = [total_tapped] * len(time_labels)
residual_series = [g - total_tapped for g in gen_series]

plt.figure(figsize=(8, 5))
plt.plot(time_labels, gen_series, label="누적 생성량 (ton)")
plt.plot(time_labels, tap_series, label="누적 출선량 (ton)")
plt.plot(time_labels, residual_series, label="저선량 (ton)")
plt.xlabel("경과시간 (분)")
plt.ylabel("ton")
plt.title("실시간 용융물 수지추적")
plt.ylim(0, total_molten * 1.2)
plt.xlim(0, max(elapsed_minutes, 240))
plt.legend()
plt.grid()
st.pyplot(plt)
