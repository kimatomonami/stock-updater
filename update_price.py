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
        
        price = info.get('currentPrice', 0)
        if not price:
            price = info.get('regularMarketPrice', 0)
            
        price_str = price if price else "N/A"
        updates.append({"range": f"AD{i}", "values": [[price_str]]})
        
        print(f"Row {i} ({ticker_symbol}) -> Price: {price_str}")
        time.sleep(0.5) # 株価だけなので少しテンポよく
        
    except Exception as e:
        print(f"Error fetching {ticker_symbol} at Row {i}: {e}")
        continue

if updates:
    print("Writing prices to Google Sheets...")
    sheet.batch_update(updates)
    print("Price updates completed successfully!")
else:
    print("No price updates to write.")
