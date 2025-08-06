import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import json
import joblib
import os
import requests
import numpy as np

# --- 1. 설정 및 상수 정의 ---
# 파일 용량이 큰 경우, 직접 다운로드 가능한 Google Drive 링크를 사용합니다.
# 파일 ID만 사용하며, 다운로드 로직이 복잡한 과정을 처리합니다.
GOOGLE_DRIVE_FILE_ID = "1pjbLZLcSc56chOuVEOlogZWFesUTYMOo"
MODEL_FILE_NAME = "gms_activity_model.pkl"
LABELS = {0: '앉아 있기', 1: '서기', 2: 걷기', 3: '자전거 타기', 4: '버스 타기', 5: '자동차 운전'}
PREDICTION_WINDOW_SIZE = 50

# --- 2. 모델 다운로드 및 로드 (더욱 안정적인 방식) ---
def download_file_from_google_drive(file_id, destination):
    URL = "https://docs.google.com/uc?export=download"
    session = requests.Session()
    
    response = session.get(URL, params = { 'id' : file_id }, stream=True)
    token = get_confirm_token(response)
    
    if token:
        params = { 'id' : file_id, 'confirm' : token }
        response = session.get(URL, params = params, stream=True)
    
    save_response_content(response, destination)
    
def get_confirm_token(response):
    for key, value in response.cookies.items():
        if key.startswith('download_warning'):
            return value
    return None

def save_response_content(response, destination):
    CHUNK_SIZE = 32768
    with open(destination, "wb") as f:
        for chunk in response.iter_content(CHUNK_SIZE):
            if chunk:
                f.write(chunk)

@st.cache_resource(show_spinner=False)
def load_and_cache_model():
    if not os.path.exists(MODEL_FILE_NAME):
        st.info("모델 파일이 없어 다운로드를 시도합니다...")
        try:
            download_file_from_google_drive(GOOGLE_DRIVE_FILE_ID, MODEL_FILE_NAME)
            st.success("모델 다운로드 완료!")
        except Exception as e:
            st.error(f"모델 다운로드 중 오류 발생: {e}")
            return None
    try:
        model = joblib.load(MODEL_FILE_NAME)
        return model
    except FileNotFoundError:
        st.error(f"모델 파일 '{MODEL_FILE_NAME}'을 찾을 수 없습니다. 다운로드 실패 여부를 확인하세요.")
        return None
    except Exception as e:
        st.error(f"모델 로드 실패: {e}")
        return None

model = load_and_cache_model()

# --- 3. Streamlit 앱 UI 및 상태 관리 ---
st.set_page_config(layout="wide", page_title="모바일 센서 예측 데모")
st.title("📱 센서 데이터 수집 + 실시간 예측")
st.markdown("---")

if "is_collecting" not in st.session_state:
    st.session_state.is_collecting = False
if "sensor_data" not in st.session_state:
    st.session_state.sensor_data = pd.DataFrame(columns=["acc_x", "acc_y", "acc_z", "gyro_alpha", "gyro_beta", "gyro_gamma"])
if "current_prediction" not in st.session_state:
    st.session_state.current_prediction = "데이터 수집을 시작하세요."
if "data_received" not in st.session_state:
    st.session_state.data_received = False

# --- 4. 자바스크립트 코드 (센서 리스너 및 버튼 UI) ---
js_code = f"""
    <button id="toggle-btn" style="background-color: {'#e53935' if st.session_state.is_collecting else '#43a047'}; color: white; border: none; padding: 10px 20px; font-size: 16px; border-radius: 5px; cursor: pointer; transition: background-color 0.3s;">
        {'⏹ 중지' if st.session_state.is_collecting else '▶️ 시작'}
    </button>
    <p id="status-text" style="margin-top: 10px; font-size: 18px;">{'센서 수집 중...' if st.session_state.is_collecting else '버튼을 눌러 시작하세요.'}</p>
    <script>
    let isCollecting = {str(st.session_state.is_collecting).lower()};
    let dataBuffer = [];
    let devicemotionListener = null;
    let sendDataInterval = null;
    const btn = document.getElementById('toggle-btn');
    const statusText = document.getElementById('status-text');

    async function requestPermission() {{
        if (typeof DeviceMotionEvent !== 'undefined' && typeof DeviceMotionEvent.requestPermission === 'function') {{
            try {{
                const res = await DeviceMotionEvent.requestPermission();
                return res === 'granted';
            }} catch (e) {{
                return false;
            }}
        }}
        return true;
    }}

    function startListening() {{
        if (devicemotionListener) return;
        devicemotionListener = e => {{
            const acc = e.accelerationIncludingGravity || {{}};
            const rot = e.rotationRate || {{}};
            dataBuffer.push({{
                acc_x: acc.x || 0,
                acc_y: acc.y || 0,
                acc_z: acc.z || 0,
                gyro_alpha: rot.alpha || 0,
                gyro_beta: rot.beta || 0,
                gyro_gamma: rot.gamma || 0
            }});
        }};
        window.addEventListener('devicemotion', devicemotionListener);
        
        sendDataInterval = setInterval(() => {{
            if (dataBuffer.length >= 20) {{
                const payload = JSON.stringify(dataBuffer);
                window.parent.postMessage({{type:"streamlit:setComponentValue", value: payload}}, "*");
                dataBuffer = [];
            }}
        }}, 1000);
    }}

    function stopListening() {{
        if (!devicemotionListener) return;
        window.removeEventListener('devicemotion', devicemotionListener);
        devicemotionListener = null;
        clearInterval(sendDataInterval);
        sendDataInterval = null;
    }}

    btn.onclick = async () => {{
        if (isCollecting) {{
            stopListening();
            window.parent.postMessage({{type:"streamlit:setComponentValue", value: "stop"}}, "*");
        }} else {{
            const permitted = await requestPermission();
            if (!permitted) {{
                alert("센서 권한이 거부되었습니다.");
                return;
            }}
            startListening();
            window.parent.postMessage({{type:"streamlit:setComponentValue", value: "start"}}, "*");
        }}
    }};
    </script>
"""

sensor_data_from_js = components.html(js_code, height=200, key="sensor_component")

# --- 5. Python 쪽 데이터 수신 및 예측 처리 ---
if sensor_data_from_js == "start":
    if not st.session_state.is_collecting:
        st.session_state.is_collecting = True
        st.session_state.current_prediction = "센서 수집 시작됨. 움직여 주세요!"
        st.experimental_rerun()
elif sensor_data_from_js == "stop":
    if st.session_state.is_collecting:
        st.session_state.is_collecting = False
        st.session_state.current_prediction = "센서 수집 중지됨."
        st.experimental_rerun()
elif isinstance(sensor_data_from_js, str):
    if sensor_data_from_js not in ("start", "stop", None):
        try:
            new_data = pd.DataFrame(json.loads(sensor_data_from_js))
            st.session_state.sensor_data = pd.concat([st.session_state.sensor_data, new_data], ignore_index=True)
            st.session_state.sensor_data = st.session_state.sensor_data.tail(PREDICTION_WINDOW_SIZE)
            st.session_state.data_received = True
        except Exception as e:
            st.warning(f"데이터 파싱 오류: {e}")

if st.session_state.data_received:
    if st.session_state.is_collecting and len(st.session_state.sensor_data) >= PREDICTION_WINDOW_SIZE:
        if model:
            try:
                mean_features = st.session_state.sensor_data.mean().values
                std_features = st.session_state.sensor_data.std().fillna(0).values
                features = np.concatenate([mean_features, std_features]).reshape(1, -1)
                
                prediction = model.predict(features)[0]
                st.session_state.current_prediction = LABELS.get(prediction, '알 수 없음')
            except Exception as e:
                st.error(f"예측 중 오류 발생: {e}")
        else:
            st.error("모델이 로드되지 않아 예측을 할 수 없습니다.")
    
    st.session_state.data_received = False
    st.experimental_rerun()

# --- 6. 데이터 및 예측 결과 출력 ---
st.markdown("### **실시간 예측 결과**")
st.info(f"**현재 상태:** {st.session_state.current_prediction}")
st.info(f"수집된 데이터 포인트: {len(st.session_state.sensor_data)} / {PREDICTION_WINDOW_SIZE}")

st.markdown("---")
st.subheader("📊 최근 센서 데이터 일부")
if not st.session_state.sensor_data.empty:
    st.dataframe(st.session_state.sensor_data.tail(5))
else:
    st.write("수집된 데이터가 없습니다.")
