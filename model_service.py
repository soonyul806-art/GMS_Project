import joblib
import pandas as pd
import numpy as np
import requests
import os

GOOGLE_DRIVE_FILE_ID = "1pjbLZLcSc56chOuVEOlogZWFesUTYMOo"
MODEL_FILE_NAME = "model/gms_activity_model.pkl"
LABELS = {0: '앉아 있기', 1: '서기', 2: '걷기', 3: '자전거 타기', 4: '버스 타기', 5: '자동차 운전'}
PREDICTION_WINDOW_SIZE = 50

def download_file_from_google_drive(file_id, destination):
    URL = "https://docs.google.com/uc?export=download"
    session = requests.Session()
    response = session.get(URL, params = { 'id' : file_id }, stream=True)
    token = get_confirm_token(response)
    if token:
        params = { 'id' : file_id, 'confirm' : token }
        response = session.get(URL, params = params, stream=True)
    os.makedirs(os.path.dirname(destination), exist_ok=True)
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

def load_model():
    if not os.path.exists(MODEL_FILE_NAME):
        print("모델 파일이 없어 다운로드를 시도합니다...")
        try:
            download_file_from_google_drive(GOOGLE_DRIVE_FILE_ID, MODEL_FILE_NAME)
            print("모델 다운로드 완료!")
        except Exception as e:
            raise RuntimeError(f"모델 다운로드 중 오류 발생: {e}")
    try:
        model = joblib.load(MODEL_FILE_NAME)
        return model
    except FileNotFoundError:
        raise RuntimeError(f"모델 파일 '{MODEL_FILE_NAME}'을 찾을 수 없습니다. 다운로드 실패 여부를 확인하세요.")
    except Exception as e:
        raise RuntimeError(f"모델 로드 실패: {e}")

model = load_model()

def predict_activity_from_data(data: list[dict[str, float]]) -> str:
    if len(data) < PREDICTION_WINDOW_SIZE:
        raise ValueError(f"데이터 포인트가 부족합니다. 최소 {PREDICTION_WINDOW_SIZE}개가 필요합니다.")
    
    df = pd.DataFrame(data)
    
    mean_features = df.mean().values
    std_features = df.std().fillna(0).values
    features = np.concatenate([mean_features, std_features]).reshape(1, -1)
    
    try:
        prediction_label = model.predict(features)[0]
        prediction_text = LABELS.get(prediction_label, '알 수 없음')
        return prediction_text
    except Exception as e:
        raise RuntimeError(f"예측 중 오류 발생: {e}")
