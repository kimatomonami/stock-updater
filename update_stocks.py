import os
import json
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import yfinance as yf

# 1. GCPの認証情報とスプレッドシートIDを設定
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
sa_key_json = os.environ.get('GCP_SA_KEY')
spreadsheet_id = os.environ.get('SPREADSHEET_ID')

creds_dict = json.loads(sa_key_json)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# 2. スプレッドシート「株管理GAS」を開く
sheet = client.open_by_key(spreadsheet_id).sheet1
data = sheet.get_all_values()

print(f"Total rows found: {len(data) - 1}")

# 3. AC列(29列目)のコードを読み込んで、各種データを指定の列に書き込み
for i, row in enumerate(data[1:], start=2): # 1行目はヘッダーと仮定
    if len(row) < 29:
        continue
    
    ticker_symbol = row[28].strip() # AC列 (インデックス28)
    if not ticker_symbol:
        print(f"Row {i}: Ticker is empty. Skipping.")
        continue
    
    print(f"Processing Row {i}: {ticker_symbol} ...")
    
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        
        # 株価の取得
        price = info.get('currentPrice', 0)
        if not price:
            price = info.get('regularMarketPrice', 0)
            
        # 配当額の取得
        dividend = info.get('dividendRate', 0)
        if not dividend:
            dividend = info.get('trailingAnnualDividendRate', 0)
            
        # 利回りの取得 (0.03 などの小数なので 100倍して％表記にする)
        yield_val = info.get('dividendYield', 0)
        if yield_val:
            yield_val = yield_val * 100
            
        # 指定された列にデータを書き込み (上書き)
        sheet.update_cell(i, 19, f"{yield_val:.2f}%" if yield_val else "N/A")
        sheet.update_cell(i, 21, dividend if dividend else "N/A")
        sheet.update_cell(i, 30, price if price else "N/A")
        
        print(f" -> Success: Price={price}, Div={dividend}, Yield={yield_val}%")
        
        # Yahoo Financeへの負荷を減らすため、1銘柄ごとに1秒待機する
        time.sleep(1)
        
    except Exception as e:
        print(f" -> Error fetching {ticker_symbol} at Row {i}: {e}")
        # エラーが出ても次の行へ進む
        continue

print("All rows processed.")
