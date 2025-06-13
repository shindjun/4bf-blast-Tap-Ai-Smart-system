# 🔧 출선 실적 입력
st.sidebar.header("⑦ 출선 실적 입력")
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

if total_tapped > production_ton:
    total_tapped = production_ton

# 🔧 저선 수지 계산
residual_molten = production_ton - total_tapped
residual_rate = (residual_molten / production_ton) * 100

# 🔧 AI 추천 및 공취예측
lead_close_time = lead_start_dt + datetime.timedelta(minutes=(lead_target / lead_speed))
gap_minutes = max((lead_close_time - follow_start_dt).total_seconds() / 60, 0)

avg_hot_metal_per_tap = production_ton / max(completed_taps, 1)
avg_slag_per_tap = avg_hot_metal_per_tap / slag_ratio

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

# 🔧 AI 목표온도 예측
base_temp = 1500
oxygen_effect = oxygen_enrichment * 5
blast_effect = (blast_volume - 4000) * 0.02
slag_effect = (slag_ratio - 2.25) * 10
pressure_effect = (top_pressure - 2.5) * 8
target_temp = base_temp + oxygen_effect + blast_effect + slag_effect + pressure_effect

# 🔧 경보판단
if residual_rate >= 9:
    status = "⚠ 저선과다 위험"
elif residual_rate >= 7:
    status = "주의"
else:
    status = "✅ 정상"

# 🔧 결과 출력
st.header("📊 AI 실시간 수지분석 결과")
st.write(f"누적 생산량: {production_ton:.1f} ton")
st.write(f"누적 출선량: {total_tapped:.1f} ton")
st.write(f"저선량: {residual_molten:.1f} ton")
st.write(f"저선율: {residual_rate:.2f}%")
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

# 🔧 시각화
st.header("📊 실시간 수지추적 그래프")
time_labels = [i for i in range(0, int(elapsed_minutes)+1, 15)]
gen_series = [(ore_per_charge * (charge_rate * (t / 60)) if mode=="장입속도 기반 (자동)" else ore_per_charge * elapsed_charges) * (tfe_percent/100) * reduction_eff_total for t in time_labels]
gen_series = [min(g, production_ton) for g in gen_series]
tap_series = [total_tapped] * len(time_labels)
residual_series = [g - total_tapped for g in gen_series]

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

# 🔧 누적 리포트 기록
record = {
    "시각": now.strftime('%Y-%m-%d %H:%M:%S'),
    "누적 생산량": production_ton,
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
st.download_button("📥 CSV 다운로드", data=csv, file_name="조업리포트_7_1.csv", mime='text/csv')
