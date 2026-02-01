import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date

# --- デザイン設定 ---
st.set_page_config(page_title="Golf Battle Tracker", page_icon="⛳️", layout="wide")
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

# --- GSheets接続 ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(sheet_name):
    try:
        df = conn.read(worksheet=sheet_name, ttl="0s")
        if df is None or df.empty:
            return pd.DataFrame()
        # 【重要】名前や日付が空の行（スプレッドシートの下の方の空行）を完全に削除する
        if sheet_name == "friends":
            df = df.dropna(subset=['名前'])
        elif sheet_name == "history":
            df = df.dropna(subset=['日付'])
        elif sheet_name == "courses":
            df = df.dropna(subset=['Name'])
        return df
    except:
        return pd.DataFrame()

# データの読み込み
f_df = load_data("friends")
h_df = load_data("history")
c_df = load_data("courses")

st.title("⛳️ GOLF BATTLE TRACKER PRO")

# --- 通算成績表示 ---
if not f_df.empty:
    st.subheader("📈 通算成績（グロス勝負）")
    # 表示する友達の数に合わせて列を分ける
    display_df = f_df.head(5) # 最大5人まで横並び
    cols = st.columns(len(display_df))
    
    for i, (idx, row) in enumerate(display_df.iterrows()):
        with cols[i]:
            # 名前が正しく取得できている場合のみ表示
            name = str(row['名前'])
            stats = h_df[h_df['対戦相手'] == name] if not h_df.empty else pd.DataFrame()
            w = (stats['勝敗'] == "勝ち").sum()
            l = (stats['勝敗'] == "負け").sum()
            
            # TypeError対策：ラベルと値が必ず文字列になるようにする
            st.metric(label=name, value=f"{w}勝 {l}敗", delta=f"HC: {row['持ちハンディ']}")

# --- ラウンド結果入力 ---
st.divider()
with st.expander("📝 ラウンド結果を入力"):
    if not f_df.empty and not c_df.empty:
        col1, col2 = st.columns(2)
        with col1:
            p_date = st.date_input("日付", date.today())
            c_list = c_df['Name'] + " (" + c_df['City'].fillna('') + ")"
            course = st.selectbox("コースを選択", options=sorted(c_list.tolist()))
        with col2:
            opps = st.multiselect("対戦相手", options=f_df['名前'].tolist())
            score = st.number_input("自分のスコア", 70, 150, 90)
        
        if st.button("🚀 保存"):
            st.info("保存機能は現在読み込みテスト中です。")
    else:
        st.warning("スプレッドシートに友達またはコースの情報がありません。")

# --- メンテナンス用サイドバー ---
with st.sidebar:
    st.header("⚙️ 設定")
    if st.button("最新データを取得"):
        st.cache_data.clear()
        st.rerun()
