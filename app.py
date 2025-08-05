import streamlit as st
import joblib
import pandas as pd
import requests
import streamlit.components.v1 as components
import os

# Google 드라이브 링크를 여기에 붙여넣기
GOOGLE_DRIVE_LINK = "YOUR_GOOGLE_DRIVE_LINK_HERE" 
MODEL_FILE_NAME = 'gms_activity_model.pkl'

# 모델 다운로드 함수
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

st.title('GMS: 친환경 습관 추적 앱 (데모)')
st.write("---")

if model:
    st.success(f"'{MODEL_FILE_NAME}' 모델을 성공적으로 불러왔습니다.")
    st.write("아래 '센서 데이터 가져오기' 버튼을 누르고 스마트폰을 움직여 보세요.")

    # ... (이전 코드의 센서 데이터 수집 자바스크립트 부분)
    js_code = """
    <script>
    if (window.DeviceMotionEvent) {
        window.addEventListener('devicemotion', function(event) {
            const acc_x = event.acceleration.x;
            const acc_y = event.acceleration.y;
            const acc_z = event.acceleration.z;
            const gyro_x = event.rotationRate.alpha;
            const gyro_y = event.rotationRate.beta;
            const gyro_z = event.rotationRate.gamma;

            window.parent.postMessage({
                'type': 'FROM_STREAMLIT',
                'data': {
                    'acc_x': acc_x, 'acc_y': acc_y, 'acc_z': acc_z,
                    'gyro_x': gyro_x, 'gyro_y': gyro_y, 'gyro_z': gyro_z
                }
            }, '*');
        }, false);
    }
    </script>
    """
    
    components.html(js_code, height=0)

    if 'sensor_data' not in st.session_state:
        st.session_state.sensor_data = pd.DataFrame(columns=['acc_x', 'acc_y', 'acc_z', 'gyro_x', 'gyro_y', 'gyro_z'])

    st.subheader("수신된 센서 데이터")
    data_placeholder = st.empty()

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        new_data = pd.DataFrame([msg['data']])
        st.session_state.sensor_data = pd.concat([st.session_state.sensor_data, new_data], ignore_index=True)
        data_placeholder.dataframe(st.session_state.sensor_data.tail(50))

    if st.button("센서 데이터 가져오기"):
        st.write("스마트폰으로 이 페이지를 열고 움직여 보세요!")
        st.session_state.messages = []
        st.session_state.sensor_data = pd.DataFrame(columns=['acc_x', 'acc_y', 'acc_z', 'gyro_x', 'gyro_y', 'gyro_z'])

        components.html("""
        <script>
            window.parent.postMessage({
                'type': 'TO_STREAMLIT',
                'command': 'start_sensors'
            }, '*');
        </script>
        """, height=0)
else:
    st.write("모델 로딩에 실패했습니다. 파일을 다시 확인해 주세요.")
