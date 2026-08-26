import os
import json
import time
import re
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import yfinance as yf

scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
sa_key_json = os.environ.get('GCP_SA_KEY')
spreadsheet_id = os.environ.get('SPREADSHEET_ID')

creds_dict = json.loads(sa_key_json)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

sheet = client.open_by_key(spreadsheet_id).sheet1
data = sheet.get_all_values()

print(f"Total rows found: {len(data) - 1}")
updates = []

for i, row in enumerate(data[1:], start=2):
    if len(row) < 29:
        continue
    
    ticker_symbol = row[28].strip()
    if not ticker_symbol or not re.search(r'\d', ticker_symbol):
        continue
    
    if ticker_symbol.isdigit() and len(ticker_symbol) == 4:
        ticker_symbol += ".T"
    
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        
        dividend = info.get('dividendRate', 0)
        if not dividend:
            dividend = info.get('trailingAnnualDividendRate', 0)
            
        # 利ロバの取得部分
        yield_val = info.get('dividendYield', 0)
        if yield_val:
            # もし取得した値が 1 未満（例: 0.0395）なら 100倍してパーセントにする
            # すでに 1 以上（例: 3.95 や 395）になっている場合はそのままにする
            if yield_val < 1.0:
                yield_val = yield_val * 100
            
        yield_str = f"{yield_val:.2f}%" if yield_val else "N/A"
            
        yield_str = f"{yield_val:.2f}%" if yield_val else "N/A"
        div_str = dividend if dividend else "N/A"
        
        updates.append({"range": f"S{i}", "values": [[yield_str]]})
        updates.append({"range": f"U{i}", "values": [[div_str]]})
        
        print(f"Row {i} ({ticker_symbol}) -> Yield: {yield_str}, Div: {div_str}")
        time.sleep(1)
        
    except Exception as e:
        print(f"Error fetching {ticker_symbol} at Row {i}: {e}")
        continue

if updates:
    print("Writing dividends to Google Sheets...")
    sheet.batch_update(updates)
    print("Dividend updates completed successfully!")
else:
    print("No dividend updates to write.")
