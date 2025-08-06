import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="센서 수집 앱", layout="centered")

st.title("📱 모바일 센서 데이터 수집")
st.write("아래 버튼을 눌러 센서 데이터를 수집하고 Streamlit으로 전달합니다.")

# 수집 시작 버튼
start_collection = st.button("센서 수집 시작")

# 센서 데이터 표시용 공간
sensor_data_placeholder = st.empty()

# HTML + JS 삽입
components.html(f"""
<!DOCTYPE html>
<html>
  <head>
    <meta charset="UTF-8" />
    <script>
      let watching = false;

      function startSensorCollection() {{
        if (!window.DeviceMotionEvent) {{
          window.parent.postMessage({{ type: 'sensorData', data: 'DeviceMotionEvent not supported' }}, '*');
          return;
        }}

        window.addEventListener('devicemotion', function(event) {{
          if (!watching) return;

          const acc = event.accelerationIncludingGravity;
          const data = {{
            x: acc.x?.toFixed(2),
            y: acc.y?.toFixed(2),
            z: acc.z?.toFixed(2),
            timestamp: Date.now()
          }};

          window.parent.postMessage({{ type: 'sensorData', data }}, '*');
        }}, true);

        watching = true;
      }}

      window.addEventListener("message", function(event) {{
        if (event.data === "start") {{
          startSensorCollection();
        }}
      }});
    </script>
  </head>
  <body>
    <p>이 창은 센서 수집을 위한 임베디드 콘텐츠입니다.</p>
  </body>
</html>
""", height=200)

# JS로 메시지를 보냄 (센서 시작 신호)
if start_collection:
    st.write("📡 센서 수집을 시작합니다. 휴대폰을 움직여보세요.")
    # JS로 메시지 전송
    st.components.v1.html(f"""
        <script>
            window.parent.postMessage("start", "*");
        </script>
    """, height=0)

# 센서 데이터 수신 JavaScript
# (Streamlit 내부적으로 브라우저와 JS가 메시지를 주고받도록 함)
st.markdown("""
<script>
    const streamlitReceiver = (event) => {
        if (event.data?.type === 'sensorData') {
            const data = event.data.data;
            const json = typeof data === 'string' ? data : JSON.stringify(data);
            const textarea = window.parent.document.querySelector('textarea[data-testid="stTextArea"]');
            if (textarea) {
                textarea.value = json;
                textarea.dispatchEvent(new Event("input", {{ bubbles: true }}));
            }
        }
    };
    window.addEventListener("message", streamlitReceiver);
</script>
""", unsafe_allow_html=True)

# 실제 센서 데이터를 표시할 위치
sensor_data = st.text_area("📊 센서 데이터", height=100)
