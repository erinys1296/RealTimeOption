import dash
from dash import dcc, html, Input, Output
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from datetime import time


import requests
from bs4 import BeautifulSoup

import threading
import queue
import os

# Airtable 上傳數據示例
import requests
import json
import pandas as pd

from time import sleep
import time as time2


# 全局變數：用於存儲第三個子圖的數據
third_subplot_data_queue = queue.Queue(maxsize=1)
third_subplot_data_ready = False  # 標記數據是否準備好


# 定義顏色常量

increasing_color = 'rgb(255, 0, 0)'
decreasing_color = 'rgb(0, 0, 245)'

red_color = 'rgba(255, 0, 0, 0.5)'
green_color = 'rgba(30, 144, 255,0.5)'

no_color = 'rgba(256, 256, 256,0)'

blue_color = 'rgb(30, 144, 255)'
red_color_full = 'rgb(255, 0, 0)'

orange_color = 'rgb(245, 152, 59)'
green_color_full = 'rgb(52, 186, 7)'

gray_color = 'rgb(188, 194, 192)'
black_color = 'rgb(0, 0, 0)'

####################################
# Airtable API 配置
# Cost & Limit Data
####################################


# Airtable API 配置
AIRTABLE_API_KEY = 'pat80TwGtrg94dFcY.dbd384b7220aaf48a81edd5331fdfb4e7a8832d1c710c08ea27be735a4bfbcb3'  # 替換為您的 Airtable API 密鑰


#https://api.airtable.com/v0/app1EGjcRgUZj2doS/limit_data
# Airtable API 端點


# 設置 API 請求頭
headers = {
    'Authorization': f'Bearer {AIRTABLE_API_KEY}',
    'Content-Type': 'application/json',
    'forHTTPHeaderField': "Authorization"
}

# 示例：查詢 Airtable 數據
def query_airtable_records(AIRTABLE_ENDPOINT,formula=None, max_records=1000, view=None):
    """
    從 Airtable 查詢記錄
    
    Args:
        formula (str, optional): 篩選公式
        max_records (int, optional): 最大返回記錄數
        view (str, optional): 視圖名稱
    
    Returns:
        pandas.DataFrame: 查詢結果
    """
    params = {}
    
    if formula:
        params['filterByFormula'] = formula
    
    if max_records:
        params['maxRecords'] = max_records
    
    if view:
        params['view'] = view
    
    # try:
    response = requests.get(
        AIRTABLE_ENDPOINT,
        headers=headers,
        params=params
    )
    
    if response.status_code == 200:
        data = response.json()
        records = data.get('records', [])

        # 這裡可能需要檢查 records 的結構
        if not isinstance(records, list):
            print(f"警告: API返回的records不是列表類型，而是 {type(records)}")
            records = []
        
        # 提取字段數據並將其轉換為 DataFrame
        extracted_records = []
        for record in records:
            if isinstance(record, dict):  # 確保 record 是字典
                record_data = record.get('fields', {})
                record_data['airtable_id'] = record.get('id')  # 保存 Airtable 記錄 ID
                extracted_records.append(record_data)
            else:
                print(f"警告: record 不是字典類型，而是 {type(record)}")
        
        df = pd.DataFrame(extracted_records)
        return df
    else:
        print(f"查詢失敗: {response.status_code} - {response.text}")
        return pd.DataFrame()
    # except Exception as e:
    #     print(f"查詢時發生異常: {str(e)}")
    #     return pd.DataFrame()
    
def test():


    AIRTABLE_BASE_ID = 'app1EGjcRgUZj2doS'  # 替換為您的 Airtable 基地 ID
    COST_TABLE_NAME = 'cost_data'  # 替換為您的表格名稱
    LIMIT_TABLE_NAME = 'limit_data'  # 替換為您的表格名稱
    COST_AIRTABLE_ENDPOINT = f'https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{COST_TABLE_NAME}'
    LIMIT_AIRTABLE_ENDPOINT = f'https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{LIMIT_TABLE_NAME}'
    cost_df = query_airtable_records(COST_AIRTABLE_ENDPOINT, formula=None, max_records=1000, view=None)
    limit_df = query_airtable_records(LIMIT_AIRTABLE_ENDPOINT, formula=None, max_records=1000, view=None)
    

    if not cost_df.empty and len(cost_df.columns) == 3:
        cost_df.columns = ['Dateonly', 'Cost', 'airtable_id']
    else:
        print(f"警告: cost_df 為空或欄位數不是 3 (實際: {len(cost_df.columns) if not cost_df.empty else 0})")
        # 創建一個具有正確結構的空 DataFrame
        cost_df = pd.DataFrame(columns=['Dateonly', 'Cost', 'airtable_id'])
    
    if not limit_df.empty and len(limit_df.columns) == 6:
        limit_df.columns = ['商品名稱', 'Dateonly', '身份別', '上極限', '下極限', 'airtable_id']
    else:
        print(f"警告: limit_df 為空或欄位數不是 6 (實際: {len(limit_df.columns) if not limit_df.empty else 0})")
        # 創建一個具有正確結構的空 DataFrame
        limit_df = pd.DataFrame(columns=['商品名稱', 'Dateonly', '身份別', '上極限', '下極限', 'airtable_id'])
    
    print(limit_df)

test()