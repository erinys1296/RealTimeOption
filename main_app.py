import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
from plotly.subplots import make_subplots   # <== 新增
from dash_split_pane import DashSplitPane
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from datetime import time

import shioaji as sj
import APIKEY
import futuredata

import requests
from bs4 import BeautifulSoup


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

# 設定simulation mode
SIM_MODE = True

api = sj.Shioaji(simulation=SIM_MODE)
api.login(
    api_key=APIKEY.get_Key(SIM_MODE),
    secret_key=APIKEY.get_Secret(SIM_MODE)
)

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
        date="2025-03-07",
        query_type=sj.constant.TicksQueryType.RangeTime,
        time_start="09:00:00",
        time_end="10:40:01"
    )
    dfticktemp = pd.DataFrame({**ticks})
    dfticktemp.ts = pd.to_datetime(dfticktemp.ts)
    dfticktemp['symbol'] = symbol  # 添加代號欄位
    return dfticktemp

ticks_df_150 = pd.concat([get_ticks_df(symbol) for symbol in df150['代號']], ignore_index=True)
    
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
Final15Tdata = futuredata.get_future_T_data(15,4)
Final60Tdata = futuredata.get_future_T_data(60,2)
Final01Tdata = futuredata.get_future_T_data(1,2)


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


app = dash.Dash(__name__)
server = app.server

# ---------------------------
# (A) 左欄 (改為單一圖 graph-left-main) + RadioItems & Slider
# ---------------------------
graph_left = dcc.Graph(id='graph-left-main', style={'width': '100%', 'height': '100%'})

left_column = html.Div(
    style={
        'display': 'flex',
        'flexDirection': 'column',
        'gap': '5px',
        'height': '100%',
        'padding': '5px',
        'boxSizing': 'border-box',
        'backgroundColor': '#272727'
    },
    children=[
        # Row1: RadioItems 切換 15/60
        html.Div([
            html.Label("Select Update Interval:", style={'color': 'white', 'marginRight': '10px'}),
            dcc.RadioItems(
                id='timeframe-toggle',
                options=[
                    {'label': '15 min', 'value': '15'},
                    {'label': '60 min', 'value': '60'},
                ],
                value='15',
                inputStyle={'marginRight': '5px'},
                style={'display': 'flex', 'flexDirection': 'row', 'gap': '20px', 'color': 'white'}
            )
        ], style={'marginBottom': '5px'}),

        # Row2: Slider (1~300, 預設60)
        html.Div([
            html.Label("Left Data Points:", style={'color': 'white', 'marginRight': '10px'}),
            html.Div([
                dcc.Slider(
                    id='slider-left',
                    min=1,
                    max=300,
                    step=1,
                    value=60,
                    marks={
                        1: '1',
                        50: '50',
                        100: '100',
                        150: '150',
                        200: '200',
                        250: '250',
                        300: '300'
                    },
                    updatemode='mouseup'
                )
            ], style={'width': '90%'})
        ], style={'marginBottom': '5px'}),

        # 單一 Graph (主圖 + 附圖 合併)
        html.Div(
            style={'flex': '1', 'width': '100%', 'height': '100%'},
            children=[graph_left]
        ),
    ]
)

# ---------------------------
# (B) 中欄 (保持一張 graph-center)
# ---------------------------
center_column = html.Div(
    style={
        'display': 'flex',
        'flexDirection': 'column',
        'justifyContent': 'center',
        'alignItems': 'center',
        'height': '100%',
        'padding': '5px',
        'boxSizing': 'border-box',
        'backgroundColor': '#272727'
    },
    children=[
        html.H3('中欄', style={'color': 'white'}),
        dcc.Graph(id='graph-center', style={'width': '100%', 'height': '300px'}),
    ]
)

# ---------------------------
# (C) 右欄 (改為單一圖 graph-right-main) + Slider
# ---------------------------
graph_right = dcc.Graph(id='graph-right-main', style={'width': '100%', 'height': '100%'})

right_column = html.Div(
    style={
        'display': 'flex',
        'flexDirection': 'column',
        'gap': '5px',
        'height': '100%',
        'padding': '5px',
        'boxSizing': 'border-box',
        'backgroundColor': '#272727'
    },
    children=[
        # Slider(1~300,預設60)
        html.Div([
            html.Label("Right Data Points:", style={'color': 'white', 'marginRight': '10px'}),
            html.Div([
                dcc.Slider(
                    id='slider-right',
                    min=1,
                    max=300,
                    step=1,
                    value=60,
                    marks={
                        1: '1',
                        50: '50',
                        100: '100',
                        150: '150',
                        200: '200',
                        250: '250',
                        300: '300'
                    },
                    updatemode='mouseup'
                )
            ], style={'width': '90%'})
        ], style={'marginBottom': '5px'}),

        # 單一 Graph (主圖 + 5個附圖 合併)
        html.Div(
            style={'flex': '1', 'width': '100%', 'height': '100%'},
            children=[graph_right]
        ),
    ]
)

