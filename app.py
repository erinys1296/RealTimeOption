import dash
from dash import dcc, html, Input, Output
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

# shioaji相關導入
try:
    import shioaji as sj
    import APIKEY  # 確保這個文件在部署環境中可用
    SHIOAJI_AVAILABLE = True
except ImportError:
    SHIOAJI_AVAILABLE = False
    print("Shioaji未安裝或APIKEY未設置，將使用模擬數據")

# 創建Dash應用
app = dash.Dash(__name__)

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

# 嘗試登入shioaji API
def login_shioaji():
    if not SHIOAJI_AVAILABLE:
        return None, "Shioaji未安裝或APIKEY未設置"
    
    try:
        # 登入shioaji
        print("嘗試登入shioaji...")
        SIM_MODE = True
        api = sj.Shioaji(simulation=SIM_MODE)
        api.login(
            api_key=APIKEY.get_Key(SIM_MODE),
            secret_key=APIKEY.get_Secret(SIM_MODE)
        )
        print("shioaji登入成功!")
        return api, "登入成功"
    except Exception as e:
        print(f"shioaji登入失敗: {e}")
        return None, f"登入失敗: {e}"

# 登入shioaji並保存狀態
api, login_message = login_shioaji()

# 生成模擬數據
def generate_fake_data(n_points=100):
    dates = pd.date_range(start=datetime.now() - timedelta(days=30), end=datetime.now(), freq='1H')
    n = len(dates)
    
    # 基本價格數據
    price_data = {
        'Date': dates,
        'Open': np.random.randn(n).cumsum() + 100,
        'High': np.random.randn(n).cumsum() + 105,
        'Low': np.random.randn(n).cumsum() + 95,
        'Close': np.random.randn(n).cumsum() + 100,
        'Volume': np.random.randint(1000, 10000, n)
    }
    
    # 技術指標
    df = pd.DataFrame(price_data)
    df['21MA'] = df['Close'].rolling(21).mean()
    df['55MA'] = df['Close'].rolling(55).mean()
    df['upper_band'] = df['21MA'] + 2 * df['Close'].rolling(21).std()
    df['lower_band'] = df['21MA'] - 2 * df['Close'].rolling(21).std()
    df['K'] = np.random.uniform(20, 80, n)
    df['D'] = np.random.uniform(20, 80, n)
    df['all_kk'] = np.where(np.random.random(n) > 0.5, 1, -1)
    
    # 成交量相關
    df['vol5'] = df['Volume'].rolling(5).mean()
    df['vol21'] = df['Volume'].rolling(21).mean()
    
    # 其他必要數據
    df['AmountRatio'] = np.random.random(n)
    df['DayCumAmount'] = df['Volume'].cumsum()
    df['bid_ask_gap'] = np.random.randn(n) * 100
    df['gap_150sum'] = np.random.randn(n) * 200
    df['gap_150_MA5'] = np.random.randn(n) * 200
    df['PutCallSum'] = np.random.randn(n) * 10 + 100
    df['PutCallSum60MA'] = np.random.randn(n) * 5 + 100
    df['CallPrice'] = np.random.randn(n) * 2 + 50
    df['PutPrice'] = np.random.randn(n) * 2 + 50
    
    # 特殊標記
    df['vol_sym'] = 'circle'
    df['vol_sym_c'] = 'rgba(0, 0, 0, 0)'
    df['vol_sym_v'] = 0
    df['bid_ask_sym'] = 'circle'
    df['bid_ask_sym_c'] = 'rgba(0, 0, 0, 0)'
    df['bid_ask_sym_v'] = 0
    
    # 設置隨機的符號標記
    for i in range(1, n):
        if np.random.random() > 0.9:
            df.loc[i, 'vol_sym_c'] = 'red'
            df.loc[i, 'vol_sym'] = 'triangle-up'
        elif np.random.random() > 0.9:
            df.loc[i, 'vol_sym_c'] = 'blue'
            df.loc[i, 'vol_sym'] = 'triangle-down'
            df.loc[i, 'vol_sym_v'] = df['vol5'].max()
    
    df.set_index('Date', inplace=True)
    return df.iloc[-n_points:]

# 添加CSS樣式和JavaScript
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

