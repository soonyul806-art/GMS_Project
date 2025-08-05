import streamlit as st
import joblib
import pandas as pd
import requests
import os
from st_mobile_sensors import mobile_sensors

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
    st.write("스마트폰으로 이 페이지를 열고 '센서 시작' 버튼을 누른 후, 움직여 보세요!")

    # st-mobile-sensors 컴포넌트를 사용해 데이터 수신
    sensor_data_json = mobile_sensors(key="mobile_sensors")

    if sensor_data_json:
        # 가속도계 및 자이로스코프 데이터 추출
        acc_x = sensor_data_json.get('acceleration', {}).get('x', None)
        acc_y = sensor_data_json.get('acceleration', {}).get('y', None)
        acc_z = sensor_data_json.get('acceleration', {}).get('z', None)
        gyro_x = sensor_data_json.get('rotationRate', {}).get('alpha', None)
        gyro_y = sensor_data_json.get('rotationRate', {}).get('beta', None)
        gyro_z = sensor_data_json.get('rotationRate', {}).get('gamma', None)

        if all(x is not None for x in [acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z]):
            new_data = pd.DataFrame([{'acc_x': acc_x, 'acc_y': acc_y, 'acc_z': acc_z,
                                      'gyro_x': gyro_x, 'gyro_y': gyro_y, 'gyro_z': gyro_z}])
            
            # 세션 상태에 데이터 추가
            st.session_state.sensor_data = pd.concat([st.session_state.sensor_data, new_data], ignore_index=True)
            
            # 화면 업데이트를 위해 st.rerun()을 호출
            st.rerun()

    PREDICTION_WINDOW_SIZE = 50
    if st.session_state.sensor_data.shape[0] >= PREDICTION_WINDOW_SIZE:
        df_for_prediction = st.session_state.sensor_data.tail(PREDICTION_WINDOW_SIZE)
        
        try:
            prediction = model.predict(df_for_prediction)
            final_prediction = pd.Series(prediction).mode()[0]
            st.session_state.last_prediction = labels.get(final_prediction, "알 수 없음")
        except ValueError as e:
            st.warning(f"예측 오류 발생: {e}")
    
else:
    st.write("모델 로딩에 실패했습니다. 파일을 다시 확인해 주세요.")
