import os
import requests  # 用於發送 POST 請求到 Google
from fastapi import FastAPI, HTTPException, Depends, status, Request
from pydantic import BaseModel
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

# --- 1. 初始化 App ---
app = FastAPI()

# --- 2. 設定環境變數 ---
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

# --- 3. 定義資料模型 (Data Models) ---
class TokenRequest(BaseModel):
    id_token: str

# --- 4. 模擬缺失的輔助函式 (通常從其他檔案 import) ---
# 假設這些函式定義在你的工具類中
def create_access_token(data: dict):
    # 這裡應該是你的 JWT 簽發邏輯
    return "mock_access_token_for_" + data.get("sub")

async def get_current_user_email(request: Request):
    # 這裡應該是驗證 JWT 並回傳 email 的邏輯
    return "user@example.com"

# --- 5. 功能函式 ---
def verify_google_id_token(token: str):
    try:
        idinfo = id_token.verify_oauth2_token(
            token, google_requests.Request(), GOOGLE_CLIENT_ID
        )
        return idinfo
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無效的 Google Token"
        )

def exchange_code_for_tokens(code: str, redirect_uri: str) -> dict:
    payload = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    # 使用標準 requests 庫
    response = requests.post(GOOGLE_TOKEN_URL, data=payload)
    
    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"無法換取 tokens: {response.json().get('error_description', '未知錯誤')}"
        )  
    return response.json()

# --- 6. 路由 (Endpoints) ---

@app.post("/auth/google", summary="[架構B] 用 ID Token 換取 JWT")
async def google_auth(request: TokenRequest):
    user_info = verify_google_id_token(request.id_token)
    user_email = user_info.get("email")
    
    if not user_email:
        raise HTTPException(status_code=400, detail="Google 帳號未提供 Email")
    
    # 簽發自家的 Access Token
    access_token = create_access_token(data={"sub": user_email})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "name": user_info.get("name"),
            "email": user_email,
            "picture": user_info.get("picture")
        }
    }

@app.get("/users/me", summary="取得當前使用者資訊")
async def read_users_me(current_user: str = Depends(get_current_user_email)):
    return {
        "msg": "成功通過 JWT 驗證",
        "user_email": current_user
    }

@app.get("/")
def root():
    return {"message": "Hello FastAPI OAuth Demo"}