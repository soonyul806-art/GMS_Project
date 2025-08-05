import streamlit as st
import joblib
import pandas as pd
import requests
import streamlit.components.v1 as components
import os
import numpy as np
import time

# Google 드라이브 링크
GOOGLE_DRIVE_LINK = "https://drive.google.com/file/d/1pjbLZLcSc56chOuVEOlogZWFesUTYMOo/view?usp=drive_link"
MODEL_FILE_NAME = 'gms_activity_model.pkl'

# 모델 다운로드 함수
@st.cache_data
def download_model(url):
    st.info("모델 파일을 다운로드 중...")
    try:
        file_id = url.split('/')[-2]
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        
        response = requests.get(download_url, stream=True)
        if response.status_code == 200:
            with open(MODEL_FILE_NAME, 'wb') as f:
                f.write(response.content)
            st.success("모델 파일 다운로드 완료!")
            return MODEL_FILE_NAME
        else:
            st.error(f"모델 다운로드 실패: HTTP {response.status_code}")
            return None
    except Exception as e:
        st.error(f"모델 다운로드 중 오류 발생: {e}")
        return None

# 모델 불러오기
model = None
if not os.path.exists(MODEL_FILE_NAME):
    downloaded_file = download_model(GOOGLE_DRIVE_LINK)
    if downloaded_file:
        model = joblib.load(downloaded_file)
else:
    model = joblib.load(MODEL_FILE_NAME)

labels = {0: '앉아 있기', 1: '서기', 2: '걷기', 3: '자전거 타기', 4: '버스 타기', 5: '자동차 운전'}

if 'last_prediction' not in st.session_state:
    st.session_state.last_prediction = "데이터를 수집하는 중..."
if 'sensor_data' not in st.session_state:
    st.session_state.sensor_data = pd.DataFrame(columns=['acc_x', 'acc_y', 'acc_z', 'gyro_x', 'gyro_y', 'gyro_z'])

st.title('GMS: 친환경 습관 추적 앱 (데모)')
st.write("---")

if model:
    st.success("모델이 성공적으로 로드되었습니다.")
    
    st.header(f"현재 활동: {st.session_state.last_prediction}")
    
    data_points_info = st.empty()
    data_points_info.write(f"현재 수집된 데이터 포인트: **{st.session_state.sensor_data.shape[0]} / 50**")
    st.write("스마트폰으로 이 페이지를 열고 '센서 권한 요청 및 시작' 버튼을 누른 후, 움직여 보세요!")

    # 앱 실행 시점에 이벤트 리스너를 한 번만 등록
    components.html("""
    <script>
    function requestAndStartSensors() {
        if (typeof DeviceMotionEvent.requestPermission === 'function') {
            DeviceMotionEvent.requestPermission()
                .then(permissionState => {
                    if (permissionState === 'granted') {
                        alert('센서 접근이 허용되었습니다. 이제 움직여보세요!');
                    } else {
                        alert('센서 접근이 거부되었습니다.');
                    }
                })
                .catch(error => {
                    console.error('권한 요청 중 오류 발생:', error);
                    alert('권한 요청 중 오류가 발생했습니다.');
                });
        } else {
            alert('이 기기는 센서 권한 요청이 필요하지 않습니다. 이제 움직여보세요!');
        }
    }
    
    window.addEventListener('devicemotion', function(event) {
        window.parent.postMessage({
            'type': 'FROM_STREAMLIT',
            'data': {
                'acc_x': event.acceleration.x, 
                'acc_y': event.acceleration.y, 
                'acc_z': event.acceleration.z,
                'gyro_x': event.rotationRate.alpha, 
                'gyro_y': event.rotationRate.beta, 
                'gyro_z': event.rotationRate.gamma
            }
        }, '*');
    }, false);
    </script>
    """, height=0)

    if st.button("센서 권한 요청 및 시작"):
        components.html("""<script>requestAndStartSensors();</script>""", height=0)
        
    # 메시지를 수신하면 세션 상태에 저장 및 처리
    if st.session_state.get('messages'):
        for msg in st.session_state.messages:
            new_data = pd.DataFrame([msg['data']])
            st.session_state.sensor_data = pd.concat([st.session_state.sensor_data, new_data], ignore_index=True)
        
        st.session_state.messages = []

        PREDICTION_WINDOW_SIZE = 50
        if st.session_state.sensor_data.shape[0] >= PREDICTION_WINDOW_SIZE:
            df_for_prediction = st.session_state.sensor_data.tail(PREDICTION_WINDOW_SIZE)
            
            try:
                prediction = model.predict(df_for_prediction)
                final_prediction = pd.Series(prediction).mode()[0]
                st.session_state.last_prediction = labels.get(final_prediction, "알 수 없음")
                # 예측이 업데이트되면 화면을 다시 그립니다.
                st.rerun()
            except ValueError as e:
                st.warning(f"예측 오류 발생: {e}")
        
else:
    st.write("모델 로딩에 실패했습니다. 파일을 다시 확인해 주세요.")
