import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import datetime
import streamlit as st
import os

# ★ここにスプレッドシートのID（URLの /d/ と /edit の間の文字列）を貼る
SPREADSHEET_KEY = "1l_Fb9McFOb9FZhpsOqIZNmtbCyh0YHlppQ9pF_2kDrY"

# 認証スコープ
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

def get_connection():
    """スプレッドシートに接続する（ローカル/クラウド両対応）"""
    try:
        # 1. まずローカルのファイルを探す
        if os.path.exists("secrets.json"):
            creds = ServiceAccountCredentials.from_json_keyfile_name("secrets.json", SCOPE)
        # 2. ファイルがなければ、Streamlit Cloudの金庫(secrets)を探す
        elif "gcp_service_account" in st.secrets:
            # st.secretsは辞書形式なので、辞書から認証情報を作る
            key_dict = dict(st.secrets["gcp_service_account"])
            creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, SCOPE)
        else:
            st.error("認証情報が見つかりません。secrets.jsonを置くか、Streamlit CloudのSecretsを設定してください。")
            return None

        client = gspread.authorize(creds)
        sheet = client.open_by_key(SPREADSHEET_KEY).worksheet("characters")
        return sheet
    except Exception as e:
        st.error(f"Googleへの接続に失敗しました: {e}")
        return None

def load_all_characters():
    sheet = get_connection()
    if not sheet: return []
    rows = sheet.get_all_records()
    clean_data = []
    for row in rows:
        try:
            full_data = json.loads(row["全データJSON"])
        except:
            full_data = {}
        clean_data.append({
            "ID": str(row["ID"]),
            "氏名": row["氏名"],
            "画像URL": row["画像URL"],
            "full_data": full_data
        })
    return clean_data

def save_character(char_id, full_data):
    sheet = get_connection()
    if not sheet: return False
    name = full_data.get("profile", {}).get("name", "名称未設定")
    image_url = full_data.get("profile", {}).get("image_file", "")
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    json_str = json.dumps(full_data, ensure_ascii=False)
    try:
        cell = sheet.find(str(char_id), in_column=1)
        row_idx = cell.row
        sheet.update_cell(row_idx, 2, name)
        sheet.update_cell(row_idx, 3, image_url)
        sheet.update_cell(row_idx, 4, now)
        sheet.update_cell(row_idx, 5, json_str)
    except gspread.exceptions.CellNotFound:
        sheet.append_row([str(char_id), name, image_url, now, json_str])
    return True