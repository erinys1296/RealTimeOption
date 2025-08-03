# 股票分析儀表板部署指南

## 本地測試

1. 安裝依賴：
```bash
pip install -r requirements.txt
```

2. 運行應用：
```bash
python app.py
```

3. 在瀏覽器中打開 `http://localhost:8050`

## 部署到 Google Cloud Platform (App Engine)

### 前置準備

1. 安裝 Google Cloud SDK：
   - 下載並安裝：https://cloud.google.com/sdk/docs/install
   - 或使用 Homebrew (macOS)：`brew install google-cloud-sdk`

2. 登錄 Google Cloud：
```bash
gcloud auth login
```

3. 創建新項目或選擇現有項目：
```bash
# 創建新項目
gcloud projects create YOUR-PROJECT-ID

# 選擇項目
gcloud config set project YOUR-PROJECT-ID
```

4. 啟用 App Engine API：
```bash
gcloud services enable appengine.googleapis.com
```

5. 初始化 App Engine：
```bash
gcloud app create --region=asia-east1
```

### 部署步驟

1. 確保在 dashboard_app 目錄中：
```bash
cd /Users/erinyschung/Documents/教學/客製化教學/選擇權爬蟲/dashboard_app
```

2. 部署應用：
```bash
gcloud app deploy
```

3. 查看應用：
```bash
gcloud app browse
```

## 使用 Docker 部署

### 本地 Docker 測試

1. 構建 Docker 映像：
```bash
docker build -t dashboard-app .
```

2. 運行容器：
```bash
docker run -p 8080:8080 dashboard-app
```

3. 在瀏覽器中打開 `http://localhost:8080`

### 部署到 Google Cloud Run

1. 啟用 Cloud Run API：
```bash
gcloud services enable run.googleapis.com
```

2. 構建並推送到 Container Registry：
```bash
# 構建映像
gcloud builds submit --tag gcr.io/real-time-dash-1/dashboard-app

# 部署到 Cloud Run
gcloud run deploy dashboard-app \
  --image gcr.io/real-time-dash-1/dashboard-app \
  --platform managed \
  --region asia-east1 \
  --allow-unauthenticated
```

## 部署到其他平台

### Heroku

1. 安裝 Heroku CLI
2. 創建 Procfile：
```
web: gunicorn app:server --bind 0.0.0.0:$PORT
```

3. 部署：
```bash
heroku create your-app-name
git push heroku main
```

### Railway

1. 連接到 Railway: https://railway.app
2. 連接 GitHub 儲存庫
3. 添加環境變數 `PORT=8080`
4. 自動部署

## 注意事項

- 確保所有依賴都在 requirements.txt 中
- 檢查防火牆設置允許相應端口
- 監控應用性能和資源使用
- 設置適當的環境變數用於生產環境

## 疑難排解

1. 如果遇到端口問題，檢查環境變數 PORT 設置
2. 如果依賴安裝失敗，嘗試更新 pip：`pip install --upgrade pip`
3. 查看日誌：`gcloud app logs tail -s default`
