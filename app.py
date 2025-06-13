import streamlit as st
import pandas as pd
import datetime
import matplotlib.pyplot as plt
import matplotlib

matplotlib.rcParams['font.family'] = 'NanumGothic'
matplotlib.rcParams['axes.unicode_minus'] = False

# 페이지 설정
st.set_page_config(page_title="BlastTap 7.3 Master", layout="wide")
st.title("🔥 BlastTap 7.3 Master — AI 고로조업 실시간 수지통제 시스템")

# 세션 초기화
if 'log' not in st.session_state:
    st.session_state['log'] = []

# 기준일자: 07시 기준일자
now = datetime.datetime.now()
if now.hour < 7:
    base_date = datetime.date.today() - datetime.timedelta(days=1)
else:
    base_date = datetime.date.today()
today_start = datetime.datetime.combine(base_date, datetime.time(7, 0))
elapsed_minutes = (now - today_start).total_seconds() / 60
elapsed_minutes = min(elapsed_minutes, 1440)

# 🔧 용융지연시간 기본설정
st.sidebar.header("💡 용융지연시간 설정")
melting_lag_base = st.sidebar.number_input("용융도달 기본 지연시간 (분)", value=240)

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

# ② 용해능력/설비 입력
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

# ④ 반응속도·열수지 입력
st.sidebar.header("④ 반응속도·열수지 입력")
iron_rate = st.sidebar.number_input("선철 생성속도 (ton/min)", value=9.0)
hot_blast_temp = st.sidebar.number_input("풍온 (°C)", value=1200)
pci_rate = st.sidebar.number_input("미분탄 취입량 (kg/thm)", value=180)

# ⑤ FeO / Si 보정 입력
st.sidebar.header("⑤ FeO / Si 보정 입력")
feo = st.sidebar.number_input("슬래그 FeO (%)", value=0.8)
si = st.sidebar.number_input("용선 Si (%)", value=0.5)
K_factor = st.sidebar.number_input("K 보정계수", value=1.0)

# ⑥ 현장 용선온도 입력
st.sidebar.header("⑥ 현장 용선온도 입력")
measured_temp = st.sidebar.number_input("현장 용선온도 (°C)", value=1520.0)

# ⑦ 목표용선온도 교정계수 입력
st.sidebar.header("⑦ 목표용선온도 교정계수")
target_temp_factor = st.sidebar.slider("AI 목표온도 교정계수", min_value=0.5, max_value=1.2, value=0.8, step=0.05)

# ⑧ TAP당 평균출선량 입력 (TAP 기반 수지용)
st.sidebar.header("⑧ TAP당 평균출선량")
fixed_avg_tap_output = st.sidebar.number_input("TAP당 평균출선량 (ton)", value=1000.0)

# ⑨ 출선구 관리 입력 (7.3 신규)
st.sidebar.header("⑨ 출선구 관리")
lead_taphole = st.sidebar.selectbox("선행 출선구 번호", [1,2,3,4])
follow_taphole = st.sidebar.selectbox("후행 출선구 번호", [1,2,3,4])
last_closed_taphole = st.sidebar.selectbox("최근 종료 TAP 출선구 번호", [1,2,3,4])

# 🔧 장입방식 선택 입력
mode = st.sidebar.radio("장입방식 선택", ["장입속도 기반 (자동)", "누적 Charge 수 직접입력"])

if mode == "장입속도 기반 (자동)":
    charge_rate = st.sidebar.number_input("장입속도 (charge/h)", value=5.5)
    elapsed_charges = charge_rate * (elapsed_minutes / 60)
else:
    charge_rate = 5.5
    elapsed_charges = st.sidebar.number_input("누적 Charge 수 (charge)", value=30.0)

# 🔧 AI 용융지연시간 보정 계산
reference_charge = 5.5
reference_blast = 4000
reference_oxygen = 3.0
reference_humidity = 20
reference_reduction_eff = 1.0

delta_charge = -10 * (charge_rate - reference_charge)
delta_blast = -5 * (blast_volume - reference_blast) / 100
delta_oxygen = -5 * (oxygen_enrichment - reference_oxygen)
delta_humidity = 10 * (humidification - reference_humidity) / 10
delta_reduction = 15 * (reference_reduction_eff - reduction_efficiency)

ai_delay_adjust = delta_charge + delta_blast + delta_oxygen + delta_humidity + delta_reduction
melting_lag_final = melting_lag_base + ai_delay_adjust
melting_lag_final = max(melting_lag_final, 0)
st.sidebar.markdown(f"**AI 용융지연시간 보정결과: {melting_lag_final:.1f} 분**")

