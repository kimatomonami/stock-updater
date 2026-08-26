import os
import json
import time
import re
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

# 3. AC列(29列目)のコードを読み込んで処理し、結果をまとめておく
updates = []

for i, row in enumerate(data[1:], start=2): # 1行目はヘッダーと仮定
    if len(row) < 29:
        continue
    
    ticker_symbol = row[28].strip() # AC列 (インデックス28)
    
    # 空白、または「ティッカー」「Y ファイナンス」などの文字が含まれている場合はスキップ
    if not ticker_symbol or not re.search(r'\d', ticker_symbol):
        continue
    
    # 末尾に .T がついていない日本株コード（例: 7203）の場合は自動で .T を補完
    if ticker_symbol.isdigit() and len(ticker_symbol) == 4:
        ticker_symbol += ".T"
    
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
            
        # 利回りの取得
        yield_val = info.get('dividendYield', 0)
        if yield_val:
            yield_val = yield_val * 100
            
        yield_str = f"{yield_val:.2f}%" if yield_val else "N/A"
        div_str = dividend if dividend else "N/A"
        price_str = price if price else "N/A"
        
        # まとめて書き込むためのリストに追加
        # cell(row, col, value) の形式
        updates.append({"range": f"S{i}", "values": [[yield_str]]})
        updates.append({"range": f"U{i}", "values": [[div_str]]})
        updates.append({"range": f"AD{i}", "values": [[price_str]]})
        
        print(f" -> Prepared: Price={price_str}, Div={div_str}, Yield={yield_str}")
        
        # Yahoo Financeへの負荷軽減
        time.sleep(1)
        
    except Exception as e:
        print(f" -> Error fetching {ticker_symbol} at Row {i}: {e}")
        continue

# 4. スプレッドシートへ一括書き込み（API制限回避）
if updates:
    print("Writing updates to Google Sheets...")
    sheet.batch_update(updates)
    print("All updates completed successfully!")
else:
    print("No updates to write.")