# 應用布局
app.layout = html.Div([
    # 標題區域
    html.Div([
        html.H1("選擇權即時籌碼", style={
            'textAlign': 'center', 
            'marginBottom': 10,
            'color': '#ffffff',
            'textShadow': '0 0 10px rgba(0,255,136,0.3)'
        }),
        html.Div([
            html.P(f"Shioaji API狀態: {login_message}", style={
                'textAlign': 'center',
                'color': 'green' if api else 'red'
            })
        ])
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
            dcc.Graph(id='left-charts', style={'height': '760px'})
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
        
        # 中間欄 - 分為上下兩部分
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
                dcc.Graph(id='middle-bar-chart', style={'height': '510px'})
            ], style={
                'backgroundColor': '#2a2a2a',
                'borderRadius': '8px 8px 0 0',
                'border': '1px solid #444',
                'marginBottom': '5px',
                'height': '560px',
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
                dcc.Graph(id='middle-bottom-chart', style={'height': '200px'})
            ], style={
                'backgroundColor': '#2a2a2a',
                'borderRadius': '0 0 8px 8px',
                'border': '1px solid #444',
                'height': '240px',
                'overflow': 'hidden'
            }),
        ], id='middle-panel', style={
            'width': '20%',
            'height': '820px',
            'display': 'flex',
            'flexDirection': 'column',
            'backgroundColor': '#0a0a0a',
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
    # 根據選擇的K線頻率生成不同的模擬數據
    if kline_interval == '15':
        title_prefix = "15分鐘"
        df = generate_fake_data(60)  # 生成60個數據點
    else:
        title_prefix = "60分鐘"
        df = generate_fake_data(30)  # 生成30個數據點
    
    # 創建子圖：1個主圖 + 2個附圖
    fig_left = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        row_heights=[0.5, 0.25, 0.25],
        specs=[[{"secondary_y": True}]]*3,
        vertical_spacing=0.02
    )
    
    # 添加K線圖 (主圖)
    fig_left.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            increasing_line_color=increasing_color,
            increasing_fillcolor=no_color,
            decreasing_line_color=decreasing_color,
            decreasing_fillcolor=decreasing_color,
            name='OHLC'
        ),
        row=1, col=1, secondary_y=True
    )
    
    # 添加移動平均線
    fig_left.add_trace(
        go.Scatter(
            x=df.index,
            y=df['21MA'],
            line=dict(color='blue', width=1),
            name='21MA'
        ),
        row=1, col=1, secondary_y=True
    )
    
    fig_left.add_trace(
        go.Scatter(
            x=df.index,
            y=df['55MA'],
            line=dict(color='orange', width=1),
            name='55MA'
        ),
        row=1, col=1, secondary_y=True
    )
    
    # 添加布林帶
    fig_left.add_trace(
        go.Scatter(
            x=df.index,
            y=df['upper_band'],
            line=dict(color='gray', width=1, dash='dash'),
            name='Upper Band'
        ),
        row=1, col=1, secondary_y=True
    )
    
    fig_left.add_trace(
        go.Scatter(
            x=df.index,
            y=df['lower_band'],
            line=dict(color='gray', width=1, dash='dash'),
            name='Lower Band'
        ),
        row=1, col=1, secondary_y=True
    )
    
    # 成交量 (主圖的主要y軸)
    volume_colors = [red_color if df['Close'][i] > df['Close'][i-1] else green_color for i in range(1, len(df))]
    volume_colors.insert(0, green_color)
    
    fig_left.add_trace(
        go.Bar(
            x=df.index,
            y=df['Volume'],
            marker_color=volume_colors,
            name='Volume'
        ),
        row=1, col=1
    )
    
    # 附圖1 - KD指標
    fig_left.add_trace(
        go.Scatter(
            x=df.index,
            y=df['K'],
            line=dict(color='green'),
            name='K'
        ),
        row=2, col=1
    )
    
    fig_left.add_trace(
        go.Scatter(
            x=df.index,
            y=df['D'],
            line=dict(color='red'),
            name='D'
        ),
        row=2, col=1
    )
    
    # 附圖2 - 成交量
    fig_left.add_trace(
        go.Bar(
            x=df.index,
            y=df['Volume'],
            marker_color=volume_colors,
            name='成交量'
        ),
        row=3, col=1
    )
    
    # 更新圖表佈局
    fig_left.update_layout(
        height=760,
        showlegend=False,
        paper_bgcolor='#1a1a1a',
        plot_bgcolor='#2a2a2a',
        font={'color': '#ffffff'},
        margin=dict(t=10, b=30, l=50, r=50),
        xaxis_rangeslider_visible=False,
        hovermode='x unified'
    )
    
    # 更新Y軸範圍和格線
    fig_left.update_yaxes(
        gridcolor='#404040',
        color='#ffffff'
    )
    
    # 設定Y軸範圍 (KD指標)
    fig_left.update_yaxes(
        range=[0, 100],
        row=2, col=1
    )
    
    # 更新X軸格式
    fig_left.update_xaxes(
        showticklabels=False,
        gridcolor='#404040',
        color='#ffffff',
        row=1, col=1
    )
    
    fig_left.update_xaxes(
        showticklabels=False,
        gridcolor='#404040',
        color='#ffffff',
        row=2, col=1
    )
    
    fig_left.update_xaxes(
        showticklabels=True,
        gridcolor='#404040',
        color='#ffffff',
        row=3, col=1
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
        column_widths=[0.25, 0.375, 0.375],
        specs=[[{"type": "xy"}, {"type": "xy"}, {"type": "xy"}]],
        horizontal_spacing=0.01
    )
    
    # 行權價列表
    strike_prices = [
        22600, 22550, 22500, 22450, 22400, 22350, 22300, 
        22250, 22200, 22150, 22100, 22050, 22000, 21950, 
        21900, 21850, 21800, 21750, 21700, 21650, 21600
    ]
    
    # 第一欄：垂直線段
    line_x = [15] * len(strike_prices)
    line_y = strike_prices
    
    for i in range(len(strike_prices)-1):
        fig.add_shape(
            type="line",
            x0=line_x[i], y0=line_y[i],
            x1=line_x[i+1], y1=line_y[i+1],
            line=dict(color='red', width=2),
            row=1, col=1
        )
    
    # 添加黃色突出顯示柱狀圖
    x_vals = np.arange(10)
    bar_vals = np.zeros(10)
    bar_vals[-1] = 15  # 最後一個值特別高
    
    fig.add_trace(
        go.Bar(
            x=x_vals, 
            y=bar_vals,
            orientation='h',
            marker_color=['yellow' if v > 0 else 'green' for v in bar_vals],
            showlegend=False
        ),
        row=1, col=1
    )
    
    # 第二欄：Call選擇權數據
    call_values = np.random.randint(-200, 50, size=len(strike_prices))
    call_colors = ['#00FF00' if v > 0 else '#FF0000' for v in call_values]
    call_labels = [f"C {s}" for s in strike_prices]
    call_annotations = [f"{abs(v)}" for v in call_values]
    
    fig.add_trace(
        go.Bar(
            y=strike_prices,
            x=call_values,
            orientation='h',
            marker_color=call_colors,
            text=call_annotations,
            textposition='auto',
            textfont=dict(
                color='yellow',
                size=9
            ),
            showlegend=False
        ),
        row=1, col=2
    )
    
    # 第三欄：Put選擇權數據
    put_values = np.random.randint(-220, 30, size=len(strike_prices))
    put_colors = ['#00FF00' if v > 0 else '#FF0000' for v in put_values]
    put_labels = [f"P {s}" for s in strike_prices]
    put_annotations = [f"{abs(v)}" for v in put_values]
    
    fig.add_trace(
        go.Bar(
            y=strike_prices,
            x=put_values,
            orientation='h',
            marker_color=put_colors,
            text=put_annotations,
            textposition='auto',
            textfont=dict(
                color='yellow',
                size=9
            ),
            showlegend=False
        ),
        row=1, col=3
    )
    
    # 更新佈局
    fig.update_layout(
        height=510,
        plot_bgcolor='black',
        paper_bgcolor='black',
        margin=dict(l=5, r=5, t=5, b=5),
        font=dict(color='white'),
        barmode='relative',
        bargap=0.15,
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
        side='right',
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

# 中間下部圖表的回調
@app.callback(
    Output('middle-bottom-chart', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_middle_bottom_chart(n):
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
    # 生成模擬數據
    df = generate_fake_data(90)
    
    # 創建6個子圖
    fig_right = make_subplots(
        rows=6, cols=1,
        row_heights=[0.3, 0.14, 0.14, 0.14, 0.14, 0.14],
        vertical_spacing=0.02,
        specs=[[{"secondary_y": True}],
               [{"secondary_y": False}],
               [{"secondary_y": False}],
               [{"secondary_y": False}],
               [{"secondary_y": True}],
               [{"secondary_y": True}]]
    )
    
    # 1. K線圖
    fig_right.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            increasing_line_color=increasing_color,
            increasing_fillcolor=no_color,
            decreasing_line_color=decreasing_color,
            decreasing_fillcolor=decreasing_color,
            name='OHLC'
        ),
        row=1, col=1, secondary_y=True
    )
    
    # 移動平均線
    fig_right.add_trace(
        go.Scatter(
            x=df.index,
            y=df['21MA'],
            line=dict(color='blue', width=1),
            name='21MA'
        ),
        row=1, col=1, secondary_y=True
    )
    
    fig_right.add_trace(
        go.Scatter(
            x=df.index,
            y=df['55MA'],
            line=dict(color='orange', width=1),
            name='55MA'
        ),
        row=1, col=1, secondary_y=True
    )
    
    # 成交量
    volume_colors = [red_color if df['Close'][i] > df['Close'][i-1] else green_color for i in range(1, len(df))]
    volume_colors.insert(0, green_color)
    
    fig_right.add_trace(
        go.Bar(
            x=df.index,
            y=df['Volume'],
            marker_color=volume_colors,
            name='Volume'
        ),
        row=1, col=1
    )
    
    # 2. KD指標
    fig_right.add_trace(
        go.Scatter(
            x=df.index,
            y=df['K'],
            line=dict(color='green'),
            name='K'
        ),
        row=2, col=1
    )
    
    fig_right.add_trace(
        go.Scatter(
            x=df.index,
            y=df['D'],
            line=dict(color='red'),
            name='D'
        ),
        row=2, col=1
    )
    
    # 3. 買賣盤差
    colors2 = ['red' if val>=0 else 'green' for val in df.bid_ask_gap]
    fig_right.add_trace(
        go.Bar(
            x=df.index,
            y=df.bid_ask_gap,
            marker_color=colors2,
            name='買賣盤差'
        ),
        row=3, col=1
    )
    
    # 4. 150檔買賣差
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
    
    # 5. 即時價平和
    fig_right.add_trace(
        go.Scatter(
            x=df.index,
            y=df.PutCallSum,
            line=dict(color='blue'),
            name='PutCallSum'
        ),
        row=5, col=1
    )
    
    fig_right.add_trace(
        go.Scatter(
            x=df.index,
            y=df.PutCallSum60MA,
            line=dict(color='orange'),
            name='PutCallSum60MA'
        ),
        row=5, col=1
    )
    
    # 6. 成交量比
    colors5 = ['red' if val > 0.5 else 'green' for val in df.AmountRatio]
    fig_right.add_trace(
        go.Bar(
            x=df.index,
            y=df.AmountRatio,
            marker_color=colors5,
            name='成交量比'
        ),
        row=6, col=1
    )
    
    # 設定y軸標題
    fig_right.update_yaxes(title_text="K線與成交量", row=1, col=1, secondary_y=False)
    fig_right.update_yaxes(title_text="KD指標", range=[0, 100], row=2, col=1)
    fig_right.update_yaxes(title_text="買賣盤差", row=3, col=1)
    fig_right.update_yaxes(title_text="150檔買賣差", row=4, col=1)
    fig_right.update_yaxes(title_text="即時價平和", row=5, col=1)
    fig_right.update_yaxes(title_text="成交量比", range=[0, 1.5], row=6, col=1)
    
    # 更新X軸和Y軸格式
    for i in range(1, 6):
        fig_right.update_xaxes(
            showticklabels=False,
            gridcolor='#404040',
            color='#ffffff',
            row=i, col=1
        )
    
    fig_right.update_xaxes(
        showticklabels=True,
        gridcolor='#404040',
        color='#ffffff',
        row=6, col=1
    )
    
    fig_right.update_yaxes(
        gridcolor='#404040',
        color='#ffffff'
    )
    
    # 更新佈局
    fig_right.update_layout(
        title={
            'text': '1分鐘即時資料',
            'font': {'color': '#ffffff', 'size': 16}
        },
        height=800,
        showlegend=False,
        paper_bgcolor='#1a1a1a',
        plot_bgcolor='#2a2a2a',
        font={'color': '#ffffff'},
        hovermode='x unified',
        xaxis_rangeslider_visible=False,
    )
    
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
    # 獲取端口 (Render將提供PORT環境變量)
    port = int(os.environ.get('PORT', 8080))
    app.run_server(
        host='0.0.0.0',  # 重要：必須是 0.0.0.0 以便在 Render 上正常工作
        port=port,
        debug=False
    )