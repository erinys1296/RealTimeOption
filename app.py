import dash
from dash import dcc, html, Input, Output
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from datetime import time

import shioaji as sj
import APIKEY
import futuredata

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

# 創建 Dash 應用
app = dash.Dash(__name__)

# 全局變數：用於存儲第三個子圖的數據
third_subplot_data_queue = queue.Queue(maxsize=1)
third_subplot_data_ready = False  # 標記數據是否準備好

# 登入 Shioaji API
SIM_MODE = True

api = sj.Shioaji(simulation=SIM_MODE)
api.login(
    api_key=APIKEY.get_Key(SIM_MODE),
    secret_key=APIKEY.get_Secret(SIM_MODE)
)

TXlist = [ i for i in str(api.Contracts.Options)[1:-1].split(", ") if i[:2] == 'TX']

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
    

####################################
# 定義函數:
####################################

def resample_df(original_df, frequency):
    df_resample = original_df.resample(frequency)
    df = pd.DataFrame()
    df['Open']   = df_resample['Open'].first()
    df['Low']    = df_resample['Low'].min()
    df['Volume'] = df_resample['Volume'].sum()
    df['Close']  = df_resample['Close'].last()
    df['High']   = df_resample['High'].max()
    return df

def get_future_raw_data(start, end):
    deadline = api.Contracts.Futures.TXF.TXFR1
    k_bars = api.kbars(api.Contracts.Futures['TXF'][deadline.symbol], start=start, end=end)
    df = pd.DataFrame({**k_bars})
    df.ts = pd.to_datetime(df.ts)
    df.sort_values(["ts"], ascending=True, inplace=True)
    df.set_index('ts', inplace=True)
    return resample_df(df, 'T')

