import streamlit as st
import pandas as pd
import datetime
import matplotlib.pyplot as plt

st.set_page_config(page_title="BlastTap 6.0 AI Smart Control System", layout="wide")
st.title("🔥 BlastTap 6.0 AI Smart Control System")

if 'log' not in st.session_state:
    st.session_state['log'] = []

# -----------------------------------------------------------
# ① 장입수지 입력
# -----------------------------------------------------------
st.sidebar.header("장입수지 입력")
ore_per_charge = st.sidebar.number_input("Ore 장입량 (ton/ch)", value=165.0)
coke_per_charge = st.sidebar.number_input("Coke 장입량 (ton/ch)", value=33.5)
ore_coke_ratio = st.sidebar.number_input("Ore/Coke 비율", value=5.0)
tfe_percent = st.sidebar.number_input("T.Fe (%)", value=58.0)
slag_ratio = st.sidebar.number_input("Slag비율 (용선:슬래그)", value=2.25)
ore_size = st.sidebar.number_input("Ore 입도 (mm)", value=20.0)
coke_size = st.sidebar.number_input("Coke 입도 (mm)", value=60.0)
reduction_efficiency = st.sidebar.number_input("환원율 (기본)", value=1.0)
melting_capacity = st.sidebar.number_input("용해능력 (°CKN m²/T-P)", value=2800)
furnace_volume = st.sidebar.number_input("고로 유효내용적 (m³)", value=3200.0)
# -----------------------------------------------------------
# ② 조업지수 입력
# -----------------------------------------------------------
st.sidebar.header("조업지수 입력")
blast_volume = st.sidebar.number_input("송풍량 (Nm³/min)", value=4000.0)
oxygen_enrichment = st.sidebar.number_input("산소부화율 (%)", value=3.0)
oxygen_blow = st.sidebar.number_input("산소부화량 (Nm³/hr)", value=6000.0)
humidification = st.sidebar.number_input("조습량 (g/Nm³)", value=20.0)
top_pressure = st.sidebar.number_input("노정압 (kg/cm²)", value=2.5)
blast_pressure = st.sidebar.number_input("풍압 (kg/cm²)", value=3.8)

# -----------------------------------------------------------
# ③ FeO / Si 보정 입력
# -----------------------------------------------------------
st.sidebar.header("FeO / Si 보정")
feo = st.sidebar.number_input("슬래그 FeO (%)", value=0.8)
si = st.sidebar.number_input("용선 Si (%)", value=0.5)
K_factor = st.sidebar.number_input("K 보정계수", value=1.0)
# -----------------------------------------------------------
# ④ AI 목표온도 자동산출 및 현장측정온도 입력
# -----------------------------------------------------------
base_temp = 1500
oxygen_effect = oxygen_enrichment * 5
blast_effect = (blast_volume - 4000) * 0.02
slag_effect = (slag_ratio - 2.25) * 10
pressure_effect = (top_pressure - 2.5) * 8
target_temp = base_temp + oxygen_effect + blast_effect + slag_effect + pressure_effect

st.sidebar.write(f"AI 자동목표용선온도: {target_temp:.1f} °C")
measured_temp = st.sidebar.number_input("현장 측정 용선온도 (°C)", value=1520.0)

# -----------------------------------------------------------
# ⑤ 장입속도 / 경과시간 입력
# -----------------------------------------------------------
now = datetime.datetime.now()
today_start = datetime.datetime.combine(datetime.date.today(), datetime.time(0, 0))
elapsed_minutes = (now - today_start).total_seconds() / 60
elapsed_minutes = min(elapsed_minutes, 1440)

st.sidebar.header("장입속도 입력")
mode = st.sidebar.radio("장입방식", ["장입속도 기반 (자동)", "누적 Charge 직접입력"])
if mode == "장입속도 기반 (자동)":
    charge_rate = st.sidebar.number_input("장입속도 (charge/h)", value=5.5)
    elapsed_charges = charge_rate * (elapsed_minutes / 60)
else:
    elapsed_charges = st.sidebar.number_input("누적 Charge 수", value=30.0)

# -----------------------------------------------------------
# ⑥ 출선 실적 입력 (시각 및 속도)
# -----------------------------------------------------------
st.sidebar.header("출선 실적 입력")
lead_start_time = st.sidebar.time_input("선행 출선 시작시각", value=datetime.time(8, 0), step=60)
follow_start_time = st.sidebar.time_input("후행 출선 시작시각", value=datetime.time(9, 0), step=60)
lead_start_dt = datetime.datetime.combine(datetime.date.today(), lead_start_time)
follow_start_dt = datetime.datetime.combine(datetime.date.today(), follow_start_time)
lead_elapsed = (now - lead_start_dt).total_seconds() / 60
follow_elapsed = (now - follow_start_dt).total_seconds() / 60

lead_speed = st.sidebar.number_input("선행 출선속도 (ton/min)", value=4.8)
follow_speed = st.sidebar.number_input("후행 출선속도 (ton/min)", value=4.8)
lead_target = st.sidebar.number_input("선행 목표출선량 (ton)", value=1215.0)

# -----------------------------------------------------------
# ⑦ TAP수 입력
# -----------------------------------------------------------
st.sidebar.header("TAP 실적")
completed_taps = st.sidebar.number_input("현재 종료된 TAP 수", value=5)
# -----------------------------------------------------------
# ⑧ 환원효율 전체 AI 보정
# -----------------------------------------------------------
size_effect = (20 / ore_size + 60 / coke_size) / 2
melting_effect = 1 + ((melting_capacity - 2500) / 500) * 0.05
gas_effect = 1 + (blast_volume - 4000) / 8000
oxygen_boost = 1 + (oxygen_enrichment / 10)
humidity_effect = 1 - (humidification / 100)
pressure_boost = 1 + (top_pressure - 2.5) * 0.05
blow_pressure_boost = 1 + (blast_pressure - 3.5) * 0.03
feo_effect = 1 - (feo / 10)
si_effect = 1 + (si / 5)
temp_effect = 1 + ((measured_temp - target_temp) / 100) * 0.03

