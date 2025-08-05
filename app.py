import streamlit as st
import pandas as pd
import joblib
import os
import requests
import json

# -------------------------------
# 모델 다운로드 및 로드
# -------------------------------
MODEL_FILE_NAME = 'gms_activity_model.pkl'
GOOGLE_DRIVE_LINK = "https://drive.google.com/file/d/1pjbLZLcSc56chOuVEOlogZWFesUTYMOo/view?usp=drive_link"

@st.cache_data
def download_model(url):
    file_id = url.split('/')[-2]
    download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    response = requests.get(download_url, stream=True)
    if response.status_code == 200:
        with open(MODEL_FILE_NAME, 'wb') as f:
            f.write(response.content)
        return MODEL_FILE_NAME
    return None

if not os.path.exists(MODEL_FILE_NAME):
    download_model(GOOGLE_DRIVE_LINK)

model = joblib.load(MODEL_FILE_NAME) if os.path.exists(MODEL_FILE_NAME) else None
labels = {0: '앉아 있기', 1: '서기', 2: '걷기', 3: '자전거 타기', 4: '버스 타기', 5: '자동차 운전'}

# -------------------------------
# 세션 상태 초기화
# -------------------------------
if 'sensor_data' not in st.session_state:
    st.session_state.sensor_data = pd.DataFrame(columns=['acc_x','acc_y','acc_z','gyro_x','gyro_y','gyro_z'])
if 'last_prediction' not in st.session_state:
    st.session_state.last_prediction = "대기 중"

# -------------------------------
# 쿼리 파라미터를 통한 데이터 수신
# -------------------------------
params = st.experimental_get_query_params()
if "sensor_data" in params:
    try:
        raw = params["sensor_data"][0]
        df = pd.DataFrame(json.loads(raw))
        st.session_state.sensor_data = df
        st.experimental_rerun()
    except Exception as e:
        st.error(f"센서 데이터 파싱 실패: {e}")

# -------------------------------
# UI 구성
# -------------------------------
st.title("GMS: 친환경 습관 추적 앱 (데모)")
st.header(f"현재 활동: {st.session_state.last_prediction}")
st.write("모바일 기기에서 아래 버튼을 누르면 센서 데이터가 수집됩니다. 5초간 스마트폰을 움직여 보세요.")

# -------------------------------
# JavaScript 삽입: 센서 수집 및 전송
# -------------------------------
st.components.v1.html("""
<button onclick="startSensor()">센서 수집 시작</button>
<script>
let collected = [];

function startSensor() {
  if (typeof DeviceMotionEvent.requestPermission === 'function') {
    DeviceMotionEvent.requestPermission().then(state => {
      if (state === 'granted') {
        window.addEventListener('devicemotion', handleMotion, true);
        setTimeout(sendData, 5000);
      } else {
        alert("센서 권한이 거부되었습니다.");
      }
    }).catch(err => alert("권한 요청 실패: " + err));
  } else {
    window.addEventListener('devicemotion', handleMotion, true);
    setTimeout(sendData, 5000);
  }
}

function handleMotion(event) {
  collected.push({
    acc_x: event.acceleration.x || 0,
    acc_y: event.acceleration.y || 0,
    acc_z: event.acceleration.z || 0,
    gyro_x: event.rotationRate.alpha || 0,
    gyro_y: event.rotationRate.beta || 0,
    gyro_z: event.rotationRate.gamma || 0
  });
}

function sendData() {
  const params = new URLSearchParams();
  params.set("sensor_data", JSON.stringify(collected));
  window.parent.location.href = window.parent.location.pathname + "?" + params.toString();
}
</script>
""", height=200)

# -------------------------------
# 예측
# -------------------------------
if model and not st.session_state.sensor_data.empty:
    df = st.session_state.sensor_data
    if df.shape[0] >= 50:
        try:
            prediction = model.predict(df)
            final_prediction = pd.Series(prediction).mode()[0]
            st.session_state.last_prediction = labels.get(final_prediction, "알 수 없음")
            st.success(f"예측 결과: {st.session_state.last_prediction}")
        except Exception as e:
            st.warning(f"예측 실패: {e}")
    else:
        st.info("예측을 위해 최소 50개의 데이터 포인트가 필요합니다.")

# -------------------------------
# 데이터 정보 출력
# -------------------------------
st.write(f"수집된 데이터 포인트 수: {st.session_state.sensor_data.shape[0]}")
