import streamlit as st
import joblib
import pandas as pd
import streamlit.components.v1 as components

# 모델 파일 이름
model_file_name = 'gms_activity_model.pkl'

# 모델 불러오기
try:
    model = joblib.load(model_file_name)
    st.success(f"'{model_file_name}' 모델을 성공적으로 불러왔습니다.")
except FileNotFoundError:
    st.error(f"오류: '{model_file_name}' 파일을 찾을 수 없습니다. 파일을 업로드했는지 확인해주세요.")
    model = None

st.title('GMS: 친환경 습관 추적 앱 (데모)')
st.write("---")

# 앱의 메인 로직
if model:
    st.write("모델이 성공적으로 로드되었습니다. 이제 실시간 센서 데이터를 처리할 준비가 되었습니다.")
    st.write("아래 '센서 데이터 가져오기' 버튼을 누르고 스마트폰을 움직여 보세요.")

    # 센서 데이터 수집을 위한 자바스크립트 코드
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
    
    # 웹 페이지에 자바스크립트 코드 삽입
    components.html(js_code, height=0)

    # 센서 데이터를 담을 DataFrame 초기화
    if 'sensor_data' not in st.session_state:
        st.session_state.sensor_data = pd.DataFrame(columns=['acc_x', 'acc_y', 'acc_z', 'gyro_x', 'gyro_y', 'gyro_z'])

    st.subheader("수신된 센서 데이터")
    data_placeholder = st.empty()

    # Streamlit에서 자바스크립트로부터 메시지 수신
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        # 이전에 받은 데이터 처리
        new_data = pd.DataFrame([msg['data']])
        st.session_state.sensor_data = pd.concat([st.session_state.sensor_data, new_data], ignore_index=True)
        
        # 최신 50개 데이터만 표시
        data_placeholder.dataframe(st.session_state.sensor_data.tail(50))

    if st.button("센서 데이터 가져오기"):
        st.write("스마트폰으로 이 페이지를 열고 움직여 보세요!")
        st.session_state.messages = []
        st.session_state.sensor_data = pd.DataFrame(columns=['acc_x', 'acc_y', 'acc_z', 'gyro_x', 'gyro_y', 'gyro_z'])

        # 스크립트 실행
        # 이 부분이 실제 데이터 수신을 위한 메시지 리스너를 활성화합니다.
        components.html("""
        <script>
            window.parent.postMessage({
                'type': 'TO_STREAMLIT',
                'command': 'start_sensors'
            }, '*');
        </script>
        """, height=0)