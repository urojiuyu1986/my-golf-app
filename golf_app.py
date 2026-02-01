import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date

# デザイン設定
st.set_page_config(page_title="Golf Battle Pro", page_icon="⛳️", layout="wide")
st.markdown("""
    <style>
    .stApp { background: linear-gradient(180deg, #1e5631 0%, #0c331a 100%); }
    h1, h2, h3, p, label, .stMarkdown, .stSelectbox label, .stMultiSelect label, .stNumberInput label {
        color: #ffffff !important;
        text-shadow: 2px 2px 0 #000, -1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000, 1px 1px 0 #000 !important;
        font-weight: 800 !important;
    }
    div[data-testid="stExpander"], .stForm, div[data-testid="metric-container"] {
        background-color: rgba(255, 255, 255, 0.15) !important;
        border: 2px solid #ffffff !important;
        border-radius: 15px !important;
    }
    div[data-testid="stMetricValue"] { color: #ffff00 !important; text-shadow: 2px 2px 2px #000 !important; }
    </style>
    """, unsafe_allow_html=True)

# GSheets接続
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception:
    st.error("Secretsの設定（URL）が正しくありません。")

def load_data(sheet_name):
    # 列名の定義
    cols = {
        "friends": ['名前', '持ちハンディ', '写真'],
        "history": ['日付', 'ゴルフ場', '対戦相手', '自分のスコア', '相手のスコア', '勝敗', 'ハンディ適用'],
        "courses": ['Name', 'City', 'State']
    }
    try:
        # 読み込み
        df = conn.read(worksheet=sheet_name, ttl="0s")
        if df is None or df.empty:
            return pd.DataFrame(columns=cols[sheet_name])
        
        # もし読み込んだ表に期待した列名がなければ、大文字・小文字を無視して補正
        df.columns = [c.strip() for c in df.columns] # スペース除去
        return df
    except Exception:
        # 読み込み失敗時はコスタメサ周辺の初期データを表示
        if sheet_name == "courses":
            return pd.DataFrame([
                {"Name": "Costa Mesa CC (Los Lagos)", "City": "Costa Mesa", "State": "CA"},
                {"Name": "Oak Creek GC", "City": "Irvine", "State": "CA"}
            ])
        return pd.DataFrame(columns=cols[sheet_name])

# 読み込み
f_df = load_data("friends")
h_df = load_data("history")
c_df = load_data("courses")

st.title("⛳️ GOLF BATTLE TRACKER PRO")

# メイン表示
st.subheader("📝 ラウンド結果を入力")
with st.expander("入力を開始する"):
    if not c_df.empty and 'Name' in c_df.columns:
        # 安全にセレクトボックスを作成
        c_df['Display'] = c_df['Name'].fillna('Unknown') + " (" + c_df['City'].fillna('') + ")"
        course_options = sorted(c_df['Display'].tolist())
        st.selectbox("コースを選択", options=["-- 選択 --"] + course_options)
    else:
        st.warning("ゴルフ場データがありません。サイドバーから追加してください。")

# サイドバーで友達やコースを追加する機能（中身は以前と同じ）
with st.sidebar:
    st.header("⚙️ メンテナンス")
    st.write("ここで友達やコースを追加してください")
