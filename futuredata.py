import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import shioaji as sj
from APIKEY import get_Key, get_Secret

# 設定 simulation mode
SIM_MODE = True
api = sj.Shioaji(simulation=SIM_MODE)

# 登入
api.login(
    api_key=get_Key(SIM_MODE),
    secret_key=get_Secret(SIM_MODE)
)

def resample_df(original_df, frequency):
    df_resample = original_df.resample(frequency)
    df = pd.DataFrame()
    df['Open'] = df_resample['Open'].first()
    df['Low'] = df_resample['Low'].min()
    df['Volume'] = df_resample['Volume'].sum()
    df['Close'] = df_resample['Close'].last()
    df['High'] = df_resample['High'].max()
    df['Amount'] = df_resample['Amount'].sum()
    return df

def get_future_raw_data(start, end):
    deadline = api.Contracts.Futures.TXF.TXFR1
    k_bars = api.kbars(api.Contracts.Futures['TXF'][deadline.symbol], start=start, end=end)
    df = pd.DataFrame({**k_bars})
    df.ts = pd.to_datetime(df.ts)
    df.sort_values(["ts"], ascending=True, inplace=True)
    df.set_index('ts', inplace=True)
    return resample_df(df, 'T')

def get_future_T_data(interval_minutes=1, days=8):
    start_date = datetime.strftime(datetime.today() - timedelta(days=days), '%Y-%m-%d')
    end_date = datetime.strftime(datetime.today(), '%Y-%m-%d')
    FutureData = get_future_raw_data(start_date, end_date)
    
    FutureData.date = pd.to_datetime(FutureData.index)
    FutureData["hourdate"] = np.array(FutureData.date.date.astype(str)) + np.array(FutureData.date.hour.astype(str).str.zfill(2)) +np.array((FutureData.date.minute // interval_minutes).astype(str).str.zfill(2))
    FutureData['date'] = np.array(pd.to_datetime(FutureData.index).values)
    
    FutureData = FutureData.dropna(subset=['Open'])
    FutureData.index = FutureData['date']
    
    tempdf = FutureData[['hourdate', 'Volume',"Amount"]]
    tempdf = tempdf.reset_index()
    
    FinalData = (
        FutureData.groupby('hourdate').max()[["High"]]
        .join(FutureData.groupby('hourdate').min()[["Low"]])
        .join(tempdf.groupby('hourdate')[["Volume"]].sum())
        .join(tempdf.groupby('hourdate')[["Amount"]].sum())
    )
    
    tempopen = FutureData.loc[FutureData.groupby('hourdate').min()['date'].values]
    tempopen.index = tempopen.hourdate
    tempClose = FutureData.loc[FutureData.groupby('hourdate').max()['date'].values]
    tempClose.index = tempClose.hourdate
    
    FinalData = FinalData.join(tempopen[["Open", 'date']]).join(tempClose[["Close"]])
    FinalData.index = FinalData.date
    FinalData.columns = ['High', 'Low', 'Volume','Amount', 'Open', 'Time', 'Close']

    # 計算布林帶指標
    FinalData['21MA'] = FinalData['Close'].rolling(21).mean()
    FinalData['55MA'] = FinalData['Close'].rolling(55).mean()
    #FinalData['MA'] = FinalData['Close'].rolling(200).mean()
    FinalData['std'] = FinalData['Close'].rolling(21).std()
    FinalData['upper_band'] = FinalData['21MA'] + 2 * FinalData['std']
    FinalData['lower_band'] = FinalData['21MA'] - 2 * FinalData['std']
    FinalData['upper_band1'] = FinalData['21MA'] + 1 * FinalData['std']
    FinalData['lower_band1'] = FinalData['21MA'] - 1 * FinalData['std']

    FinalData['IC'] = FinalData['Close'] + 2 * FinalData['Close'].shift(1) - FinalData['Close'].shift(3) -FinalData['Close'].shift(4)


    # 在k线基础上计算KDF，并将结果存储在df上面(k,d,j)
    low_list = FinalData['Low'].rolling(9, min_periods=9).min()
    low_list.fillna(value=FinalData['Low'].expanding().min(), inplace=True)
    high_list = FinalData['High'].rolling(9, min_periods=9).max()
    high_list.fillna(value=FinalData['High'].expanding().max(), inplace=True)
    rsv = (FinalData['Close'] - low_list) / (high_list - low_list) * 100
    FinalData['K'] = pd.DataFrame(rsv).ewm(com=2).mean()
    FinalData['D'] = FinalData['K'].ewm(com=2).mean()

    #enddatemonth = enddate[~enddate["契約月份"].str.contains("W")]['最後結算日']
    FinalData['end_low'] = 0
    FinalData['end_high'] = 0

    #詢問
    ds = 2
    FinalData['uline'] = FinalData['High'].rolling(ds, min_periods=1).max()
    FinalData['dline'] = FinalData['Low'].rolling(ds, min_periods=1).min()

    FinalData["all_kk"] = 0
    barssince5 = 0
    barssince6 = 0
    FinalData['labelb'] = 1
    FinalData = FinalData[~FinalData.index.duplicated(keep='first')]

    for i in range(2,len(FinalData.index)):
        try:
            #(FinalData.loc[FinalData.index[i],'Close'] > FinalData.loc[FinalData.index[i-1],"uline"])
            condition51 = (FinalData.loc[FinalData.index[i-1],"High"] < FinalData.loc[FinalData.index[i-2],"Low"] ) and (FinalData.loc[FinalData.index[i],"Low"] > FinalData.loc[FinalData.index[i-1],"High"] )
            #condition52 = (FinalData.loc[FinalData.index[i-1],'Close'] < FinalData.loc[FinalData.index[i-2],"Low"]) and (FinalData.loc[FinalData.index[i-1],'成交金額'] > FinalData.loc[FinalData.index[i-2],'成交金額']) and (FinalData.loc[FinalData.index[i],'Close']>FinalData.loc[FinalData.index[i-1],"High"] )
            condition53 = (FinalData.loc[FinalData.index[i],'Close'] > FinalData.loc[FinalData.index[i-1],"uline"]) and (FinalData.loc[FinalData.index[i-1],'Close'] <= FinalData.loc[FinalData.index[i-1],"uline"])

            condition61 = (FinalData.loc[FinalData.index[i-1],"Low"] > FinalData.loc[FinalData.index[i-2],"High"] ) and (FinalData.loc[FinalData.index[i],"High"] < FinalData.loc[FinalData.index[i-1],"Low"] )
            #condition62 = (FinalData.loc[FinalData.index[i-1],'Close'] > FinalData.loc[FinalData.index[i-2],"High"]) and (FinalData.loc[FinalData.index[i-1],'成交金額'] > FinalData.loc[FinalData.index[i-2],'成交金額']) and (FinalData.loc[FinalData.index[i],'Close']<FinalData.loc[FinalData.index[i-1],"Low"] )
            condition63 = (FinalData.loc[FinalData.index[i],'Close'] < FinalData.loc[FinalData.index[i-1],"dline"]) and (FinalData.loc[FinalData.index[i-1],'Close'] >= FinalData.loc[FinalData.index[i-1],"dline"])
        except:
            condition51 = True
            condition52 = True
            condition53 = True
            condition61 = True
            condition63 = True
        condition54 = condition51 or condition53 #or condition52
        condition64 = condition61 or condition63 #or condition62 

        #FinalData['labelb'] = np.where((FinalData['Close']> FinalData['upper_band1']) , 1, np.where((FinalData['Close']< FinalData['lower_band1']),-1,1))

        #print(i)
        if FinalData.loc[FinalData.index[i],'Close'] > FinalData.loc[FinalData.index[i],'upper_band1']:
            FinalData.loc[FinalData.index[i],'labelb'] = 1
        elif FinalData.loc[FinalData.index[i],'Close'] < FinalData.loc[FinalData.index[i],'lower_band1']:
            FinalData.loc[FinalData.index[i],'labelb'] = -1
        else:
            FinalData.loc[FinalData.index[i],'labelb'] = FinalData.loc[FinalData.index[i-1],'labelb']

        if condition54 == True:
            barssince5 = 1
        else:
            barssince5 += 1

        if condition64 == True:
            barssince6 = 1
        else:
            barssince6 += 1


        if barssince5 < barssince6:
            FinalData.loc[FinalData.index[i],"all_kk"] = 1
        else:
            FinalData.loc[FinalData.index[i],"all_kk"] = -1

    # 1) 計算 9日最高、最低
    FinalData['9d_high'] = FinalData['High'].rolling(window=9).max()
    FinalData['9d_low'] = FinalData['Low'].rolling(window=9).min()

    # 2) 計算 RSV (若區間最高==最低，避免除0，可自行設為0或做其他處理)
    FinalData['RSV'] = 100 * (FinalData['Close'] - FinalData['9d_low']) / (FinalData['9d_high'] - FinalData['9d_low'])
    # 若要避免 0 除錯，可加上:
    # FinalData['RSV'] = 100 * (FinalData['Close'] - FinalData['9d_low']) / FinalData[['9d_high','9d_low']].apply(lambda x: 1 if x[0]==x[1] else x[0]-x[1], axis=1)

    # 3) 準備 K, D 欄位 (先預設 NaN)
    FinalData['K-value'] = np.nan
    FinalData['D-value'] = np.nan

    # 4) 初始化 K(0)、D(0) (假設第一筆即從資料最前面開始算)
    #   若您要略過前8筆，則可視情況將起始值放在第9筆
    FinalData.loc[FinalData.index[0], 'K-value'] = 50
    FinalData.loc[FinalData.index[0], 'D-value'] = 50

    # 5) 依序迭代計算每行的 K、D
    for i in range(1, len(FinalData)):
        # 取得當筆 RSV
        rsv_t = FinalData.loc[FinalData.index[i], 'RSV']
        k_prev= FinalData.loc[FinalData.index[i-1], 'K-value']
        d_prev= FinalData.loc[FinalData.index[i-1], 'D-value']

        # 略過 NaN
        if pd.isna(rsv_t) or pd.isna(k_prev) or pd.isna(d_prev):
            FinalData.loc[FinalData.index[i], 'K-value'] = k_prev
            FinalData.loc[FinalData.index[i], 'D-value'] = d_prev
        else:
            k_t = k_prev * (2/3) + rsv_t * (1/3)
            d_t = d_prev * (2/3) + k_t * (1/3)

            FinalData.loc[FinalData.index[i], 'K-value'] = k_t
            FinalData.loc[FinalData.index[i], 'D-value'] = d_t

    # 6) 若要清理中間欄位:
    FinalData.drop(columns=['9d_high','9d_low','RSV'], inplace=True)
    #FinalData.index = FinalData.index.strftime(("%m-%d-%Y %H:%M"))

    
    return FinalData

if __name__ == '__main__':
    print(get_future_T_data().head)