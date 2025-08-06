import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import json
import joblib

@st.cache_resource
def load_model():
    return joblib.load("model.pkl")

model = load_model()

st.title("📱 센서 데이터 수집 + 실시간 예측")

if "sensor_data" not in st.session_state:
    st.session_state.sensor_data = pd.DataFrame(columns=[
        "acc_x", "acc_y", "acc_z", "gyro_alpha", "gyro_beta", "gyro_gamma"
    ])

# JS → Python 값 수신 (components.html의 리턴값으로 받음)
sensor_data_json = components.html(
    """
    <button onclick="startSensor()">센서 수집 시작</button>
    <script>
    async function startSensor() {
        if (typeof DeviceMotionEvent !== 'undefined' && 
            typeof DeviceMotionEvent.requestPermission === 'function') {
            const res = await DeviceMotionEvent.requestPermission();
            if (res !== 'granted') {
                alert("센서 권한 거부됨");
                return;
            }
        }
        let dataBuffer = [];
        window.addEventListener('devicemotion', e => {
            const acc = e.accelerationIncludingGravity || {};
            const rot = e.rotationRate || {};
            dataBuffer.push({
                acc_x: acc.x || 0,
                acc_y: acc.y || 0,
                acc_z: acc.z || 0,
                gyro_alpha: rot.alpha || 0,
                gyro_beta: rot.beta || 0,
                gyro_gamma: rot.gamma || 0
            });
            if (dataBuffer.length >= 20) {
                const toSend = JSON.stringify(dataBuffer);
                dataBuffer = [];
                // 공식 규격: type=streamlit:setComponentValue, value=데이터
                window.parent.postMessage({type:"streamlit:setComponentValue", value: toSend}, "*");
            }
        });
    }
    </script>
    """,
    height=150,
)

# sensor_data_json은 JSON 문자열 (JS에서 보낸 데이터 chunk)
if sensor_data_json:
    try:
        new_data = pd.DataFrame(json.loads(sensor_data_json))
        # 세션 상태의 DataFrame에 새 데이터 추가
        st.session_state.sensor_data = pd.concat([st.session_state.sensor_data, new_data], ignore_index=True)
        # 슬라이딩 윈도우: 최근 100개만 유지
        st.session_state.sensor_data = st.session_state.sensor_data.tail(100)
    except Exception as e:
        st.warning(f"데이터 파싱 오류: {e}")

if len(st.session_state.sensor_data) > 10:
    st.subheader("최근 센서 데이터")
    st.dataframe(st.session_state.sensor_data.tail(5))

    # 평균값을 특징으로 사용해 예측
    features = st.session_state.sensor_data.mean()[[
        "acc_x", "acc_y", "acc_z", "gyro_alpha", "gyro_beta", "gyro_gamma"
    ]].values.reshape(1, -1)

    prediction = model.predict(features)[0]
    st.success(f"예측 결과: **{prediction}**")
else:
    st.info("센서 데이터를 수집하려면 '센서 수집 시작' 버튼을 누르고 휴대폰을 움직이세요.")
