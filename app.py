import streamlit as st
import streamlit.components.v1 as components
import json

st.set_page_config(page_title="센서 수집기", layout="centered")

st.title("📱 스마트폰 센서 수집기")

# iframe으로 자바스크립트 컴포넌트 삽입
components.html("""
    <iframe id="sensor-frame" src="/sensor_component.html" width="0" height="0" style="display: none;"></iframe>
    <script>
      const iframe = document.getElementById("sensor-frame");
      const channel = new BroadcastChannel("sensor_channel");

      window.addEventListener("message", (event) => {
        if (event.data && event.data.type === "sensor_data") {
          const data = event.data.payload;
          channel.postMessage(JSON.stringify(data));
        }
      });

      function sendMessageToIframe(msg) {
        iframe.contentWindow.postMessage(msg, "*");
      }

      window.sendPermissionRequest = () => sendMessageToIframe("request_permission");
      window.startCollection = () => sendMessageToIframe("start_collection");
    </script>
""", height=0)

# 권한 요청 버튼
if st.button("📲 센서 권한 요청"):
    st.info("브라우저에 센서 사용 권한을 요청했습니다.")
    components.html("<script>window.sendPermissionRequest()</script>", height=0)

# 센서 수집 버튼
if st.button("▶️ 센서 수집 시작"):
    st.success("센서 데이터 수집을 시작했습니다. 약 5초간 측정 후 자동 종료됩니다.")
    components.html("<script>window.startCollection()</script>", height=0)

# 수집된 센서 데이터를 수신
sensor_data = st.session_state.get("sensor_data", None)

# 데이터 수신을 위한 채널
sensor_data_placeholder = st.empty()

from streamlit_javascript import st_javascript

received_json = st_javascript(
    code="""
    new Promise((resolve) => {
      const channel = new BroadcastChannel("sensor_channel");
      channel.onmessage = (event) => {
        resolve(event.data);
      };
    });
    """
)

# 수신 후 파싱
if received_json:
    try:
        parsed = json.loads(received_json)
        st.session_state["sensor_data"] = parsed
        st.success("✅ 센서 데이터 수신 완료!")
        st.json(parsed)
    except Exception as e:
        st.error(f"데이터 파싱 오류: {e}")
