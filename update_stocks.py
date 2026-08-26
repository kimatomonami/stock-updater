import os
import json
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

# 3. AC列(29列目)のコードを読み込んで、各種データを指定の列に書き込み
# A=1, ..., S=19(利回り), U=21(配当額), AC=29(コード), AD=30(株価)
for i, row in enumerate(data[1:], start=2): # 1行目はヘッダーと仮定
    if len(row) < 29:
        continue
    
    ticker_symbol = row[28] # AC列 (インデックス28)
    if not ticker_symbol:
        continue
    
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
        # S列(19列目): 利回り
        sheet.update_cell(i, 19, f"{yield_val:.2f}%" if yield_val else "N/A")
        # U列(21列目): 配当額
        sheet.update_cell(i, 21, dividend if dividend else "N/A")
        # AD列(30列目): 株価
        sheet.update_cell(i, 30, price if price else "N/A")
        
        print(f"Updated {ticker_symbol} -> Price: {price}, Div: {dividend}, Yield: {yield_val}%")
        
    except Exception as e:
        print(f"Error fetching {ticker_symbol}: {e}")
