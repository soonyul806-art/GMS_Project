import streamlit as st
import pandas as pd
import json

st.set_page_config(page_title="모바일 센서 수집기", layout="centered")

st.title("📱 모바일 센서 수집기")

# 센서 데이터 초기화
if "sensor_data" not in st.session_state:
    st.session_state.sensor_data = None

# 자바스크립트 코드 삽입
sensor_script = """
<script>
let collecting = false;
let sensorData = [];

function sendSensorData() {
    const encoded = encodeURIComponent(JSON.stringify(sensorData));
    const newUrl = new URL(window.location.href);
    newUrl.searchParams.set("sensor_data", encoded);
    window.location.href = newUrl.toString();
}

// 센서 수집 시작
function startCollection() {
    if (collecting) return;
    collecting = true;
    sensorData = [];

    if (window.DeviceMotionEvent) {
        window.addEventListener('devicemotion', function(event) {
            if (!collecting) return;
            const acc = event.accelerationIncludingGravity;
            const rot = event.rotationRate;
            const timestamp = Date.now();
            sensorData.push({
                time: timestamp,
                ax: acc.x,
                ay: acc.y,
                az: acc.z,
                alpha: rot?.alpha || 0,
                beta: rot?.beta || 0,
                gamma: rot?.gamma || 0
            });
        });
    } else {
        alert("DeviceMotionEvent를 지원하지 않는 브라우저입니다.");
    }
}

// 센서 수집 종료
function stopCollection() {
    collecting = false;
    setTimeout(sendSensorData, 500);  // 약간의 지연 후 데이터 전송
}
</script>
"""

st.components.v1.html(sensor_script, height=0)

# 버튼 UI
col1, col2 = st.columns(2)
with col1:
    if st.button("▶️ 센서 수집 시작"):
        st.components.v1.html("<script>startCollection();</script>", height=0)
with col2:
    if st.button("⏹ 센서 수집 종료 및 데이터 전송"):
        st.components.v1.html("<script>stopCollection();</script>", height=0)

# URL 파라미터 수신 처리
params = st.query_params
if "sensor_data" in params:
    try:
        raw = params["sensor_data"][0]
        df = pd.DataFrame(json.loads(raw))
        st.session_state.sensor_data = df
        st.experimental_rerun()  # 다시 로딩하여 쿼리 제거
    except Exception as e:
        st.error(f"데이터 파싱 실패: {e}")

# 수신된 센서 데이터 표시
if st.session_state.sensor_data is not None:
    st.subheader("📊 수신된 센서 데이터 (최근 5개)")
    st.dataframe(st.session_state.sensor_data.tail(5))
