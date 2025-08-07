from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict
from model_service import predict_activity_from_data

app = FastAPI()

class SensorData(BaseModel):
    data: List[Dict[str, float]]

@app.post("/predict")
async def predict_endpoint(sensor_data: SensorData):
    try:
        prediction_text = predict_activity_from_data(sensor_data.data)
        return {"prediction": prediction_text, "status": "success"}
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"예측 중 서버 오류 발생: {e}")