# (D) 最右欄 (隱藏)
extra_column = html.Div(
    style={
        'backgroundColor': '#272727',
        'height': '100%',
        'padding': '5px',
        'boxSizing': 'border-box'
    },
    children=[
        html.H4("No usage, purely for design reasons", style={'color': '#272727'}),
        html.P("No usage, purely for design reasons", style={'color': '#272727'}),
    ]
)

# ---------------------------
# SplitPane 佈局
# ---------------------------
from dash_split_pane import DashSplitPane

third_split_pane = DashSplitPane(
    split='vertical',
    primary='first',
    size='96.77%',
    minSize='80%',
    maxSize='99%',
    children=[right_column, extra_column],
    style={'width': '100%', 'height': '100%'}
)

second_split_pane = DashSplitPane(
    split='vertical',
    primary='first',
    size='24.39%',
    minSize='10%',
    maxSize='50%',
    children=[center_column, third_split_pane],
    style={'width': '100%', 'height': '100%'}
)

outer_split_pane = DashSplitPane(
    split='vertical',
    primary='first',
    size='42.25%',
    minSize='10%',
    maxSize='70%',
    children=[left_column, second_split_pane],
    style={'width': '100%', 'height': '100%'}
)

app.layout = html.Div(
    style={
        'width': '100%',
        'height': '100vh',
        'overflow': 'hidden',
        'margin': 0,
        'padding': 0,
        'backgroundColor': '#272727'
    },
    children=[
        html.H3("即時盤 籌碼分析",
                style={'textAlign': 'center', 'color': 'white', 'margin': '10px'}),
        outer_split_pane,
        # Interval
        dcc.Interval(id='interval-left', interval=900*1000, n_intervals=0),
        dcc.Interval(id='interval-other', interval=60*1000, n_intervals=0),
    ]
)

###################################
# (1) 調整左欄 Callback (單一 Figure, 3-row subplots)
###################################
@app.callback(
    Output('graph-left-main', 'figure'),
    [
        Input('interval-left', 'n_intervals'),
        Input('timeframe-toggle', 'value'),
        Input('slider-left', 'value')
    ]
)
def update_left_charts(n, toggle_value, num_points):
    if toggle_value == '15':
        df = Final15Tdata
    else:
        df = Final60Tdata
    if df.empty:
        return go.Figure()
    #df.index = df.index.strftime(("%m-%d-%Y %H:%M"))
    
    df.index = pd.to_datetime(df.index)
    
    
    df = df.sort_index(ascending=True)
    # 只取最後 num_points
    #df = df.iloc[-num_points:] if num_points < len(df) else df
    df = df[df.index > df.index[-num_points]]
    #df = df.reset_index()
    #df.index = df.index.strftime(("%Y-%m-%d %H:%M")))
    #print(df)
    

   

    # 建立 3-row subplot (主圖 / 附圖1 / 附圖2)
    fig_left = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        row_heights=[0.5, 0.25, 0.25],
        specs=[[{"secondary_y": True}]]*3,
        vertical_spacing=0.02
    )
    # 1) 主圖
    fig_left.add_trace(
        go.Scatter(
            x=df.index,
            y=df['21MA'],
            name='21MA'
        ),
        row=1, col=1, secondary_y= True
    )
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
            name='55MA'
        ),
        row=1, col=1, secondary_y= True
    )
    fig_left.add_trace(
        go.Scatter(
            x=df.index,
            y=df['upper_band'],
            name='+2sigma'
        ),
        row=1, col=1, secondary_y= True
    )
    fig_left.add_trace(
        go.Scatter(
            x=df.index,
            y=df['lower_band'],
            name='-2sigma'
        ),
        row=1, col=1, secondary_y= True
    )


    # Volume (第一 y 軸)
    volume_colors = [red_color if df['Close'][i] > df['Close'][i-1] else green_color for i in range(len(df['Close']))]
    volume_colors[0] = green_color
    volumes = df['Volume']  # 請確定 df 中有 'Volume' 欄位
    fig_left.add_trace(go.Bar(x=df.index, y=df['Volume'], name='Volume', marker=dict(color=volume_colors,line=dict(width=0))), row=1, col=1)


    # 2) 附圖1
    fig_left.add_trace(
        go.Scatter(
            x=df.index,
            y=df['Close'],
            mode='lines+markers',
            marker=dict(color='white'),
            name='附圖1 (Closes)'
        ),
        row=2, col=1
    )
    # 3) 附圖2
    fig_left.add_trace(
        go.Scatter(
            x=df.index,
            y=df['High'],
            mode='lines+markers',
            marker=dict(color='white'),
            name='附圖2 (High-Low)'
        ),
        row=3, col=1
    )

    fig_left.update_layout(
        title=f'左欄主圖+附圖 ({toggle_value}min)',
        autosize=True,
        plot_bgcolor='#272727',
        paper_bgcolor='#272727',
        font=dict(color='white')
    )


    fig_left.update_xaxes(
    rangeslider= {'visible':False},
    rangebreaks=[
        #dict(bounds=[6, 8], pattern="hour")
        dict(bounds=['sat', 'mon']),# hide weekends, eg. hide sat to before mon
        #dict(values=T300noshow)
    ],
                row = 1, 
                col = 1
    )
    fig_left.update_layout(
        title=f'左欄主圖 ({toggle_value}min)',
        hovermode='x unified',
        autosize=True,
        plot_bgcolor='#272727',
        paper_bgcolor='#272727',
        font=dict(color='white'),
        hoverlabel_namelength=-1,
        showlegend=False,
        height = 900,
        xaxis = dict(
            type = 'category'),
        # 也可以視需要設定重疊 or 分佈
        hoverlabel=dict(align='left',bgcolor='rgba(255,255,255,0.5)',font=dict(color='black')),
        legend_traceorder="reversed",
    )
    fig_left.update_yaxes(
        range=[0, df['Volume'].max()+500],showgrid=False,
        secondary_y=False,
                    row = 1, 
                    col = 1
    )
    fig_left.update_yaxes(
        range=[df['Low'].min() - 50, df['High'].max() + 50],showgrid=False,
        secondary_y=True,
                    row = 1, 
                    col = 1
    )
    #print(df)
    return fig_left