# 🔧 AI 환원효율 보정계산
size_effect = (20 / ore_size + 60 / coke_size) / 2
melting_effect = 1 + ((melting_capacity - 2500) / 500) * 0.05
gas_effect = 1 + (blast_volume - 4000) / 8000
oxygen_boost = 1 + (oxygen_enrichment / 10)
humidity_effect = 1 - (humidification / 100)
pressure_boost = 1 + (top_pressure - 2.5) * 0.05
blow_pressure_boost = 1 + (blast_pressure - 3.5) * 0.03
temp_effect = 1 + ((hot_blast_temp - 1100) / 100) * 0.03
pci_effect = 1 + (pci_rate - 150) / 100 * 0.02
iron_rate_effect = iron_rate / 9.0
measured_temp_effect = 1 + ((measured_temp - 1500) / 100) * 0.03

reduction_eff_total = reduction_efficiency * size_effect * melting_effect * gas_effect * \
    oxygen_boost * humidity_effect * pressure_boost * blow_pressure_boost * \
    temp_effect * pci_effect * iron_rate_effect * measured_temp_effect * K_factor * 0.9

# 🔧 장입기반 누적 생산량 (AI 이론생산량)
ore_total = ore_per_charge * elapsed_charges
total_fe = ore_total * (tfe_percent / 100)
production_ton = total_fe * reduction_eff_total

# 🔧 TAP 기반 누적생산량 병렬 계산
tap_based_production = fixed_avg_tap_output * elapsed_charges

# 🔧 장입수지 vs TAP수지 편차 계산
production_gap = production_ton - tap_based_production

# 🔧 출선 실적 입력
st.sidebar.header("⑩ 출선 실적 입력")
lead_start_time = st.sidebar.time_input("선행 출선 시작시각", value=datetime.time(8, 0))
follow_start_time = st.sidebar.time_input("후행 출선 시작시각", value=datetime.time(9, 0))
lead_speed = st.sidebar.number_input("선행 출선속도 (ton/min)", value=4.8)
follow_speed = st.sidebar.number_input("후행 출선속도 (ton/min)", value=4.8)
lead_target = st.sidebar.number_input("선행 목표출선량 (ton)", value=1215.0)
completed_taps = st.sidebar.number_input("종료된 TAP 수 (EA)", value=5)
plan_taps = st.sidebar.number_input("계획 TAP 수 (EA)", value=9)

# 🔧 출선 경과시간 계산
lead_start_dt = datetime.datetime.combine(base_date, lead_start_time)
follow_start_dt = datetime.datetime.combine(base_date, follow_start_time)
lead_elapsed = max((now - lead_start_dt).total_seconds() / 60, 0)
follow_elapsed = max((now - follow_start_dt).total_seconds() / 60, 0)
lead_tapped = lead_speed * lead_elapsed
follow_tapped = follow_speed * follow_elapsed

# 🔧 누적 출선량 계산
avg_tap_output = production_ton / plan_taps if plan_taps > 0 else production_ton / 9
completed_tap_amount = completed_taps * avg_tap_output
total_tapped = completed_tap_amount + lead_tapped + follow_tapped

# 🔧 생산량 초과방지
if total_tapped > production_ton:
    total_tapped = production_ton

# 🔧 저선량 및 저선율 계산
residual_molten = production_ton - total_tapped
residual_rate = (residual_molten / production_ton) * 100

# 🔧 공취 예상시간
lead_close_time = lead_start_dt + datetime.timedelta(minutes=(lead_target / lead_speed))
gap_minutes = max((lead_close_time - follow_start_dt).total_seconds() / 60, 0)

# 🔧 TAP당 평균 수지계산
avg_hot_metal_per_tap = production_ton / max(completed_taps, 1)
avg_slag_per_tap = avg_hot_metal_per_tap / slag_ratio

# 🔧 AI 비트경 추천
if residual_molten < 100 and residual_rate < 5:
    tap_diameter = 43
elif residual_molten < 150 and residual_rate < 7:
    tap_diameter = 45
else:
    tap_diameter = 48

# 🔧 AI 출선간격 추천
if residual_rate < 5:
    next_tap_interval = "15~20분"
elif residual_rate < 7:
    next_tap_interval = "10~15분"
elif residual_rate < 9:
    next_tap_interval = "5~10분"
else:
    next_tap_interval = "즉시 (0~5분)"

