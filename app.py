import streamlit as st
import pandas as pd
import numpy as np
import joblib
import os
import requests
import time

# 모델 파일 다운로드
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

# 세션 상태 초기화
if 'sensor_data' not in st.session_state:
    st.session_state.sensor_data = pd.DataFrame(columns=['acc_x', 'acc_y', 'acc_z', 'gyro_x', 'gyro_y', 'gyro_z'])

if 'last_prediction' not in st.session_state:
    st.session_state.last_prediction = "데이터를 수집하는 중..."

st.title("GMS: 친환경 습관 추적 앱 (데모)")
st.write("---")

st.header(f"현재 활동: {st.session_state.last_prediction}")
st.write("스마트폰에서 아래 버튼을 눌러 센서 데이터를 수집하세요.")

# JavaScript로 데이터를 수집하고 hidden input을 통해 Python에 전달
st.components.v1.html("""
<div>
  <button onclick="startSensor()">센서 권한 요청 및 수집 시작</button>
</div>
<form id="sensorForm" method="post">
  <input type="hidden" name="sensor_data" id="sensor_data_input" />
</form>

<script>
let collected = [];

function startSensor() {
  if (typeof DeviceMotionEvent.requestPermission === 'function') {
    DeviceMotionEvent.requestPermission().then(state => {
      if (state === 'granted') {
        window.addEventListener('devicemotion', handleMotion, true);
        alert("센서 수집 시작! 5초간 데이터를 수집합니다.");
        setTimeout(sendData, 5000);
      } else {
        alert("센서 권한이 거부되었습니다.");
      }
    });
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
  let input = document.getElementById("sensor_data_input");
  input.value = JSON.stringify(collected);
  document.getElementById("sensorForm").submit();
}
</script>
""", height=200)

# POST 요청으로 전달된 센서 데이터 처리
if 'sensor_data' in st.query_params:
    try:
        import json
        raw_data = st.query_params.get("sensor_data")
        data = pd.DataFrame(json.loads(raw_data))
        st.session_state.sensor_data = data
    except Exception as e:
        st.error(f"데이터 처리 오류: {e}")

# 예측
if model and not st.session_state.sensor_data.empty:
    df = st.session_state.sensor_data
    if df.shape[0] >= 30:
        try:
            prediction = model.predict(df)
            final_prediction = pd.Series(prediction).mode()[0]
            st.session_state.last_prediction = labels.get(final_prediction, "알 수 없음")
            st.success(f"예측 결과: {st.session_state.last_prediction}")
        except Exception as e:
            st.warning(f"예측 오류: {e}")
    else:
        st.info("예측을 위해 더 많은 데이터가 필요합니다.")

# 현재 데이터 수 확인
st.write(f"현재 수집된 데이터 포인트: {st.session_state.sensor_data.shape[0]}개")
