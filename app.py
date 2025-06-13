import streamlit as st
import pandas as pd
import datetime
import matplotlib.pyplot as plt
import matplotlib

matplotlib.rcParams['font.family'] = 'NanumGothic'
matplotlib.rcParams['axes.unicode_minus'] = False

st.set_page_config(page_title="BlastTap 6.3 Master AI 고로조업 최적화", layout="wide")
st.title("🔥 BlastTap 6.3 Master AI 고로조업 실전 수지엔진 (누적출선량 교정반영)")

if 'log' not in st.session_state:
    st.session_state['log'] = []

# 07시 기준일자 적용
now = datetime.datetime.now()
if now.hour < 7:
    base_date = datetime.date.today() - datetime.timedelta(days=1)
else:
    base_date = datetime.date.today()

today_start = datetime.datetime.combine(base_date, datetime.time(7, 0))
elapsed_minutes = (now - today_start).total_seconds() / 60
elapsed_minutes = min(elapsed_minutes, 1440)

# ① 장입수지 입력
st.sidebar.header("① 장입수지 입력")
ore_per_charge = st.sidebar.number_input("Ore 장입량 (ton/ch)", value=165.0)
coke_per_charge = st.sidebar.number_input("Coke 장입량 (ton/ch)", value=33.5)
ore_coke_ratio = st.sidebar.number_input("Ore/Coke 비율 (-)", value=5.0)
tfe_percent = st.sidebar.number_input("T.Fe 함량 (%)", value=58.0)
slag_ratio = st.sidebar.number_input("슬래그 비율 (용선:슬래그)", value=2.25)
ore_size = st.sidebar.number_input("Ore 입도 (mm)", value=20.0)
coke_size = st.sidebar.number_input("Coke 입도 (mm)", value=60.0)
reduction_efficiency = st.sidebar.number_input("환원율 (기본)", value=1.0)

# ② 용해/설비 입력
st.sidebar.header("② 용해/설비 입력")
melting_capacity = st.sidebar.number_input("용해능력 (°CKN m²/T-P)", value=2800)
furnace_volume = st.sidebar.number_input("고로 유효내용적 (m³)", value=3200)

# ③ 조업지수 입력
st.sidebar.header("③ 조업지수 입력")
blast_volume = st.sidebar.number_input("송풍량 (Nm³/min)", value=4000.0)
oxygen_enrichment = st.sidebar.number_input("산소부화율 (%)", value=3.0)
oxygen_blow = st.sidebar.number_input("산소부화량 (Nm³/hr)", value=6000.0)
humidification = st.sidebar.number_input("조습량 (g/Nm³)", value=20.0)
top_pressure = st.sidebar.number_input("노정압 (kg/cm²)", value=2.5)
blast_pressure = st.sidebar.number_input("풍압 (kg/cm²)", value=3.8)

# ④ FeO / Si 보정 입력
st.sidebar.header("④ FeO / Si 보정 입력")
feo = st.sidebar.number_input("슬래그 FeO (%)", value=0.8)
si = st.sidebar.number_input("용선 Si (%)", value=0.5)
K_factor = st.sidebar.number_input("K 보정계수", value=1.0)

# ⑤ 용선온도 입력
st.sidebar.header("⑤ 용선온도 입력")
measured_temp = st.sidebar.number_input("현장 용선온도 (°C)", value=1520.0)

# ⑥ 장입속도 입력
st.sidebar.header("⑥ 장입속도 입력")
mode = st.sidebar.radio("장입방식 선택", ["장입속도 기반 (자동)", "누적 Charge 수 직접입력"])
if mode == "장입속도 기반 (자동)":
    charge_rate = st.sidebar.number_input("장입속도 (charge/h)", value=5.5)
else:
    elapsed_charges = st.sidebar.number_input("누적 Charge 수 (charge)", value=30.0)

# ⑦ 출선 실적 입력
st.sidebar.header("⑦ 출선 실적 입력")
lead_start_time = st.sidebar.time_input("선행 출선 시작시각", value=datetime.time(8, 0))
follow_start_time = st.sidebar.time_input("후행 출선 시작시각", value=datetime.time(9, 0))
lead_speed = st.sidebar.number_input("선행 출선속도 (ton/min)", value=4.8)
follow_speed = st.sidebar.number_input("후행 출선속도 (ton/min)", value=4.8)
lead_target = st.sidebar.number_input("선행 목표출선량 (ton)", value=1215.0)
completed_taps = st.sidebar.number_input("종료된 TAP 수 (EA)", value=5)

# ⑧ 계획입력
st.sidebar.header("⑧ 계획 스케줄 입력")
plan_charges = st.sidebar.number_input("금일 계획 Charge 수 (EA)", value=126)
plan_taps = st.sidebar.number_input("금일 계획 TAP 수 (EA)", value=9)
max_residual_limit = st.sidebar.number_input("최대저선한계 (ton)", value=800)

# ⑨ 이론출선량 입력
st.sidebar.header("⑨ 예상 이론출선량 입력")
theoretical_tap = st.sidebar.number_input("예상 이론출선량 (ton)", value=1215.0)

# 실시간 장입 누적 계산
if mode == "장입속도 기반 (자동)":
    elapsed_charges = charge_rate * (elapsed_minutes / 60)