reduction_eff_total = reduction_efficiency * size_effect * melting_effect * \
                      gas_effect * oxygen_boost * humidity_effect * \
                      pressure_boost * blow_pressure_boost * feo_effect * \
                      si_effect * temp_effect * K_factor * 0.9

# -----------------------------------------------------------
# ⑨ 생성량 수지계산
# -----------------------------------------------------------
total_ore = ore_per_charge * elapsed_charges
total_fe = total_ore * (tfe_percent / 100)
hot_metal = total_fe * reduction_eff_total
slag = hot_metal / slag_ratio
total_molten = hot_metal + slag
# -----------------------------------------------------------
# ⑩ 출선량 계산
# -----------------------------------------------------------
lead_in_progress = lead_speed * lead_elapsed
follow_in_progress = follow_speed * follow_elapsed
total_tapped = lead_in_progress + follow_in_progress

# -----------------------------------------------------------
# ⑪ 저선량 및 경보계산
# -----------------------------------------------------------
residual_molten = max(total_molten - total_tapped, 0)
residual_rate = (residual_molten / total_molten) * 100

if residual_rate >= 9: status = "⚠ 저선과다 위험"
elif residual_rate >= 7: status = "주의"
else: status = "✅ 정상"

# -----------------------------------------------------------
# ⑫ 공취시간 예측
# -----------------------------------------------------------
lead_close_time = lead_start_dt + datetime.timedelta(minutes=(lead_target / lead_speed))
gap_minutes = (lead_close_time - follow_start_dt).total_seconds() / 60

# -----------------------------------------------------------
# ⑬ TAP당 평균 배출량 계산
# -----------------------------------------------------------
avg_hot_metal_per_tap = hot_metal / completed_taps
avg_slag_per_tap = slag / completed_taps

# -----------------------------------------------------------
# ⑭ 비트경 및 출선간격 추천
# -----------------------------------------------------------
if residual_molten < 100 and residual_rate < 5:
    tap_diameter = 43
elif residual_molten < 150 and residual_rate < 7:
    tap_diameter = 45
else:
    tap_diameter = 48

if residual_rate < 5:
    next_tap_interval = "15~20분"
elif residual_rate < 7:
    next_tap_interval = "10~15분"
elif residual_rate < 9:
    next_tap_interval = "5~10분"
else:
    next_tap_interval = "0~5분 (즉시 권고)"
# -----------------------------------------------------------
# ⑮ 결과 출력
# -----------------------------------------------------------
st.header("📊 AI 수지분석 결과")

st.write(f"누적 생성량: {total_molten:.1f} ton")
st.write(f"누적 배출량: {total_tapped:.1f} ton")
st.write(f"생산-배출차 (저선량): {residual_molten:.1f} ton")
st.write(f"저선율: {residual_rate:.2f} %")
st.write(f"조업상태: {status}")
st.write(f"선행 예상폐쇄시각: {lead_close_time.strftime('%H:%M')}")
st.write(f"공취 예상시간: {gap_minutes:.1f} 분")
st.write(f"출선당 평균 용선배출량: {avg_hot_metal_per_tap:.1f} ton/TAP")
st.write(f"출선당 평균 슬래그배출량: {avg_slag_per_tap:.1f} ton/TAP")
st.write(f"추천 비트경: {tap_diameter} Ø")
st.write(f"차기 출선간격 추천: {next_tap_interval}")
st.write(f"AI 자동목표용선온도: {target_temp:.1f} °C")
st.write(f"현장 측정 용선온도: {measured_temp:.1f} °C")

# -----------------------------------------------------------
실시간 수지 시각화 (수치변화 강조 안정판)
st.header("📊 Real-time Smelting Balance Tracking")

time_labels = [i for i in range(0, int(elapsed_minutes)+1, 15)]  # 15분 간격으로 시간축 세분화
gen_series = [(total_molten / 1440) * t for t in time_labels]
tap_series = [total_tapped] * len(time_labels)
residual_series = [g - total_tapped for g in gen_series]

plt.figure(figsize=(8, 5))
plt.plot(time_labels, gen_series, label="Total Generation (ton)")
plt.plot(time_labels, tap_series, label="Total Tapped (ton)")
plt.plot(time_labels, residual_series, label="Residual Molten (ton)")
plt.xlabel("Elapsed Time (min)")
plt.ylabel("ton")
plt.title("Real-time Smelting Balance")

plt.ylim(0, total_molten * 1.2)  # Y축 변화 확대 (20% 여유)
plt.xlim(0, max(elapsed_minutes, 240))  # X축: 최소 4시간 확대 보정
plt.legend()
plt.grid()
st.pyplot(plt)

# 🔧 누적 기록 저장 (기존 리포트 기록부분 동일 적용)
record = {
    "Time": now.strftime('%Y-%m-%d %H:%M:%S'),
    "Total Generation": total_molten,
    "Total Tapped": total_tapped,
    "Residual": residual_molten,
    "Residual Rate (%)": residual_rate,
    "Status": status
}
st.session_state['log'].append(record)

st.header("📋 Cumulative Operation Report")
df = pd.DataFrame(st.session_state['log'])
st.dataframe(df)
csv = df.to_csv(index=False).encode('utf-8-sig')
st.download_button("📥 Download CSV", data=csv, file_name="operation_report.csv", mime='text/csv')