###################################
# (2) 中欄 (保持一張 graph-center) => interval-other
###################################
#   (若無變動可省略callback或您原本的Bar圖繼續)

@app.callback(
    Output('graph-center', 'figure'),
    Input('interval-other', 'n_intervals')
)
def update_center_chart(n):
    # 這裡示範簡易Bar
    fig_center = go.Figure([
        go.Bar(x=[1,2,3], y=[4,1,2], marker=dict(color='white'))
    ])
    fig_center.update_layout(
        title='中欄 (Bar示例)',
        autosize=True,
        plot_bgcolor='#272727',
        paper_bgcolor='#272727',
        font=dict(color='white')
    )
    return fig_center

###################################
# (3) 右欄 Callback (單一 Figure, 6-row subplots)
###################################
@app.callback(
    Output('graph-right-main', 'figure'),
    [
        Input('interval-other', 'n_intervals'),
        Input('slider-right', 'value')
    ]
)
def update_right_charts(n, num_points):
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
    df = df[df.index > df.index[-num_points]]
    
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

    x_data = df['Time']
    opens = df['Open']
    highs = df['High']
    lows  = df['Low']
    closes= df['Close']
    #print(df)

    fig_right = make_subplots(
        rows=6, cols=1,
        shared_xaxes=True,
        
        row_heights=[0.3, 0.14, 0.14, 0.14, 0.14, 0.14],
        specs=[[{"secondary_y": True}]]*6,
        vertical_spacing=0.02
    )
    
    # 1) 主圖
    fig_right.add_trace(
        go.Scatter(
            x=df.index,
            y=df['21MA'],
            name='21MA'
        ),
        row=1, col=1, secondary_y= True
    )
    ### K線圖製作 ###
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

    ### K線圖製作 ###
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


    # Volume (第一 y 軸)
    volume_colors = [red_color if df['Close'][i] > df['Close'][i-1] else green_color for i in range(len(df['Close']))]
    volume_colors[0] = green_color
    volumes = df['Volume']  # 請確定 df 中有 'Volume' 欄位
    fig_right.add_trace(go.Bar(x=df.index, y=df['Volume'], name='Volume', marker=dict(color=volume_colors,line=dict(width=0))), row=1, col=1)

    
    fig_right.add_trace(
        go.Scatter(
            x=df.index,
            y=df['55MA'],
            name='55MA'
        ),
        row=1, col=1, secondary_y= True
    )
    fig_right.add_trace(
        go.Scatter(
            x=df.index,
            y=df['upper_band'],
            name='+2sigma'
        ),
        row=1, col=1, secondary_y= True
    )
    fig_right.add_trace(
        go.Scatter(
            x=df.index,
            y=df['lower_band'],
            name='-2sigma'
        ),
        row=1, col=1, secondary_y= True
    )

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
    fig_right.add_trace(
    go.Scatter(
        x=df.index,
        y=df['vol_sym_v'],
        mode='markers',
        marker=dict(
            color=df['vol_sym_c'],
            symbol=df['vol_sym'],
            size=10  # 箭頭大小
        ),
        showlegend=False,
        name='arrow'
    ),
    row=1, col=1
    )
    # row=2: 附圖1 (示範 line)
    # 假設 df['Volume'] 是您的成交量欄位


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

    #    step3.2: 建立一條 y=20  並 fill='tonexty'
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
    # row=3: 附圖2 (柱狀, 漲跌 正紅負綠)
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
    # row=4: 附圖3 (柱狀, High-Close)
    y3 = highs - closes
    colors3 = ['red' if val>=0 else 'green' for val in df.gap_150sum]
    fig_right.add_trace(
        go.Bar(
            x=df.index,
            y=df.gap_150sum,
            marker_color=colors3,
            name='買賣盤差'
        ),
        row=4, col=1
    
    )
    fig_right.add_trace(
        go.Scatter(
            x=df.index,
            y=df.gap_150_MA5,
            mode='lines',
            marker=dict(color='green'),
            name='附圖4 (Lows)'
        ),
        row=4, col=1
    )
     # row=5: 附圖4 (線圖: PutCallSum 與 PutCallSum60MA)
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

    # row=6: 附圖5 (柱狀, closes-lows)
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
        col=1
    )
        
    fig_right.add_trace(
        go.Scatter(
            x=df.index,
            y=df['DayCumAmount'],
            mode='lines',
            marker=dict(color='blue'),
            
            
        ),
        row=6, col=1, secondary_y= True
    )
    # 為每個子圖添加左側標題
    fig_right.update_yaxes(title_text="K線與成交量", row=1, col=1)
    fig_right.update_yaxes(title_text="KD指標", row=2, col=1)
    fig_right.update_yaxes(title_text="買賣盤差", row=3, col=1)
    fig_right.update_yaxes(title_text="150檔買賣差", row=4, col=1)
    fig_right.update_yaxes(title_text="即時價平和", row=5, col=1)
    fig_right.update_yaxes(title_text="成交量比", row=6, col=1)

    fig_right.update_layout(
        title=f'１分K線',
        autosize=True,
        plot_bgcolor='#272727',
        paper_bgcolor='#272727',
        font=dict(color='white')
    )


    fig_right.update_xaxes(
    rangeslider= {'visible':False},
    rangebreaks=[
        #dict(bounds=[6, 8], pattern="hour")
        #dict(bounds=['sat', 'mon']),# hide weekends, eg. hide sat to before mon
        #dict(values=T300noshow)
    ],
                row = 1, 
                col = 1
    )
    fig_right.update_layout(
        title=f'１分K線',
        hovermode='x unified',
        autosize=True,
        plot_bgcolor='#272727',
        paper_bgcolor='#272727',
        font=dict(color='white'),
        hoverlabel_namelength=-1,
        showlegend=False,
        height = 900,
        xaxis=dict(
            type='category'),
        #rangebreaks=[
        #dict(pattern="hour", bounds=[5, 8]),  # 不顯示 05:00~08:00
        #dict(pattern="day of week", bounds=[6, 7]),  # 週六、週日
        #],
        # 也可以視需要設定重疊 or 分佈
        hoverlabel=dict(align='left',bgcolor='rgba(255,255,255,0.5)',font=dict(color='black')),
        legend_traceorder="reversed",
    )
    fig_right.update_yaxes(
        range=[0, df['Volume'].max()+500],showgrid=False,
        secondary_y=False,
                    row = 1, 
                    col = 1
    )
    fig_right.update_yaxes(
        range=[df['lower_band'].min() , df['upper_band'].max() ],showgrid=False,
        secondary_y=True,
                    row = 1, 
                    col = 1
    )

    fig_right.update_xaxes(showgrid=False)
    fig_right.update_yaxes(showgrid=False)
    return fig_right

if __name__ == '__main__':
    app.run_server(debug=True)
