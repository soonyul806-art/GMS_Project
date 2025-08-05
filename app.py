import streamlit as st
import joblib
import pandas as pd
import requests
import streamlit.components.v1 as components
import os

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
    st.session_state.last_prediction = "아직 데이터가 없습니다."

st.title('GMS: 친환경 습관 추적 앱 (데모)')
st.write("---")

if model:
    st.success("모델이 성공적으로 로드되었습니다.")
    st.header(f"현재 활동: {st.session_state.last_prediction}")

    # 자바스크립트 코드 (센서 권한 요청 및 데이터 수집)
    js_code = """
    <script>
    window.onload = function() {
        const urlParams = new URLSearchParams(window.location.search);
        const getSensors = urlParams.get('getSensors');
        if (getSensors === 'true') {
            if (typeof DeviceMotionEvent.requestPermission === 'function') {
                DeviceMotionEvent.requestPermission()
                    .then(permissionState => {
                        if (permissionState === 'granted') {
                            window.parent.postMessage({ type: 'FROM_STREAMLIT', data: 'permission_granted' }, '*');
                        } else {
                            window.parent.postMessage({ type: 'FROM_STREAMLIT', data: 'permission_denied' }, '*');
                        }
                    })
                    .catch(console.error);
            } else {
                 window.parent.postMessage({ type: 'FROM_STREAMLIT', data: 'permission_not_required' }, '*');
            }
        }
    };
    
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
    """
    components.html(js_code, height=0)

    if st.button("센서 데이터 가져오기 시작"):
        # 버튼을 누르면 URL에 파라미터를 추가하여 페이지를 새로고침
        st.experimental_rerun()
    
    st.session_state.messages = []
    
    PREDICTION_WINDOW_SIZE = 50
    if st.session_state.get('sensor_data') and st.session_state.sensor_data.shape[0] >= PREDICTION_WINDOW_SIZE:
        df_for_prediction = st.session_state.sensor_data.tail(PREDICTION_WINDOW_SIZE)
        prediction = model.predict(df_for_prediction)
        
        final_prediction = pd.Series(prediction).mode()[0]
        st.session_state.last_prediction = labels.get(final_prediction, "알 수 없음")
        
    st.write("스마트폰으로 이 페이지를 열고 움직여 보세요!")
else:
    st.write("모델 로딩에 실패했습니다. 파일을 다시 확인해 주세요.")