# 🔧 AI 목표용선온도 (교정계수 적용)
base_temp = 1500
oxygen_effect = oxygen_enrichment * 5
blast_effect = (blast_volume - 4000) * 0.02
slag_effect = (slag_ratio - 2.25) * 10
pressure_effect = (top_pressure - 2.5) * 8

raw_temp_offset = oxygen_effect + blast_effect + slag_effect + pressure_effect
target_temp = base_temp + (raw_temp_offset * target_temp_factor)

# 🔧 저선경보 (ton 기준)
if residual_molten >= 200:
    status = "🔴 저선 위험 (비상)"
elif residual_molten >= 150:
    status = "🟠 저선과다 누적"
elif residual_molten >= 100:
    status = "🟡 저선 관리권고"
else:
    status = "✅ 정상운전"

# 🔧 출선구 번호 실시간 표시
all_tapholes = {1,2,3,4}
active_tapholes = {lead_taphole, follow_taphole}
standby_tapholes = list(all_tapholes - active_tapholes)

# 🔧 결과 출력
st.header("📊 AI 실시간 수지분석 결과")
st.write(f"누적 생산량 (AI): {production_ton:.1f} ton")
st.write(f"누적 출선량: {total_tapped:.1f} ton")
st.write(f"저선량: {residual_molten:.1f} ton")
st.write(f"저선율: {residual_rate:.2f}%")
st.write(f"수지편차 (장입-출선): {production_gap:.1f} ton")
st.write(f"조업상태: {status}")
st.write(f"공취 예상시간: {gap_minutes:.1f} 분")
st.write(f"선행폐쇄 예상시각: {lead_close_time.strftime('%H:%M')}")
st.write(f"평균 용선배출량: {avg_hot_metal_per_tap:.1f} ton")
st.write(f"평균 슬래그배출량: {avg_slag_per_tap:.1f} ton")
st.write(f"추천 비트경: {tap_diameter} Ø")
st.write(f"차기 출선간격 추천: {next_tap_interval}")
st.write(f"AI 목표용선온도: {target_temp:.1f} °C")
st.write(f"현장 용선온도: {measured_temp:.1f} °C")
st.write(f"AI 자동 용융지연시간: {melting_lag_final:.1f} 분")
st.write(f"선행출선구: {lead_taphole}번, 후행출선구: {follow_taphole}번")
st.write(f"대기출선구 (Standby): {standby_tapholes}")

# 🔧 실시간 수지 시각화
st.header("📊 실시간 수지추적 그래프")

time_labels = [i for i in range(0, int(elapsed_minutes)+1, 15)]

gen_series = [
    (ore_per_charge * (charge_rate * (t / 60)) if mode == "장입속도 기반 (자동)"
     else ore_per_charge * elapsed_charges) * (tfe_percent/100) * reduction_eff_total
    for t in time_labels
]
gen_series = [min(g, production_ton) for g in gen_series]
tap_series = [total_tapped] * len(time_labels)
residual_series = [max(g - total_tapped, 0) for g in gen_series]

plt.figure(figsize=(8, 5))
plt.plot(time_labels, gen_series, label="누적 생산량 (ton)")
plt.plot(time_labels, tap_series, label="누적 출선량 (ton)")
plt.plot(time_labels, residual_series, label="저선량 (ton)")
plt.xlabel("경과시간 (분)")
plt.ylabel("ton")
plt.title("실시간 용융물 수지추적")
plt.ylim(0, production_ton * 1.2)
plt.xlim(0, max(elapsed_minutes, 240))
plt.legend()
plt.grid()
st.pyplot(plt)

# 🔧 누적 리포트 기록 및 CSV 다운로드
record = {
    "시각": now.strftime('%Y-%m-%d %H:%M:%S'),
    "AI 생산량": production_ton,
    "출선량": total_tapped,
    "저선량": residual_molten,
    "수지편차": production_gap,
    "조업상태": status,
    "AI 목표온도": target_temp,
    "선행출선구": lead_taphole,
    "후행출선구": follow_taphole,
}
st.session_state['log'].append(record)

st.header("📋 누적 조업 리포트")
df = pd.DataFrame(st.session_state['log'])
st.dataframe(df)
csv = df.to_csv(index=False).encode('utf-8-sig')
st.download_button("📥 CSV 다운로드", data=csv, file_name="조업리포트_7_3.csv", mime='text/csv')

# 🔧 시스템 안정화 보호코드
if residual_molten < 0:
    residual_molten = 0
if total_tapped > production_ton:
    total_tapped = production_ton