def get_ticks_df(symbol):
    ticks = api.ticks(
        contract=api.Contracts.Stocks[str(symbol)], 
        #抓取當天日期
        #若當天為假日，則抓取前一天
        date = datetime.now().strftime('%Y-%m-%d') if datetime.now().weekday() < 5 else (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
        query_type=sj.constant.TicksQueryType.RangeTime,
        time_start="09:00:00",
        time_end="10:40:01"
    )
    dfticktemp = pd.DataFrame({**ticks})
    dfticktemp.ts = pd.to_datetime(dfticktemp.ts)
    dfticktemp['symbol'] = symbol  # 添加代號欄位
    return dfticktemp


# 背景任務：處理第三個子圖需要的數據
def process_third_subplot_data():
    """在背景執行耗時的數據抓取，完成後將結果放入隊列"""
    global third_subplot_data_ready
    
    while True:
        try:
            print("開始處理第三子圖的數據：抓取期權合約資料...")
            start_time = time2.time()
            
            # 您提供的數據抓取代碼
            try:
                df = pd.DataFrame()
                # 假設 TXlist 和 api 已在其他地方定義，或在這裡導入
                # 例如：from your_api_module import api, TXlist
                
                for txo_contract in list(api.Contracts.Options[TXlist[0]]):
                    # 抓取昨天的資料
                    yesterday = datetime.strftime(datetime.now() - timedelta(days=1), '%Y-%m-%d')
                    tick_data = api.ticks(txo_contract, yesterday)
                    dftemp = pd.DataFrame({**tick_data})
                    dftemp['Contract'] = txo_contract.symbol[-6:-1]
                    dftemp['PC'] = txo_contract.symbol[-1:]
                    dftemp.ts = pd.to_datetime(dftemp.ts)
                    
                    df = pd.concat([df, dftemp], ignore_index=True)
                    
                    # 抓取今天的資料
                    today = datetime.strftime(datetime.now(), '%Y-%m-%d')
                    tick_data = api.ticks(txo_contract, today)
                    dftemp = pd.DataFrame({**tick_data})
                    dftemp['Contract'] = txo_contract.symbol[-6:-1]
                    dftemp['PC'] = txo_contract.symbol[-1:]
                    dftemp.ts = pd.to_datetime(dftemp.ts)
                    
                    df = pd.concat([df, dftemp], ignore_index=True)
                
                # 數據後處理（如有需要）
                if not df.empty:
                    # 這裡可以添加數據處理邏輯，如計算指標、整理數據等
                    # 例如按時間排序
                    putcallsum = []
                    #starttime = datetime(datetime.now().year, datetime.now().month , datetime.now().day, datetime.now().hour -5, 00)
                    starttime = pd.to_datetime(df.ts.dt.date.max()) - timedelta(hours=5)  # 從最新日期減去14小時
                    for mini in range(60*14):
                        minutesdelta = timedelta(minutes=mini)
                        cuttime = starttime + minutesdelta
                        dftemp = df[df['ts'] < cuttime]
                        # 先依照時間戳記排序資料
                        dftemp_sorted = dftemp.sort_values('ts')

                        # 取得每個 Contract 和 PC 組合的最後一筆交易
                        last_trades = dftemp_sorted.groupby(['Contract', 'PC']).last().reset_index()[['Contract', 'PC', 'close']]

                        # 將資料轉為寬表格(wide format)，讓每個 Contract 有 P 和 C 的價格欄位
                        pivot_df = last_trades.pivot(index='Contract', columns='PC', values='close').reset_index()
                        pivot_df.columns.name = None

                        # 計算 P + C 的總和
                        pivot_df['P+C'] = np.abs(pivot_df['P'] + pivot_df['C'])
                        pivot_df['P-C'] = np.abs(pivot_df['P'] - pivot_df['C'])

                        # 排序找出差異最小的 Contract
                        result = pivot_df.sort_values('P-C')


                        putcallsum.append([cuttime,result.iloc[0]['Contract'],result.iloc[0]['P+C'],result.iloc[0]['C'],result.iloc[0]['P']])

                    #將 putcallsum 轉換為 DataFrame 以便繪圖
                    putcallsum_df = pd.DataFrame(putcallsum, columns=['Time','Contract', 'PutCallSum', 'CallPrice', 'PutPrice'])
                    
                    # 準備結果數據
                    result = {
                        'data': putcallsum_df,
                        'metadata': {
                            'calculated_at': datetime.now(),
                            'records_count': len(putcallsum_df),
                            'contracts_count': len(set(putcallsum_df['Contract']))
                        }
                    }
                    
                    # 清空並更新隊列
                    if not third_subplot_data_queue.empty():
                        try:
                            third_subplot_data_queue.get_nowait()
                        except queue.Empty:
                            pass
                    
                    third_subplot_data_queue.put(result)
                    third_subplot_data_ready = True
                    
                    end_time = time2.time()
                    print(f"第三子圖數據處理完成: {len(df)} 筆記錄，耗時 {end_time - start_time:.2f} 秒")
                else:
                    print("第三子圖數據處理完成，但沒有取得資料")
                    
            except Exception as e:
                print(f"抓取期權合約資料時出錯: {e}")
                import traceback
                traceback.print_exc()
            
            # 等待一段時間再次更新數據（例如每小時更新一次）
            sleep(3600)  # 3600秒 = 1小時
            
        except Exception as e:
            print(f"處理第三子圖數據主循環出錯: {e}")
            import traceback
            traceback.print_exc()
            sleep(300)  # 出錯時等待5分鐘後重試


####################################
# 爬蟲台灣前150大權值股
####################################

# 目標網址
url = "https://www.taifex.com.tw/cht/9/futuresQADetail"

# 設定 Headers 模擬瀏覽器訪問
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# 發送請求
response = requests.get(url, headers=headers)
response.encoding = "utf-8"

# 檢查請求是否成功
if response.status_code == 200:
    soup = BeautifulSoup(response.text, "html.parser")
    
    # 找到目標表格
    table = soup.find("table", {"class": "table_c"})  # 可能需要根據實際 HTML 調整
    
    if table:
        headers = [th.text.strip() for th in table.find_all("th")]
        data = []
        
        for row in table.find_all("tr")[1:]:  # 跳過標題行
            cols = row.find_all("td")
            data.append([col.text.strip() for col in cols][:4])
        
        # 轉換成 DataFrame
        df150 = pd.DataFrame(data[:150], columns=['排行', '代號','證券名稱', '市值佔 大盤比重'])
        
    else:
        print("未找到表格，請檢查 HTML 結構是否變更。")
else:
    print(f"請求失敗，狀態碼: {response.status_code}")

df150data = []
for symbol in df150['代號']:
    try:
        df = get_ticks_df(symbol)
        df150data.append(df)
    except Exception as e:
        print(f"獲取 {symbol} 的數據時出錯: {e}")

ticks_df_150 = pd.concat(df150data, ignore_index=True)
#only for testing
ticks_df_150['ts'] = ticks_df_150['ts'] + pd.Timedelta(hours=18)

ticks_df_150['date'] = (ticks_df_150.ts + pd.Timedelta(minutes=1)).dt.strftime('%Y-%m-%d %H:%M:00')
bid_ask_df_150 = ticks_df_150.groupby(['date','symbol','tick_type']).agg({ 'volume': 'sum'}).reset_index().pivot(index=['date','symbol'], columns='tick_type', values='volume').fillna(0)
bid_ask_df_150 = bid_ask_df_150.reset_index()
bid_ask_df_150['gap_150sum'] = bid_ask_df_150[1] - bid_ask_df_150[2]
bid_ask_df_150 = bid_ask_df_150.groupby('date').agg({'gap_150sum':'sum'})

####################################
# 載入 DataFrame:
####################################
Final15Tdata = futuredata.get_future_T_data(15,3)
Final60Tdata = futuredata.get_future_T_data(60,10)
Final01Tdata = futuredata.get_future_T_data(1,5)


# 昨天日期
yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
# 30天前日期
thirty_days_ago = (datetime.now() - timedelta(days=35)).strftime("%Y-%m-%d")
kbars = api.kbars(
    contract=api.Contracts.Futures.TXF.TXFR1,
    start=thirty_days_ago, 
    end=yesterday, 
)
dfam = pd.DataFrame({**kbars})
dfam.ts = pd.to_datetime(dfam.ts)
dfam['date'] = dfam.ts.dt.date
dfam = dfam[dfam.ts > pd.to_datetime(np.sort(dfam.date.unique())[-5]) + timedelta(hours=8)]
# 
dfam['time'] = dfam.ts.dt.time
# time_cal 為 time - 5小時
dfam['time_cal'] = dfam.ts.apply(lambda x: ((x - timedelta(minutes=5*60+1))).time())
#對 amount 進行平均, 對 ts 進行取最小
amount_mean_time = dfam.groupby('time_cal').agg({'Amount':'mean', 'time':'min'}).reset_index()
amount_mean_time['cumsum'] = amount_mean_time.Amount.cumsum()
print(amount_mean_time)





# 添加 CSS 樣式和 JavaScript
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            body {
                background-color: #0a0a0a !important;
                color: #ffffff !important;
                margin: 0;
                padding: 0;
            }
            
            /* 分隔器樣式 */
            .divider {
                background-color: #555 !important;
                transition: background-color 0.2s;
                position: relative;
                z-index: 1000;
                cursor: ew-resize !important;
                flex-shrink: 0;
            }
            
            .divider:hover {
                background-color: #00ff88 !important;
                box-shadow: 0 0 5px rgba(0, 255, 136, 0.5) !important;
            }
            
            .divider.dragging {
                background-color: #00cc66 !important;
                box-shadow: 0 0 10px rgba(0, 255, 136, 0.8) !important;
            }
            
            /* 確保分隔器可見 */
            #divider1, #divider2 {
                width: 8px !important;
                background-color: #555 !important;
                cursor: ew-resize !important;
                user-select: none !important;
                -webkit-user-select: none !important;
                -moz-user-select: none !important;
                -ms-user-select: none !important;
            }
            
            /* 主容器樣式 */
            #main-container {
                display: flex !important;
                align-items: stretch !important;
            }
            
            /* 防止選取文字 */
            .no-select {
                -webkit-user-select: none;
                -moz-user-select: none;
                -ms-user-select: none;
                user-select: none;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
        
        <script>
            let isDragging = false;
            let currentDivider = null;
            let startX = 0;
            let startWidths = {};
            
            function initDragResize() {
                console.log('Initializing drag resize...');
                const dividers = document.querySelectorAll('.divider');
                const leftPanel = document.getElementById('left-panel');
                const middlePanel = document.getElementById('middle-panel');
                const rightPanel = document.getElementById('right-panel');
                const container = document.getElementById('main-container');
                
                console.log('Found elements:', {
                    dividers: dividers.length,
                    leftPanel: !!leftPanel,
                    middlePanel: !!middlePanel,
                    rightPanel: !!rightPanel,
                    container: !!container
                });
                
                if (!leftPanel || !middlePanel || !rightPanel || !container || dividers.length === 0) {
                    console.log('Missing elements, retrying in 200ms...');
                    setTimeout(initDragResize, 200);
                    return;
                }
                
                // 移除之前的事件監聽器
                dividers.forEach(divider => {
                    const newDivider = divider.cloneNode(true);
                    divider.parentNode.replaceChild(newDivider, divider);
                });
                
                // 重新獲取分隔器
                const newDividers = document.querySelectorAll('.divider');
                
                newDividers.forEach((divider, index) => {
                    console.log(`Setting up divider ${index}`);
                    
                    divider.addEventListener('mousedown', function(e) {
                        console.log(`Mousedown on divider ${index}`);
                        isDragging = true;
                        currentDivider = index;
                        startX = e.clientX;
                        
                        // 記錄初始寬度
                        const containerWidth = container.offsetWidth;
                        startWidths = {
                            left: (leftPanel.offsetWidth / containerWidth) * 100,
                            middle: (middlePanel.offsetWidth / containerWidth) * 100,
                            right: (rightPanel.offsetWidth / containerWidth) * 100
                        };
                        
                        console.log('Start widths:', startWidths);
                        
                        divider.classList.add('dragging');
                        document.body.classList.add('no-select');
                        e.preventDefault();
                        e.stopPropagation();
                    });
                    
                    // 添加懸停效果
                    divider.addEventListener('mouseenter', function() {
                        if (!isDragging) {
                            divider.style.backgroundColor = '#00ff88';
                            divider.style.boxShadow = '0 0 5px rgba(0, 255, 136, 0.5)';
                        }
                    });
                    
                    divider.addEventListener('mouseleave', function() {
                        if (!isDragging) {
                            divider.style.backgroundColor = '#555';
                            divider.style.boxShadow = 'none';
                        }
                    });
                });
                
                console.log('Drag resize initialized successfully');
            }
            
            // 全局事件監聽器
            document.addEventListener('mousemove', function(e) {
                if (!isDragging) return;
                
                const container = document.getElementById('main-container');
                const leftPanel = document.getElementById('left-panel');
                const middlePanel = document.getElementById('middle-panel');
                const rightPanel = document.getElementById('right-panel');
                
                if (!container || !leftPanel || !middlePanel || !rightPanel) return;
                
                const containerWidth = container.offsetWidth;
                const deltaX = e.clientX - startX;
                const deltaPercent = (deltaX / containerWidth) * 100;
                
                let leftWidth = startWidths.left;
                let middleWidth = startWidths.middle;
                let rightWidth = startWidths.right;
                
                if (currentDivider === 0) {
                    // 拖拽第一個分隔器（左欄和中欄之間）
                    leftWidth += deltaPercent;
                    middleWidth -= deltaPercent;
                    
                    // 限制最小和最大寬度
                    if (leftWidth < 15) {
                        const diff = 15 - leftWidth;
                        leftWidth = 15;
                        middleWidth = startWidths.middle - deltaPercent + diff;
                    }
                    if (middleWidth < 10) {
                        const diff = 10 - middleWidth;
                        middleWidth = 10;
                        leftWidth = startWidths.left + deltaPercent - diff;
                    }
                    if (leftWidth > 70) {
                        const diff = leftWidth - 70;
                        leftWidth = 70;
                        middleWidth = startWidths.middle - deltaPercent + diff;
                    }
                } else if (currentDivider === 1) {
                    // 拖拽第二個分隔器（中欄和右欄之間）
                    middleWidth += deltaPercent;
                    rightWidth -= deltaPercent;
                    
                    // 限制最小和最大寬度
                    if (middleWidth < 10) {
                        const diff = 10 - middleWidth;
                        middleWidth = 10;
                        rightWidth = startWidths.right - deltaPercent + diff;
                    }
                    if (rightWidth < 15) {
                        const diff = 15 - rightWidth;
                        rightWidth = 15;
                        middleWidth = startWidths.middle + deltaPercent - diff;
                    }
                    if (rightWidth > 70) {
                        const diff = rightWidth - 70;
                        rightWidth = 70;
                        middleWidth = startWidths.middle + deltaPercent - diff;
                    }
                }
                
                // 應用新寬度
                leftPanel.style.width = leftWidth + '%';
                middlePanel.style.width = middleWidth + '%';
                rightPanel.style.width = rightWidth + '%';
                
                // 觸發圖表重新調整大小
                setTimeout(() => {
                    window.dispatchEvent(new Event('resize'));
                }, 50);
            });
            
            document.addEventListener('mouseup', function(e) {
                if (isDragging) {
                    console.log('Mouse up, stopping drag');
                    isDragging = false;
                    currentDivider = null;
                    
                    document.querySelectorAll('.divider').forEach(d => {
                        d.classList.remove('dragging');
                        d.style.backgroundColor = '#555';
                        d.style.boxShadow = 'none';
                    });
                    document.body.classList.remove('no-select');
                }
            });
            
            // 初始化函數
            function startDragSystem() {
                console.log('Starting drag system...');
                
                // 等待 DOM 完全載入
                if (document.readyState === 'loading') {
                    document.addEventListener('DOMContentLoaded', function() {
                        setTimeout(initDragResize, 500);
                    });
                } else {
                    setTimeout(initDragResize, 500);
                }
                
                // 監聽 Dash 圖表載入
                const observer = new MutationObserver(function(mutations) {
                    let shouldReinit = false;
                    
                    mutations.forEach(function(mutation) {
                        if (mutation.addedNodes.length > 0) {
                            for (let node of mutation.addedNodes) {
                                if (node.nodeType === 1) {
                                    if (node.querySelector && (
                                        node.querySelector('.plotly-graph-div') ||
                                        node.querySelector('#left-panel') ||
                                        node.querySelector('#middle-panel') ||
                                        node.querySelector('#right-panel')
                                    )) {
                                        shouldReinit = true;
                                        break;
                                    }
                                }
                            }
                        }
                    });
                    
                    if (shouldReinit) {
                        console.log('DOM mutation detected, reinitializing...');
                        setTimeout(initDragResize, 300);
                    }
                });
                
                observer.observe(document.body, {
                    childList: true,
                    subtree: true
                });
                
                // 定期檢查和重新初始化
                setInterval(() => {
                    const dividers = document.querySelectorAll('.divider');
                    if (dividers.length === 0) {
                        console.log('Dividers missing, reinitializing...');
                        initDragResize();
                    }
                }, 2000);
            }
            
            // 啟動拖拽系統
            startDragSystem();
        </script>
    </body>
</html>
'''

# 生成假資料
def generate_fake_data():
    dates = pd.date_range(start=datetime.now() - timedelta(days=30), end=datetime.now(), freq='1H')
    n = len(dates)
    
    # 主圖資料 (價格資料)
    price_data = {
        'Date': dates,
        'Open': np.random.randn(n).cumsum() + 100,
        'High': np.random.randn(n).cumsum() + 105,
        'Low': np.random.randn(n).cumsum() + 95,
        'Close': np.random.randn(n).cumsum() + 100,
        'Volume': np.random.randint(1000, 10000, n)
    }
    
    # 附圖資料
    sub_data = {
        'RSI': np.random.uniform(20, 80, n),
        'MACD': np.random.randn(n),
        'BollUpper': np.random.randn(n).cumsum() + 110,
        'BollLower': np.random.randn(n).cumsum() + 90,
        'MA5': np.random.randn(n).cumsum() + 100,
        'MA20': np.random.randn(n).cumsum() + 100,
        'Stoch': np.random.uniform(0, 100, n),
        'OBV': np.random.randn(n).cumsum() * 1000
    }
    
    df = pd.DataFrame({**price_data, **sub_data})
    return df

# 生成柱狀圖資料
def generate_bar_data():
    categories = ['Call 18000', 'Call 18100', 'Call 18200', 'Call 18300', 'Call 18400',
                  'Put 17600', 'Put 17700', 'Put 17800', 'Put 17900', 'Put 18000']
    values = np.random.randint(-5000, 5000, len(categories))
    colors = ['red' if v > 0 else 'green' for v in values]
    
    return pd.DataFrame({
        'Category': categories,
        'Value': values,
        'Color': colors
    })

# 應用布局
app.layout = html.Div([
    # 標題區域
    html.Div([
        html.H1("選擇權即時籌碼", style={
            'textAlign': 'center', 
            'marginBottom': 10,
            'color': '#ffffff',
            'textShadow': '0 0 10px rgba(0,255,136,0.3)'
        })
    ], style={
        'backgroundColor': '#1a1a1a',
        'padding': '3px',
        'borderBottom': '2px solid #333'
    }),
    
    # 主要內容區域 - 使用可拖拽的分隔器
    html.Div([
        # 左側欄 - 主圖 + 2個附圖
        html.Div([
            # 添加 K 線頻率選擇控件
            html.Div([
                html.H3(id='left-chart-title', style={'display': 'inline-block', 'marginRight': '20px', 'color': '#ffffff'}),
                dcc.RadioItems(
                    id='kline-interval-selector',
                    options=[
                        {'label': '15分K', 'value': '15'},
                        {'label': '60分K', 'value': '60'}
                    ],
                    value='15',  # 默認選擇15分鐘
                    labelStyle={'display': 'inline-block', 'marginRight': '10px', 'color': '#ffffff'},
                    style={'display': 'inline-block', 'marginLeft': '20px'}
                )
            ], style={'padding': '10px', 'backgroundColor': '#1a1a1a', 'textAlign': 'left'}),
            dcc.Graph(id='left-charts', style={'height': '760px'})  # 減小高度以適應標題區域
        ], id='left-panel', style={
            'width': '40%', 
            'height': '820px',
            'backgroundColor': '#2a2a2a',
            'borderRadius': '8px',
            'border': '1px solid #444',
            'overflow': 'hidden'
        }),
        
        # 第一個分隔器
        html.Div(
            style={
                'width': '8px',
                'height': '820px',
                'backgroundColor': '#555',
                'cursor': 'ew-resize',
                'position': 'relative',
                'transition': 'background-color 0.2s'
            },
            id='divider1',
            className='divider'
        ),
        
        # 中間欄 - 分為上下兩部分，比例 7:3
        html.Div([
            # 上部分 (70%)
            html.Div([
                html.Div([
                    html.H3("冰火能量圖", style={
                        'color': '#ffffff', 
                        'margin': '10px',
                        'padding': '5px'
                    })
                ], style={
                    'backgroundColor': '#1a1a1a', 
                    'textAlign': 'left'
                }),
                dcc.Graph(id='middle-bar-chart', style={'height': '510px'})  # 70% 的 760px 約為 532px，減去標題高度
            ], style={
                'backgroundColor': '#2a2a2a',
                'borderRadius': '8px 8px 0 0',
                'border': '1px solid #444',
                'marginBottom': '5px',
                'height': '560px',  # 560px / 800px ≈ 0.7 (70%)
                'overflow': 'hidden'
            }),
            
            # 下部分 (30%)
            html.Div([
                html.Div([
                    html.H3("SC賣方價格", style={
                        'color': '#ffffff', 
                        'margin': '10px',
                        'padding': '5px'
                    })
                ], style={
                    'backgroundColor': '#1a1a1a', 
                    'textAlign': 'left'
                }),
                dcc.Graph(id='middle-bottom-chart', style={'height': '200px'})  # 30% 的 760px 約為 228px，減去標題高度
            ], style={
                'backgroundColor': '#2a2a2a',
                'borderRadius': '0 0 8px 8px',
                'border': '1px solid #444',
                'height': '240px',  # 240px / 800px = 0.3 (30%)
                'overflow': 'hidden'
            }),
        ], id='middle-panel', style={
            'width': '20%',
            'height': '820px',
            'display': 'flex',
            'flexDirection': 'column',
            'backgroundColor': '#0a0a0a',  # 背景設為主背景色，讓分隔更明顯
            'borderRadius': '8px',
            'overflow': 'hidden'
        }),
        
        # 第二個分隔器
        html.Div(
            style={
                'width': '8px',
                'height': '820px',
                'backgroundColor': '#555',
                'cursor': 'ew-resize',
                'position': 'relative',
                'transition': 'background-color 0.2s'
            },
            id='divider2',
            className='divider'
        ),
        
        # 右側欄 - 主圖 + 5個附圖
        html.Div([
            dcc.Graph(id='right-charts', style={'height': '800px'})
        ], id='right-panel', style={
            'width': '40%',
            'height': '820px',
            'backgroundColor': '#2a2a2a',
            'borderRadius': '8px',
            'border': '1px solid #444',
            'overflow': 'hidden'
        })
    ], id='main-container', style={
        'display': 'flex',
        'backgroundColor': '#0a0a0a',
        'padding': '10px',
        'gap': '0px'
    }),
    
    # 儲存面板寬度的隱藏 div
    html.Div(id='panel-widths', style={'display': 'none'}),
    
    # 自動更新組件
    dcc.Interval(
        id='interval-component',
        interval=60*1000,  # 每1分鐘更新一次
        n_intervals=0
    )
], style={
    'backgroundColor': '#0a0a0a',
    'minHeight': '100vh',
    'fontFamily': '"Segoe UI", Arial, sans-serif'
})

# 左側圖表回調
@app.callback(
    Output('left-charts', 'figure'),
    [Input('interval-component', 'n_intervals'),
     Input('kline-interval-selector', 'value')]
)
def update_left_charts(n, kline_interval):
    AIRTABLE_BASE_ID = 'app1EGjcRgUZj2doS'  # 替換為您的 Airtable 基地 ID
    COST_TABLE_NAME = 'cost_data'  # 替換為您的表格名稱
    LIMIT_TABLE_NAME = 'limit_data'  # 替換為您的表格名稱
    COST_AIRTABLE_ENDPOINT = f'https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{COST_TABLE_NAME}'
    LIMIT_AIRTABLE_ENDPOINT = f'https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{LIMIT_TABLE_NAME}'
    cost_df = query_airtable_records(COST_AIRTABLE_ENDPOINT, formula=None, max_records=1000, view=None)
    limit_df = query_airtable_records(LIMIT_AIRTABLE_ENDPOINT, formula=None, max_records=1000, view=None)
    #print(limit_df)
    # 檢查 DataFrame 是否為空，以及列數是否符合預期
    if not cost_df.empty and len(cost_df.columns) == 3:
        cost_df.columns = ['Dateonly', 'Cost', 'airtable_id']
        cost_df['Dateonly'] = pd.to_datetime(cost_df['Dateonly']).dt.date  # 確保 Dateonly 是日期格式
    else:
        print(f"警告: cost_df 為空或欄位數不是 3 (實際: {len(cost_df.columns) if not cost_df.empty else 0})")
        # 創建一個具有正確結構的空 DataFrame
        cost_df = pd.DataFrame(columns=['Dateonly', 'Cost', 'airtable_id'])
    
    if not limit_df.empty and len(limit_df.columns) == 6:
        limit_df.columns = ['商品名稱', 'Dateonly', '身份別', '上極限', '下極限', 'airtable_id']
        limit_df['Dateonly'] = pd.to_datetime(limit_df['Dateonly']).dt.date  # 確保 Dateonly 是日期格式
    else:
        print(f"警告: limit_df 為空或欄位數不是 6 (實際: {len(limit_df.columns) if not limit_df.empty else 0})")
        # 創建一個具有正確結構的空 DataFrame
        limit_df = pd.DataFrame(columns=['商品名稱', 'Dateonly', '身份別', '上極限', '下極限', 'airtable_id'])
    
    # 模擬不同頻率的數據
    if kline_interval == '15':
        # 15分鐘 K 線數據（假設原本的 generate_fake_data 返回的是 15 分鐘數據）
        title_prefix = "15分鐘"
        df = Final15Tdata
        # 15分鐘K線使用日期 時:分格式
        date_format = '%Y-%m-%d %H:%M'  # 15分鐘K線使用年月日 時:分格式
        
    else:
        # 60分鐘 K 線數據（這裡僅做簡單模擬，實際應用中需要獲取真實的 60 分鐘數據）
        title_prefix = "60分鐘"
        # 模擬 60 分鐘數據，實際應用中替換為真實的 60 分鐘數據獲取邏輯
        df = Final60Tdata
        date_format = '%Y-%m-%d %H:00'  # 60分鐘K線使用小時:00格式

    df.index = pd.to_datetime(df.index)
    print(df.index)
    
    
    
    df = df.sort_index(ascending=True)
    # 只取最後 num_points
    #df = df.iloc[-num_points:] if num_points < len(df) else df
    #print(df.index.values)
    #print(df.index[-60])
    df = df[df.index > df.index[-60]]
    
    #print(df.index[0])
    #df = df.reset_index()
    #df.index = df.index.strftime(("%Y-%m-%d %H:%M")))
    #print(df)
    df['Dateonly'] = (df.index - pd.Timedelta(hours=13)).date
    df['indexdate'] = df.index
    limit_df_per = limit_df[limit_df['身份別'] == '自營商']
    limit_df = limit_df[limit_df['身份別'] == '外資']
    limit_df.columns = ['商品名稱', 'Dateonly', '外資身份別', '外資上極限', '外資下極限', 'airtable_id']
    
    limit_df_per.columns = ['自營商商品名稱', 'Dateonly', '自營商身份別', '自營商上極限', '自營商下極限', 'airtable_id']
    
    df = df.merge(cost_df, on='Dateonly', how='left')
    df = df.merge(limit_df, on= 'Dateonly', how='left')
    df = df.merge(limit_df_per, on= 'Dateonly', how='left')
    #print(df.index)
    df.index = df.indexdate
    #print(df[['Dateonly', 'Cost', '外資上極限', '外資下極限', '自營商身份別', '自營商上極限']].head(5))
    
    
    today = datetime.now().strftime('%Y-%m-%d')
    deadline = api.Contracts.Futures.TXF.TXFR1
    ticks = api.ticks(
        contract=api.Contracts.Futures['TXF'][deadline.symbol], 
        date=today
    )
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    df_bs = pd.DataFrame({**ticks})
    df_bs.ts = pd.to_datetime(df_bs.ts)

    ticks2 = api.ticks(
        contract=api.Contracts.Futures['TXF'][deadline.symbol], 
        date=yesterday
    )

    # 轉換為DataFrame並處理時間戳
    df_bs2 = pd.DataFrame({**ticks2})
    df_bs2.ts = pd.to_datetime(df_bs2.ts)
    df_bs = pd.concat([df_bs,df_bs2], ignore_index=True)

    df_bs.sort_values(["ts"], ascending=True, inplace=True)
    df_bs = df_bs[df_bs['bid_price']>0]




    # 創建子圖：1個主圖 + 2個附圖
    fig_left = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        row_heights=[0.5, 0.25, 0.25],
        specs=[[{"secondary_y": True}]]*3,
        vertical_spacing=0.02
    )
    
    # 主圖 - K線圖
    # 1) 主圖
    fig_left.add_trace(
        go.Scatter(
            x=df.index,
            y=df['21MA'],
            connectgaps=True,  # 啟用間隙連接
            name='21MA'
        ),
        row=1, col=1, secondary_y= True
    )
    fig_left.add_trace(
        go.Scatter(
            x=df.index,
            y=df['Cost'],
            connectgaps=True,  # 啟用間隙連接
            name='Cost'
        ),
        row=1, col=1, secondary_y= True
    )
    # fig_left.add_trace(
    #     go.Scatter(
    #         x=df.index,
    #         y=df['外資上極限'],
    #         connectgaps=True,  # 啟用間隙連接
    #         name='外資上極限'
    #     ),
    #     row=1, col=1, secondary_y= True
    # )
    # fig_left.add_trace(
    #     go.Scatter(
    #         x=df.index,
    #         y=df['外資下極限'],
    #         connectgaps=True,  # 啟用間隙連接
    #         name='外資下極限'
    #     ),
    #     row=1, col=1, secondary_y= True
    # )
    # fig_left.add_trace(
    #     go.Scatter(
    #         x=df.index,
    #         y=df['自營商上極限'],
    #         connectgaps=True,  # 啟用間隙連接
    #         name='自營商上極限'
    #     ),
    #     row=1, col=1, secondary_y= True
    # )
    # fig_left.add_trace(
    #     go.Scatter(
    #         x=df.index,
    #         y=df['自營商下極限'],
    #         connectgaps=True,  # 啟用間隙連接
    #         name='自營商下極限'
    #     ),
    #     row=1, col=1, secondary_y= True
    # )

    fig_left.add_traces(go.Scatter(x=df.index, y = df['外資上極限'].values,
                                        line = dict(color='rgba(0,0,0,0)'),showlegend=False,name='外資上極限'),rows=[1], cols=[1], secondary_ys= [True])
                
    fig_left.add_traces(go.Scatter(x=df.index, y = df['自營商上極限'].values,
                                line = dict(color='rgba(0,0,0,0)'),
                                fill='tonexty', 
                                fillcolor = 'rgba(0,0,256,0.2)',showlegend=False,name='自營商上極限'
                                ),rows=[1], cols=[1], secondary_ys= [True])
    fig_left.add_traces(go.Scatter(x=df.index, y = df['外資下極限'].values,
                                        line = dict(color='rgba(0,0,0,0)'),showlegend=False,name='外資下極限'),rows=[1], cols=[1], secondary_ys= [True])

    fig_left.add_traces(go.Scatter(x=df.index, y = df['自營商下極限'].values,
                                line = dict(color='rgba(0,0,0,0)'),
                                fill='tonexty', 
                                fillcolor = 'rgba(256,0,0,0.2)',showlegend=False,name='自營商下極限'
                                ),rows=[1], cols=[1], secondary_ys= [True])



    ### K線圖製作 ###
    fig_left.add_trace(
        go.Candlestick(
            x=df[(df['all_kk'] == -1)&(df['Close'] >df['Open'] )].index,
            open=df[(df['all_kk'] == -1)&(df['Close'] >df['Open'] )]['Open'],
            high=df[(df['all_kk'] == -1)&(df['Close'] >df['Open'] )]['High'],
            low=df[(df['all_kk'] == -1)&(df['Close'] >df['Open'] )]['Low'],
            close=df[(df['all_kk'] == -1)&(df['Close'] >df['Open'] )]['Close'],
            increasing_line_color=decreasing_color,
            increasing_fillcolor=no_color, #fill_increasing_color(df.index>df.index[50])
            decreasing_line_color=decreasing_color,
            decreasing_fillcolor=no_color,#decreasing_color,
            line=dict(width=2),
            name='OHLC',showlegend=False
        )#,
        
        ,row=1, col=1, secondary_y= True
    )


    fig_left.add_trace(
        go.Candlestick(
            x=df[(df['all_kk'] == 1)&(df['Close'] >df['Open'] )].index,
            open=df[(df['all_kk'] == 1)&(df['Close'] >df['Open'] )]['Open'],
            high=df[(df['all_kk'] == 1)&(df['Close'] >df['Open'] )]['High'],
            low=df[(df['all_kk'] == 1)&(df['Close'] >df['Open'] )]['Low'],
            close=df[(df['all_kk'] == 1)&(df['Close'] >df['Open'] )]['Close'],
            increasing_line_color=increasing_color,
            increasing_fillcolor=no_color, #fill_increasing_color(df.index>df.index[50])
            decreasing_line_color=increasing_color,
            decreasing_fillcolor=no_color,#decreasing_color,
            line=dict(width=1),
            name='OHLC',showlegend=False
        )#,
        
        ,row=1, col=1, secondary_y= True
    )

    ### K線圖製作 ###
    fig_left.add_trace(
        go.Candlestick(
            x=df[(df['all_kk'] == -1)&(df['Close'] <df['Open'] )].index,
            open=df[(df['all_kk'] == -1)&(df['Close'] <df['Open'] )]['Open'],
            high=df[(df['all_kk'] == -1)&(df['Close'] <df['Open'] )]['High'],
            low=df[(df['all_kk'] == -1)&(df['Close'] <df['Open'] )]['Low'],
            close=df[(df['all_kk'] == -1)&(df['Close'] <df['Open'] )]['Close'],
            increasing_line_color=decreasing_color,
            increasing_fillcolor=decreasing_color, #fill_increasing_color(df.index>df.index[50])
            decreasing_line_color=decreasing_color,
            decreasing_fillcolor=decreasing_color,#decreasing_color,
            line=dict(width=1),
            name='OHLC',showlegend=False
        )#,
        
        ,row=1, col=1, secondary_y= True
    )


    fig_left.add_trace(
        go.Candlestick(
            x=df[(df['all_kk'] == 1)&(df['Close'] <df['Open'] )].index,
            open=df[(df['all_kk'] == 1)&(df['Close'] <df['Open'] )]['Open'],
            high=df[(df['all_kk'] == 1)&(df['Close'] <df['Open'] )]['High'],
            low=df[(df['all_kk'] == 1)&(df['Close'] <df['Open'] )]['Low'],
            close=df[(df['all_kk'] == 1)&(df['Close'] <df['Open'] )]['Close'],
            increasing_line_color=increasing_color,
            increasing_fillcolor=increasing_color, #fill_increasing_color(df.index>df.index[50])
            decreasing_line_color=increasing_color,
            decreasing_fillcolor=increasing_color,#decreasing_color,
            line=dict(width=1),
            name='OHLC',showlegend=False
        )#,
        
        ,row=1, col=1, secondary_y= True
    )
    
    fig_left.add_trace(
        go.Scatter(
            x=df.index,
            y=df['55MA'],
            connectgaps=True,  # 啟用間隙連接
            name='55MA'
        ),
        row=1, col=1, secondary_y= True
    )
    fig_left.add_trace(
        go.Scatter(
            x=df.index,
            y=df['upper_band'],
            connectgaps=True,  # 啟用間隙連接
            name='+2sigma'
        ),
        row=1, col=1, secondary_y= True
    )
    fig_left.add_trace(
        go.Scatter(
            x=df.index,
            y=df['lower_band'],
            connectgaps=True,  # 啟用間隙連接
            name='-2sigma'
        ),
        row=1, col=1, secondary_y= True
    )


    # Volume (第一 y 軸)
    volume_colors = [red_color if df['Close'][i] > df['Close'][i-1] else green_color for i in range(1,len(df['Close']))]
    volume_colors[0] = green_color
    volumes = df['Volume']  # 請確定 df 中有 'Volume' 欄位
    fig_left.add_trace(go.Bar(x=df.index, y=df['Volume'], name='Volume', marker=dict(color=volume_colors,line=dict(width=0))), row=1, col=1)


    # 附圖1 - RSI
    fig_left.add_trace(
        go.Scatter(
            x=df.index,
            y=len(df.index)*[2],
            mode='lines',
            name='RSI',
            line=dict(color='purple')
        ),
        row=2, col=1
    )
    
    # 添加RSI超買超賣線
    # fig_left.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
    # fig_left.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
    
    # 附圖2 - 成交量
    colors = ['red' if close >= open else 'green' 
              for close, open in zip(df['Close'], df['Open'])]

    fig_left.add_trace(
        go.Bar(
            x=df.index,
            y=len(df.index)*[2],
            name='成交量',
            marker_color=colors
        ),
        row=3, col=1
    )
    
    # 更新子圖標題樣式
    for annotation in fig_left['layout']['annotations']:
        annotation['font'] = dict(color='#ffffff', size=12)

    # 更新所有子圖的x軸設定 - 除了最後一個子圖外都隱藏x軸標籤
    for i in range(1, 3):  # 總共3個子圖，前2個隱藏x軸標籤
        fig_left.update_xaxes(
            showticklabels=False,
            gridcolor='#404040',
            color='#ffffff',
            row=i, col=1
        )
    
    # 最後一個子圖顯示x軸標籤
    fig_left.update_xaxes(
        showticklabels=True,
        gridcolor='#404040',
        color='#ffffff',
        row=3, col=1
    )

    # 更新X軸：參考fig_right的格式，跳過無數據的時間段
    fig_left.update_xaxes(
        tickformat=date_format,
        tickmode='array',
        tickvals=df.index,  # 只在有數據的時間點顯示刻度
        rangeslider_visible=False,
        showgrid=True,
        gridcolor='rgba(255,255,255,0.1)',
        row=1, col=1
    )

    fig_left.update_xaxes(
        tickformat=date_format,
        tickmode='array',
        tickvals=df.index,
        showgrid=True,
        gridcolor='rgba(255,255,255,0.1)',
        row=2, col=1
    )
    
    # 更新所有y軸樣式
    fig_left.update_yaxes(
        gridcolor='#404040',
        color='#ffffff'
    )

    fig_left.update_layout(
        
        xaxis_rangeslider_visible=False,
        height=760,  # 適配上方控件區域
        showlegend=False,  # 隱藏圖例
        paper_bgcolor='#1a1a1a',
        plot_bgcolor='#2a2a2a',
        font={'color': '#ffffff'},
        margin=dict(t=10, b=30, l=50, r=50),  # 減小上邊距，因為標題已移至控件區域
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        # 確保X軸設置是共享的，並且只在有數據的地方顯示
        xaxis=dict(
            rangebreaks=[
                #dict(bounds=["sat", "mon"]),  # 跳過週末
                dict(bounds=[6, 9], pattern="hour"),
                dict(bounds=[14, 15], pattern="hour"),  # 跳過非交易時間
            ] if kline_interval == '60' else [
                #dict(bounds=["sat", "mon"]),  # 跳過週末
                dict(bounds=[6, 8], pattern="hour"),
                dict(bounds=[14, 15], pattern="hour"),  # 跳過非交易時間
            ]  # 只有60分鐘K線才應用這些範圍中斷
        ),
        hovermode='x unified',
    )
    
    return fig_left

# 中間柱狀圖回調
@app.callback(
    Output('middle-bar-chart', 'figure'),
    Input('interval-component', 'n_intervals')
)
def update_middle_chart(n):
    # 創建包含三個子圖的圖表
    fig = make_subplots(
        rows=1, cols=3,
        column_widths=[0.25, 0.375, 0.375],  # 調整三欄的寬度比例
        specs=[[{"type": "xy"}, {"type": "xy"}, {"type": "xy"}]],
        horizontal_spacing=0.01  # 減小水平間距
    )
    
    # === 第一欄：線圖+柱狀圖 ===
    # 模擬數據
    x_vals = np.arange(10)
    line_vals = np.array([10, 12, 15, 14, 16, 18, 17, 20, 22, 25])
    bar_vals = np.array([0, 0, 0, 0, 0, 0, 0, 0, 0, 15])  # 最後一個值特別高

    # === 第一欄：垂直線段 + 橫向柱狀圖 ===
    strike_prices = [
        22600, 22550, 22500, 22450, 22400, 22350, 22300, 
        22250, 22200, 22150, 22100, 22050, 22000, 21950, 
        21900, 21850, 21800, 21750, 21700, 21650, 21600
    ]
    


    # 創建垂直線段數據
    line_x = [15] * len(strike_prices)  # 固定 x 位置
    line_y = strike_prices

    # 添加垂直線段 - 使用多個小的線段連接
    for i in range(len(strike_prices)-1):
        fig.add_shape(
            type="line",
            x0=line_x[i], y0=line_y[i],
            x1=line_x[i+1], y1=line_y[i+1],
            line=dict(color='red', width=2),
            row=1, col=1
        )
    
    # 添加柱狀圖（黃色突出顯示）
    fig.add_trace(
        go.Bar(
            x=x_vals, 
            y=bar_vals,
            orientation='h',  # 垂直方向
            marker_color=['yellow' if v > 0 else 'green' for v in bar_vals],
            name='柱圖',
            showlegend=False
        ),
        row=1, col=1
    )
    
    # === 第二欄：正負柱狀圖(Call) ===
    # 模擬選擇權數據
    strike_prices = [
        22600, 22550, 22500, 22450, 22400, 22350, 22300, 
        22250, 22200, 22150, 22100, 22050, 22000, 21950, 
        21900, 21850, 21800, 21750, 21700, 21650, 21600
    ]
    
    call_values = [
        -20, 15, -10, 40, -15, 10, -5,
        20, -30, -25, -150, -10, -140, -15,
        -60, 10, -120, -140, -180, 15, -200
    ]
    
    # 顏色映射：正值為綠色，負值為紅色
    call_colors = ['#00FF00' if v > 0 else '#FF0000' for v in call_values]
    
    # 添加標籤數據
    call_labels = [f"C {s}" for s in strike_prices]
    call_annotations = [f"{abs(v)}" for v in call_values]
    
    # 添加Call柱狀圖
    fig.add_trace(
        go.Bar(
            y=strike_prices,  # Y軸為價格
            x=call_values,    # X軸為數量
            orientation='h',  # 水平方向
            marker_color=call_colors,
            text=call_annotations,  # 數值標註
            textposition='auto',
            textfont=dict(
                color='yellow',
                size=9
            ),
            name='Call',
            showlegend=False
        ),
        row=1, col=2
    )
    
    # === 第三欄：正負柱狀圖(Put) ===
    put_values = [
        10, -20, 15, -10, 30, -25, 5,
        -15, 10, -5, -180, -15, -160, -25,
        -50, 15, -130, -150, -200, 20, -220
    ]
    
    # 顏色映射：正值為綠色，負值為紅色
    put_colors = ['#00FF00' if v > 0 else '#FF0000' for v in put_values]
    
    # 添加標籤數據
    put_labels = [f"P {s}" for s in strike_prices]
    put_annotations = [f"{abs(v)}" for v in put_values]
    
    # 添加Put柱狀圖
    fig.add_trace(
        go.Bar(
            y=strike_prices,  # Y軸為價格
            x=put_values,     # X軸為數量
            orientation='h',  # 水平方向
            marker_color=put_colors,
            text=put_annotations,  # 數值標註
            textposition='auto',
            textfont=dict(
                color='yellow',
                size=9
            ),
            name='Put',
            showlegend=False
        ),
        row=1, col=3
    )
    
    # === 更新布局 ===
    fig.update_layout(
        height=510,
        plot_bgcolor='black',
        paper_bgcolor='black',
        margin=dict(l=5, r=5, t=5, b=5),
        font=dict(color='white'),
        barmode='relative',  # 使用相對模式，不是堆疊模式
        bargap=0.15,        # 柱子之間的間距
    )
    
    # 更新第一欄的軸
    fig.update_xaxes(
        showgrid=False,
        showticklabels=False,
        row=1, col=1
    )
    
    fig.update_yaxes(
        showgrid=False,
        showticklabels=False,
        row=1, col=1
    )
    
    # 更新第二欄的軸
    fig.update_xaxes(
        showgrid=False,
        zeroline=True,
        zerolinecolor='white',
        zerolinewidth=1,
        showticklabels=False,
        row=1, col=2
    )
    
    fig.update_yaxes(
        showgrid=False,
        tickfont=dict(color='white', size=10),
        tickmode='array',
        tickvals=strike_prices,
        ticktext=call_labels,
        side='right', 
        row=1, col=2
    )
    
    # 更新第三欄的軸
    fig.update_xaxes(
        showgrid=False,
        zeroline=True,
        zerolinecolor='white',
        zerolinewidth=1,
        showticklabels=False,
        row=1, col=3
    )
    
    fig.update_yaxes(
        showgrid=False,
        tickfont=dict(color='white', size=10),
        tickmode='array',
        tickvals=strike_prices,
        ticktext=put_labels,
        side='right',  # 在右側顯示標籤
        row=1, col=3
    )
    
    # 添加中央縱線
    fig.add_shape(
        type="line",
        x0=0, y0=min(strike_prices)-50,
        x1=0, y1=max(strike_prices)+50,
        line=dict(color="white", width=1),
        row=1, col=2
    )
    
    fig.add_shape(
        type="line",
        x0=0, y0=min(strike_prices)-50,
        x1=0, y1=max(strike_prices)+50,
        line=dict(color="white", width=1),
        row=1, col=3
    )
    
    return fig


# 添加中間下部圖表的回調
@app.callback(
    Output('middle-bottom-chart', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_middle_bottom_chart(n):
    # 這是新添加的 SC賣方價格 圖表
    # 目前只顯示一個空圖表和說明文字
    
    fig = go.Figure()
    
    # 添加一個說明文字
    fig.add_annotation(
        text="SC賣方價格數據 (暫無內容)",
        xref="paper", yref="paper",
        x=0.5, y=0.5,
        showarrow=False,
        font=dict(color="white", size=14)
    )
    
    fig.update_layout(
        title=None,
        height=200,
        plot_bgcolor='#2a2a2a',
        paper_bgcolor='#2a2a2a',
        font=dict(color='white'),
        margin=dict(l=40, r=40, t=10, b=40),
        xaxis=dict(
            showgrid=True,
            gridcolor='rgba(255,255,255,0.1)',
            showticklabels=False
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='rgba(255,255,255,0.1)',
            showticklabels=False
        )
    )
    
    return fig

# 右側圖表回調
@app.callback(
    Output('right-charts', 'figure'),
    Input('interval-component', 'n_intervals')
)
def update_right_charts(n):
    df = Final01Tdata
    if df.empty:
        return go.Figure()

        
    df['date'] = df.Time.dt.date
    df['time'] = df.Time.dt.time
    # 定義重置時間點
    reset_morning = time(8, 46)
    reset_afternoon = time(15, 1)
    df['is_reset'] = ((df['time'] == reset_morning) | 
                        (df['time'] == reset_afternoon) | 
                        (df['date'] != df['date'].shift(1, fill_value=pd.Timestamp('1900-01-01').date())))
    # 使用累計總和來創建組識別符
    df['cum_reset'] = df['is_reset'].cumsum()

    # 按照組識別符計算累計成交量
    df['DayCumAmount'] = df.groupby('cum_reset')['Amount'].cumsum()
    df['is_reset2'] = ((df['time'] == reset_morning) | 
                    (df['date'] != df['date'].shift(1, fill_value=pd.Timestamp('1900-01-01').date())))
    # 使用累計總和來創建組識別符
    df['cum_reset2'] = df['is_reset2'].cumsum()

    # 按照組識別符計算累計成交量
    df['DayCumAmount2'] = df.groupby('cum_reset2')['Amount'].cumsum()
    df = df.merge(amount_mean_time[['time','cumsum']], on='time',how='left')
    df['AmountRatio'] = df['DayCumAmount2'] / df['cumsum']
    df.index = df.Time


    #df = df.iloc[-num_points:] if num_points < len(df) else df
    #df.index = df.index.strftime(("%m-%d-%Y %H:%M"))
    df = df.sort_index(ascending=True)
    # 計算 5MA、21MA (最簡單的 rolling mean)
    df['vol5'] = df['Volume'].rolling(5).mean()
    df['vol21'] = df['Volume'].rolling(21).mean()
    df = df[df.index > df.index[-90]]
    
    df['vol_sym'] = 'circle'
    df['vol_sym_c'] = 'rgba(0, 0, 0, 0)'
    df['vol_sym_v'] = 0
    today = datetime.now().strftime('%Y-%m-%d')
    deadline = api.Contracts.Futures.TXF.TXFR1
    ticks = api.ticks(
        contract=api.Contracts.Futures['TXF'][deadline.symbol], 
        date=today
    )
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    df_bs = pd.DataFrame({**ticks})
    df_bs.ts = pd.to_datetime(df_bs.ts)

    ticks2 = api.ticks(
        contract=api.Contracts.Futures['TXF'][deadline.symbol], 
        date=yesterday
    )

    df_bs2 = pd.DataFrame({**ticks2})
    df_bs2.ts = pd.to_datetime(df_bs2.ts)
    df_bs = pd.concat([df_bs,df_bs2],ignore_index=True)
    df_bs.sort_values(["ts"], ascending=True, inplace=True)
    df_bs = df_bs[df_bs['bid_price']>0]
    df_bs['date'] = (df_bs.ts + pd.Timedelta(minutes=1)).dt.strftime('%Y-%m-%d %H:%M:00')
    bid_ask_df = df_bs.groupby(['date','tick_type']).agg({ 'volume': 'sum'}).reset_index().pivot(index='date', columns='tick_type', values='volume').fillna(0)
    bid_ask_df['bid_ask_gap'] = bid_ask_df[1] - bid_ask_df[2]
    
    bid_ask_df.index = pd.to_datetime(bid_ask_df.index)
    df = df.join(bid_ask_df, how='left')
    #print(bid_ask_df)
    #print(df)
    df['bid_ask_sym'] = 'circle'
    df['bid_ask_sym_c'] = 'rgba(0, 0, 0, 0)'
    df['bid_ask_sym_v'] = 0
    bid_ask_df_150.index = pd.to_datetime(bid_ask_df_150.index)
    bid_ask_df_150['gap_150_MA5'] = bid_ask_df_150['gap_150sum'].rolling(5).mean()
    #print(bid_ask_df_150)

    df = df.join(bid_ask_df_150, how='left')
    if third_subplot_data_ready:
        try:
            # 從隊列中獲取最新的處理結果
            third_data = third_subplot_data_queue.queue[0]  # 只查看而不移除
            putcallsum_df = third_data['data']
        except IndexError:
            print("第三個子圖的數據隊列為空，無法獲取數據。")

    else:
        putcallsum_df = pd.read_csv('putcallsum.csv')
    putcallsum_df['PutCallSum60MA'] = putcallsum_df['PutCallSum'].rolling(60).mean()
    putcallsum_df.index = pd.to_datetime(putcallsum_df['Time'])
    putcallsum_df = putcallsum_df.drop('Time', axis=1)
    #print(df.index)
    #print(putcallsum_df.index)
    df = df.join(putcallsum_df, how='left')
    #print(df.PutCallSum60MA)
    for i in range(1,len(df['vol5'])):
        # 以 vol5[i] vs vol21[i] 判斷
        #print(i)
        #print(df.loc[df.index[i],'vol5'], df.loc[df.index[i],'vol21'])
        if df.loc[df.index[i],'vol5'] > df.loc[df.index[i],'vol21'] and df.loc[df.index[i-1],'vol5'] < df.loc[df.index[i-1],'vol21']:
            # 紅色上箭頭
            df.loc[df.index[i],'vol_sym_c'] = 'red'
            df.loc[df.index[i],'vol_sym'] = 'triangle-up'
        elif df.loc[df.index[i],'vol5'] < df.loc[df.index[i],'vol21'] and df.loc[df.index[i-1],'vol5'] > df.loc[df.index[i-1],'vol21']:
            # 藍色下箭頭
            df.loc[df.index[i],'vol_sym_c'] = 'blue'
            df.loc[df.index[i],'vol_sym'] = 'triangle-down'
            df.loc[df.index[i],'vol_sym_v'] = max(df['vol5'].max(),df['vol21'].max())
        else:
            # 藍色下箭頭
            df.loc[df.index[i],'vol_sym_c'] = 'rgba(0, 0, 0, 0)'
            df.loc[df.index[i],'vol_sym'] = 'circle'

        if df.loc[df.index[i],'bid_ask_gap'] / df.loc[df.index[i],'Volume'] >0.3:
            df.loc[df.index[i],'bid_ask_sym_c'] = 'red'
            df.loc[df.index[i],'bid_ask_sym'] = 'triangle-up'
            df.loc[df.index[i],'bid_ask_sym_v'] = df.loc[df.index[i],'bid_ask_gap']

        elif df.loc[df.index[i],'bid_ask_gap'] / df.loc[df.index[i],'Volume'] < -0.3:
            df.loc[df.index[i],'bid_ask_sym_c'] = 'green'
            df.loc[df.index[i],'bid_ask_sym'] = 'triangle-down'
            df.loc[df.index[i],'bid_ask_sym_v'] = df.loc[df.index[i],'bid_ask_gap']
        else:
            df.loc[df.index[i],'bid_ask_sym_c'] = 'rgba(0, 0, 0, 0)'
            df.loc[df.index[i],'bid_ask_sym'] = 'circle'
            df.loc[df.index[i],'bid_ask_sym_v'] = 0

        
        #    arrow_color.append(None)
        #    arrow_symbol.append(None)
        #arrow_y.append(df.iloc[i,'vol5'] )  # 或者放 vol21.iloc[i], 看要貼在哪個數值
    
    # 創建6個子圖，參考 main_app.py 的結構
    fig_right = make_subplots(
        rows=6, cols=1,
        row_heights=[0.3, 0.14, 0.14, 0.14, 0.14, 0.14],
        #subplot_titles=('K線與成交量', 'KD指標', '買賣盤差', '150檔買賣差', '即時價平和', '成交量比'),
        vertical_spacing=0.02,
        specs=[[{"secondary_y": True}],
               [{"secondary_y": False}],
               [{"secondary_y": False}],
               [{"secondary_y": False}],
               [{"secondary_y": True}],
               [{"secondary_y": True}]]
    )
    
    # 第1行：主圖 - K線圖 + 移動平均線 + 成交量
    # 主圖 - K線圖
    fig_right.add_trace(
        go.Candlestick(
            x=df[(df['all_kk'] == -1)&(df['Close'] >df['Open'] )].index,
            open=df[(df['all_kk'] == -1)&(df['Close'] >df['Open'] )]['Open'],
            high=df[(df['all_kk'] == -1)&(df['Close'] >df['Open'] )]['High'],
            low=df[(df['all_kk'] == -1)&(df['Close'] >df['Open'] )]['Low'],
            close=df[(df['all_kk'] == -1)&(df['Close'] >df['Open'] )]['Close'],
            increasing_line_color=decreasing_color,
            increasing_fillcolor=no_color, #fill_increasing_color(df.index>df.index[50])
            decreasing_line_color=decreasing_color,
            decreasing_fillcolor=no_color,#decreasing_color,
            line=dict(width=2),
            name='OHLC',showlegend=False
        )#,
        
        ,row=1, col=1, secondary_y= True
    )
    fig_right.add_trace(
        go.Candlestick(
            x=df[(df['all_kk'] == 1)&(df['Close'] >df['Open'] )].index,
            open=df[(df['all_kk'] == 1)&(df['Close'] >df['Open'] )]['Open'],
            high=df[(df['all_kk'] == 1)&(df['Close'] >df['Open'] )]['High'],
            low=df[(df['all_kk'] == 1)&(df['Close'] >df['Open'] )]['Low'],
            close=df[(df['all_kk'] == 1)&(df['Close'] >df['Open'] )]['Close'],
            increasing_line_color=increasing_color,
            increasing_fillcolor=no_color, #fill_increasing_color(df.index>df.index[50])
            decreasing_line_color=increasing_color,
            decreasing_fillcolor=no_color,#decreasing_color,
            line=dict(width=1),
            name='OHLC',showlegend=False
        )#,
        
        ,row=1, col=1, secondary_y= True
    )
    fig_right.add_trace(
        go.Candlestick(
            x=df[(df['all_kk'] == -1)&(df['Close'] <df['Open'] )].index,
            open=df[(df['all_kk'] == -1)&(df['Close'] <df['Open'] )]['Open'],
            high=df[(df['all_kk'] == -1)&(df['Close'] <df['Open'] )]['High'],
            low=df[(df['all_kk'] == -1)&(df['Close'] <df['Open'] )]['Low'],
            close=df[(df['all_kk'] == -1)&(df['Close'] <df['Open'] )]['Close'],
            increasing_line_color=decreasing_color,
            increasing_fillcolor=decreasing_color, #fill_increasing_color(df.index>df.index[50])
            decreasing_line_color=decreasing_color,
            decreasing_fillcolor=decreasing_color,#decreasing_color,
            line=dict(width=1),
            name='OHLC',showlegend=False
        )#,
        
        ,row=1, col=1, secondary_y= True
    )


    fig_right.add_trace(
        go.Candlestick(
            x=df[(df['all_kk'] == 1)&(df['Close'] <df['Open'] )].index,
            open=df[(df['all_kk'] == 1)&(df['Close'] <df['Open'] )]['Open'],
            high=df[(df['all_kk'] == 1)&(df['Close'] <df['Open'] )]['High'],
            low=df[(df['all_kk'] == 1)&(df['Close'] <df['Open'] )]['Low'],
            close=df[(df['all_kk'] == 1)&(df['Close'] <df['Open'] )]['Close'],
            increasing_line_color=increasing_color,
            increasing_fillcolor=increasing_color, #fill_increasing_color(df.index>df.index[50])
            decreasing_line_color=increasing_color,
            decreasing_fillcolor=increasing_color,#decreasing_color,
            line=dict(width=1),
            name='OHLC',showlegend=False
        )#,
        
        ,row=1, col=1, secondary_y= True
    )

    # 主圖 - 移動平均線

    fig_right.add_trace(
        go.Scatter(
            x=df.index,
            y=df['21MA'],
            connectgaps=True,  # 連接間隙
            name='21MA'
        ),
        row=1, col=1, secondary_y= True
    )
    
    fig_right.add_trace(
        go.Scatter(
            x=df.index,
            y=df['55MA'],
            connectgaps=True,  # 連接間隙
            name='55MA'
        ),
        row=1, col=1, secondary_y= True
    )

    # 主圖 - 布林通道
    fig_right.add_trace(
        go.Scatter(
            x=df.index,
            y=df['upper_band'],
            connectgaps=True,  # 連接間隙
            name='+2σ'
        ),
        row=1, col=1, secondary_y= True
    )
    fig_right.add_trace(
        go.Scatter(
            x=df.index,
            y=df['lower_band'],
            connectgaps=True,  # 連接間隙
            name='-2σ'
        ),
        row=1, col=1, secondary_y= True
    )

   

    # 主圖 - 成交量 (主要y軸)
    volume_colors = [red_color if df['Close'][i] > df['Close'][i-1] else green_color for i in range(len(df['Close']))]
    volume_colors[0] = green_color
    volumes = df['Volume']  # 請確定 df 中有 'Volume' 欄位
    fig_right.add_trace(go.Bar(x=df.index, y=df['Volume'], name='Volume', marker=dict(color=volume_colors,line=dict(width=0))), row=1, col=1)

    
    # 成交量移動平均
    fig_right.add_trace(
        go.Scatter(
            x=df.index,
            y=df.vol5,
            line=dict(color='red'),
            name='5MV'
        ),
        row=1, col=1
    )

    fig_right.add_trace(
        go.Scatter(
            x=df.index,
            y=df.vol21,
            line=dict(color='green'),
            name='21MV'
        ),
        row=1, col=1
    )
    
    
    # 第2行 附圖1 ：KD指標
    fig_right.add_trace(
        go.Scatter(
            x=df.index,
            y=df["K"],
            line=dict(color='green'),
            name='K'
        ),
        row=2, col=1
    )

    fig_right.add_trace(
        go.Scatter(
            x=df.index,
            y=df["D"],
            line=dict(color='red'),
            name='D'
        ),
        row=2, col=1
    )

    # (2) 紅色區域：K>80
    #    step2.1: 建立一條 y=80 的 baseline
    fig_right.add_trace(
        go.Scatter(
            x=df.index,
            y=[80]*len(df),   # 固定值80
            mode='lines',
            line=dict(width=0),   # 使其不顯示線
            showlegend=False
        ),
        row=2, col=1
    )

    #    step2.2: 建立一條只在 K>80 時顯示的線
    k_upper = df["K"].where(df["K"] > 80, other=80)
    fig_right.add_trace(
        go.Scatter(
            x=df.index,
            y=k_upper,
            mode='lines',
            line=dict(width=0),   # 不顯示額外線，只當fill之用
            fill='tonexty',       # 與上個trace之間填充
            fillcolor='rgba(255,0,0,0.5)',  # 半透明紅
            showlegend=False
        ),
        row=2, col=1
    )

    # (3) 綠色區域：K<20
    #    step3.1: 建立一條「K本身，但只在K<20」 (用做fill baseline)
    k_lower = df["K"].where(df["K"] < 20, other=20)
    fig_right.add_trace(
        go.Scatter(
            x=df.index,
            y=k_lower,
            mode='lines',
            line=dict(width=0),
            showlegend=False
        ),
        row=2, col=1
    )

    # step3.2: 建立一條 y=20  並 fill='tonexty'
    fig_right.add_trace(
        go.Scatter(
            x=df.index,
            y=[20]*len(df),   # 固定值20
            mode='lines',
            line=dict(width=0),
            fill='tonexty',   # 向上填充
            fillcolor='rgba(0,255,0,0.5)',  # 半透明綠
            showlegend=False
        ),
        row=2, col=1
    )
    
    
    # 第3行：附圖2 買賣盤差 (柱狀, 漲跌 正紅負綠)
    colors2 = ['red' if val>=0 else 'green' for val in df.bid_ask_gap]
    #print(df.bid_ask_gap)
    fig_right.add_trace(
        go.Bar(
            x=df.index,
            y=df.bid_ask_gap,
            marker_color=colors2,
            name='買賣盤差'
        ),
        row=3, col=1
    
    )
    fig_right.add_trace(
    go.Scatter(
        x=df.index,
        y=df['bid_ask_sym_v'],
        mode='markers',
        marker=dict(
            color=df['bid_ask_sym_c'],
            symbol=df['bid_ask_sym'],
            size=14  # 箭頭大小
        ),
        showlegend=False,
        name='arrow'
    ),
    row=3, col=1
    )
    
    # 第4行：附圖3 150檔買賣差
    colors4 = ['red' if val>=0 else 'green' for val in df.gap_150sum]
    fig_right.add_trace(
        go.Bar(
            x=df.index,
            y=df.gap_150sum,
            marker_color=colors4,
            name='150檔買賣差'
        ),
        row=4, col=1
    
    )
    fig_right.add_trace(
        go.Scatter(
            x=df.index,
            y=df.gap_150_MA5,
            mode='lines',
            marker=dict(color='green'),
            name='150檔買賣差 MA5'
        ),
        row=4, col=1
    )
    
    # 第5行：附圖4 Put/Call Sum 與價平和 (線圖: PutCallSum 與 PutCallSum60MA)
    # 先添加 PutCallSum60MA 作為基準線
    fig_right.add_trace(
        go.Scatter(
            x=df.index,
            y=df.PutCallSum60MA,
            mode='lines',
            marker=dict(color='blue'),
            name='60MA',
            line=dict(width=2)
        ),
        row=5, col=1
    )
    
    # 創建 PutCallSum > PutCallSum60MA 時的填充區域（紅色）
    fig_right.add_trace(
        go.Scatter(
            x=df.index,
            y=df['PutCallSum'].where(df['PutCallSum'] > df['PutCallSum60MA'], df['PutCallSum60MA']),
            mode='lines',
            line=dict(width=0),
            showlegend=False,
            fill='tonexty',
            fillcolor='rgba(255, 0, 0, 0.3)'  # 半透明紅色
        ),
        row=5, col=1
    )
    
    # 創建 PutCallSum < PutCallSum60MA 時的填充區域（綠色）
    fig_right.add_trace(
        go.Scatter(
            x=df.index,
            y=df['PutCallSum'].where(df['PutCallSum'] <= df['PutCallSum60MA'], df['PutCallSum60MA']),
            mode='lines',
            line=dict(width=0),
            showlegend=False,
            fill='tonexty',
            fillcolor='rgba(0, 255, 0, 0.3)'  # 半透明綠色
        ),
        row=5, col=1
    )
    
    # 最後添加 PutCallSum 作為最上層線條
    fig_right.add_trace(
        go.Scatter(
            x=df.index,
            y=df.PutCallSum,
            mode='lines',
            marker=dict(color='blue'),
            name='Sum_P-C',
            line=dict(width=2)
        ),
        row=5, col=1
    )
    # 添加 CallPrice 線 (使用次要 y 軸)
    fig_right.add_trace(
        go.Scatter(
            x=df.index,
            y=df.CallPrice,
            mode='lines',
            marker=dict(color='red'),  # 使用紅色表示 Call
            name='Call Price'
        ),
        row=5, col=1,
        secondary_y=True  # 使用次要 y 軸
    )

    # 添加 PutPrice 線 (使用次要 y 軸)
    fig_right.add_trace(
        go.Scatter(
            x=df.index,
            y=df.PutPrice,
            mode='lines',
            marker=dict(color='green'),  # 使用綠色表示 Put
            name='Put Price'
        ),
        row=5, col=1,
        secondary_y=True  # 使用次要 y 軸
    )
    
    # 第6行：附圖5 成交量比例
    # 計算 AmountRatio 的變化
    df['AmountRatio_change'] = df['AmountRatio'].diff()
    # 為第一個值設置一個預設值（可以為 0 或任何其他值）
    df['AmountRatio_change'].iloc[0] = 0

    # 設定顏色邏輯：與前面比較，增加為紅色，減少為綠色
    colors5 = ['rgba(255, 0, 0, 0.5)' if val > 0 else 'rgba(0, 255, 0, 0.5)' for val in df['AmountRatio_change']]
    fig_right.add_trace(
        go.Bar(
            x=df.index,
            y=df['AmountRatio'],
            marker_color=colors5,
            name='成交量比'
        ),
        row=6, col=1
    )
    
    # 設定 y 軸範圍為 0~1.5
    fig_right.update_yaxes(
        range=[0, 1.5],
        showgrid=False,
        row=6, 
        col=1, secondary_y= False
    )
        
    fig_right.add_trace(
        go.Scatter(
            x=df.index,
            y=df['DayCumAmount'],
            mode='lines',
            marker=dict(color='blue'),
            name='今天累計成交量'
            
            
        ),
        row=6, col=1, secondary_y= True
    )
    
    # 更新子圖標題樣式
    for annotation in fig_right['layout']['annotations']:
        annotation['font'] = dict(color='#ffffff', size=12)
    
    # 設定y軸範圍和標題
    fig_right.update_yaxes(title_text="K線與成交量", row=1, col=1, secondary_y=False)
    #fig_right.update_yaxes(title_text="價格", row=1, col=1, secondary_y=True)
    fig_right.update_yaxes(title_text="KD指標",range=[0, 100], row=2, col=1)
    fig_right.update_yaxes(title_text="買賣盤差", row=3, col=1)
    fig_right.update_yaxes(title_text="150檔買賣差", row=4, col=1)
    fig_right.update_yaxes(title_text="即時價平和", row=5, col=1, secondary_y=False)
    #fig_right.update_yaxes(title_text="選擇權價", row=5, col=1, secondary_y=True)
    fig_right.update_yaxes( title_text="成交量比",range=[0, 1.5], row=6, col=1, secondary_y=False)
    #fig_right.update_yaxes(title_text="累積量", row=6, col=1, secondary_y=True)

    # 更新所有子圖的x軸設定 - 除了最後一個子圖外都隱藏x軸標籤
    for i in range(1, 6):  # 總共6個子圖，前5個隱藏x軸標籤
        fig_right.update_xaxes(
            showticklabels=False,
            gridcolor='#404040',
            color='#ffffff',
            row=i, col=1
        )
    
 
    
    # 更新所有y軸樣式
    fig_right.update_yaxes(
        gridcolor='#404040',
        color='#ffffff'
    )

    fig_right.update_layout(
        title={
            'text': '1分鐘即時資料',
            'font': {'color': '#ffffff', 'size': 16}
        },
        height=800,
        showlegend=False,  # 隱藏圖例
        paper_bgcolor='#1a1a1a',
        plot_bgcolor='#2a2a2a',
        font={'color': '#ffffff'},
        hovermode='x unified',
        
    )
    # 然後在最後的 update_layout 中統一設定所有 x 軸
    fig_right.update_xaxes(
        rangeslider_visible=False,
        rangeselector_visible=False,
        title_text="",  # 移除 x 軸標題
        showticklabels=False,  # 先全部隱藏 x 軸刻度標籤
    )
    # 最後一個子圖顯示x軸標籤
    fig_right.update_xaxes(
        showticklabels=True,
        gridcolor='#404040',
        color='#ffffff',
        row=6, col=1
    )
    # fig_right.update_yaxes(
    #     title_text="",  # 移除所有 y 軸標題
    # )
    return fig_right

# 更新左側圖表標題的回調函數
@app.callback(
    Output('left-chart-title', 'children'),
    [Input('kline-interval-selector', 'value')]
)
def update_left_chart_title(kline_interval):
    if kline_interval == '15':
        return "15分鐘K線"
    else:
        return "60分鐘K線"

# 為 Gunicorn 暴露 server
server = app.server

if __name__ == '__main__':
    import os
    # 啟動第三子圖數據處理線程
    third_subplot_thread = threading.Thread(
        target=process_third_subplot_data, 
        daemon=True
    )
    third_subplot_thread.start()
    print("已啟動期權合約數據處理背景線程")

    # # Cloud Run 會提供 PORT 環境變量
    port = int(os.environ.get('PORT', 8080))
    app.run_server(
        host='0.0.0.0',  # 重要：必須是 0.0.0.0
        port=port,
        debug=False
    )

    # 啟動 Dash 服務器
    # port = int(os.environ.get('PORT', 8080))
    # debug_mode = os.environ.get('DASH_DEBUG', 'false').lower() == 'true'
    # app.run_server(debug=debug_mode, host='0.0.0.0', port=port)