# AI 보정 환원효율
size_effect = (20 / ore_size + 60 / coke_size) / 2
melting_effect = 1 + ((melting_capacity - 2500) / 500) * 0.05
gas_effect = 1 + (blast_volume - 4000) / 8000
oxygen_boost = 1 + (oxygen_enrichment / 10)
humidity_effect = 1 - (humidification / 100)
pressure_boost = 1 + (top_pressure - 2.5) * 0.05
blow_pressure_boost = 1 + (blast_pressure - 3.5) * 0.03
feo_effect = 1 - (feo / 10)
si_effect = 1 + (si / 5)
temp_effect = 1 + ((measured_temp - 1500) / 100) * 0.03

reduction_eff_total = reduction_efficiency * size_effect * melting_effect * gas_effect * \
    oxygen_boost * humidity_effect * pressure_boost * blow_pressure_boost * feo_effect * \
    si_effect * temp_effect * K_factor * 0.9

# 생성량 수지계산
total_ore = ore_per_charge * elapsed_charges
total_fe = total_ore * (tfe_percent / 100)
hot_metal = total_fe * reduction_eff_total
slag = hot_metal / slag_ratio
total_molten = hot_metal + slag

# 출선량 수지계산 (누적출선량 보정 포함!)
lead_start_dt = datetime.datetime.combine(base_date, lead_start_time)
follow_start_dt = datetime.datetime.combine(base_date, follow_start_time)

lead_elapsed = max((now - lead_start_dt).total_seconds() / 60, 0)
follow_elapsed = max((now - follow_start_dt).total_seconds() / 60, 0)

lead_tapped = lead_speed * lead_elapsed
follow_tapped = follow_speed * follow_elapsed

# ✅ [핵심 교정] 누적출선량 보정
completed_tap_amount = completed_taps * theoretical_tap
real_time_in_progress = lead_tapped + follow_tapped
total_tapped = completed_tap_amount + real_time_in_progress

# 저선 수지계산
residual_molten = max(total_molten - total_tapped, 0)
residual_rate = (residual_molten / total_molten) * 100

# 공취시간 예측
lead_close_time = lead_start_dt + datetime.timedelta(minutes=(lead_target / lead_speed))
gap_minutes = (lead_close_time - follow_start_dt).total_seconds() / 60
gap_minutes = max(gap_minutes, 0)

# TAP당 평균 수지계산
avg_hot_metal_per_tap = hot_metal / max(completed_taps, 1)
avg_slag_per_tap = slag / max(completed_taps, 1)

# AI 비트경 추천 및 출선간격 추천
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
    next_tap_interval = "즉시 (0~5분)"

# AI 목표용선온도 산출
base_temp = 1500
oxygen_effect = oxygen_enrichment * 5
blast_effect = (blast_volume - 4000) * 0.02
slag_effect = (slag_ratio - 2.25) * 10
pressure_effect = (top_pressure - 2.5) * 8
target_temp = base_temp + oxygen_effect + blast_effect + slag_effect + pressure_effect

# AI 이론출선량 비교보정
ai_theoretical_tap = avg_hot_metal_per_tap
field_theoretical_tap = theoretical_tap
final_theoretical_tap = (ai_theoretical_tap + field_theoretical_tap) / 2

# 경보판단
if residual_rate >= 9:
    status = "⚠ 저선과다 위험"
elif residual_rate >= 7:
    status = "주의"
else:
    status = "✅ 정상"

# 최종 결과 출력
st.header("📊 AI 실시간 수지분석 결과")

st.write(f"누적 생성량: {total_molten:.1f} ton")
st.write(f"누적 출선량: {total_tapped:.1f} ton")
st.write(f"저선량: {residual_molten:.1f} ton")
st.write(f"저선율: {residual_rate:.2f}%")
st.write(f"조업상태: {status}")
st.write(f"공취 예상시간: {gap_minutes:.1f} 분")
st.write(f"선행폐쇄 예상시각: {lead_close_time.strftime('%H:%M')}")
st.write(f"TAP당 평균 용선배출량: {avg_hot_metal_per_tap:.1f} ton")
st.write(f"TAP당 평균 슬래그배출량: {avg_slag_per_tap:.1f} ton")
st.write(f"추천 비트경: {tap_diameter} Ø")
st.write(f"차기 출선간격 추천: {next_tap_interval}")
st.write(f"AI 목표용선온도: {target_temp:.1f} °C")
st.write(f"현장 용선온도: {measured_temp:.1f} °C")
st.write(f"AI 이론출선량: {ai_theoretical_tap:.1f} ton")
st.write(f"입력 이론출선량: {field_theoretical_tap:.1f} ton")
st.write(f"최종 보정 이론출선량: {final_theoretical_tap:.1f} ton")

# 실시간 수지 시각화
st.header("📊 실시간 수지추적 그래프")

time_labels = [i for i in range(0, int(elapsed_minutes)+1, 15)]
gen_series = [(total_molten / 1440) * t for t in time_labels]
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

# 누적 리포트 기록 및 다운로드
record = {
    "시각": now.strftime('%Y-%m-%d %H:%M:%S'),
    "누적 생성량": total_molten,
    "누적 출선량": total_tapped,
    "저선량": residual_molten,
    "저선율": residual_rate,
    "조업상태": status
}
st.session_state['log'].append(record)

st.header("📋 누적 조업 리포트")
df = pd.DataFrame(st.session_state['log'])
st.dataframe(df)
csv = df.to_csv(index=False).encode('utf-8-sig')
st.download_button("📥 CSV 다운로드", data=csv, file_name="조업리포트_6_3.csv", mime='text/csv')