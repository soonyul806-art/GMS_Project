import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import joblib

# === 모델 로드 (model.pkl 파일이 같은 폴더에 있어야 합니다) ===
@st.cache_resource
def load_model():
    return joblib.load("model.pkl")

model = load_model()

st.title("📱 모바일 센서 데이터 수집 + 모델 예측 데모")

# 세션 상태 초기화
if "sensor_data" not in st.session_state:
    st.session_state.sensor_data = []

# ===== 자바스크립트로 센서 데이터 수집 및 Streamlit으로 전송 =====
sensor_component = components.html(
    """
    <script>
    // iOS 센서 권한 요청 함수
    async function requestPermission() {
        if (
            typeof DeviceMotionEvent !== 'undefined' && 
            typeof DeviceMotionEvent.requestPermission === 'function'
        ) {
            try {
                const response = await DeviceMotionEvent.requestPermission();
                if (response !== 'granted') {
                    alert("센서 권한이 거부되었습니다.");
                    return false;
                }
                return true;
            } catch(err) {
                alert("권한 요청 실패: " + err);
                return false;
            }
        }
        return true;
    }

    // 센서 데이터 버퍼
    let dataBuffer = [];

    // 센서 데이터 전송 주기(ms)
    const SEND_INTERVAL = 300;

    // 센서 데이터 수집 시작 함수
    async function startSensor() {
        const permitted = await requestPermission();
        if (!permitted) return;

        window.addEventListener('devicemotion', (event) => {
            const acc = event.accelerationIncludingGravity || {};
            const rot = event.rotationRate || {};

            dataBuffer.push({
                timestamp: Date.now(),
                acc_x: acc.x || 0,
                acc_y: acc.y || 0,
                acc_z: acc.z || 0,
                gyro_alpha: rot.alpha || 0,
                gyro_beta: rot.beta || 0,
                gyro_gamma: rot.gamma || 0
            });
        });

        setInterval(() => {
            if (dataBuffer.length > 0) {
                window.parent.postMessage(
                    {type: "sensor_data", payload: dataBuffer},
                    "*"
                );
                dataBuffer = [];
            }
        }, SEND_INTERVAL);
    }

    // 센서 수집 시작 요청 이벤트 받기
    window.addEventListener("message", (event) => {
        if (event.data === "start_sensor") {
            startSensor();
        }
    });
    </script>
    <button onclick="window.parent.postMessage('start_sensor', '*')">센서 수집 시작</button>
    """,
    height=150,
)

# ===== 센서 데이터 수신 및 저장 =====
# Streamlit은 postMessage 이벤트를 직접 받을 수 없으니 workaround를 씁니다.
# st.experimental_get_query_params()나 session_state 변경 등으로 바로 연결 불가.

# 여기선 st.experimental_rerun() 같은 강제 새로고침 없이
# 우회해서 센서 데이터를 받으려면 streamlit_javascript 같은 별도 컴포넌트 필요.
# 하지만 외부 라이브러리 없이 간단히 하기 위해 아래처럼 진행합니다.

# 메시지를 받을 수 있는 간단한 트릭 - Streamlit 앱 내에서 자바스크립트가 postMessage를 보내면 
# window.onmessage 이벤트를 리스닝해서 text_area 값을 바꾸는 방식 활용

st.markdown("""
<script>
window.addEventListener("message", event => {
    if(event.data.type === "sensor_data") {
        const dataStr = JSON.stringify(event.data.payload);
        const textarea = window.parent.document.querySelector('textarea[data-testid="stSensorDataInput"]');
        if(textarea) {
            textarea.value = dataStr;
            textarea.dispatchEvent(new Event('input', { bubbles: true }));
        }
    }
});
</script>
""", unsafe_allow_html=True)

# === 센서 데이터 입력용 텍스트박스 (보이지 않게 처리) ===
sensor_data_json = st.text_area(
    label="센서 데이터 (내부용)", 
    key="stSensorDataInput",
    height=150,
    value="[]",
    label_visibility="collapsed"
)

# === 센서 데이터 파싱 및 세션에 저장 ===
try:
    new_data = pd.DataFrame(eval(sensor_data_json))
    if not new_data.empty:
        # 중복 없이 세션에 추가
        old_df = pd.DataFrame(st.session_state.sensor_data)
        combined = pd.concat([old_df, new_data]).drop_duplicates().reset_index(drop=True)
        st.session_state.sensor_data = combined.to_dict('records')
except Exception as e:
    st.warning(f"센서 데이터 파싱 오류: {e}")

# === 수집된 센서 데이터 출력 및 모델 예측 ===
if len(st.session_state.sensor_data) > 10:
    st.subheader("수집된 센서 데이터 (최근 5개)")
    df = pd.DataFrame(st.session_state.sensor_data)
    st.dataframe(df.tail(5))

    # 단순 평균으로 피처 생성
    features = df.mean()[["acc_x", "acc_y", "acc_z", "gyro_alpha", "gyro_beta", "gyro_gamma"]].values.reshape(1, -1)
    prediction = model.predict(features)[0]

    st.success(f"예측 결과: **{prediction}**")
else:
    st.info("센서 데이터를 수집하려면 위 버튼을 누르고, 휴대폰을 움직여주세요.")

