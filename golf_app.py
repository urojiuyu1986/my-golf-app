import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date

# デザイン設定
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

# GSheets接続
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"接続設定（Secrets）に不備があります: {e}")

def load_data_safe(sheet_name, fallback_cols):
    try:
        # サービスアカウント経由で読み込み
        df = conn.read(worksheet=sheet_name, ttl="0s")
        if df is not None and not df.empty:
            df = df.dropna(how='all') # 完全に空の行を削除
            return df
    except Exception:
        pass
    # 読み込み失敗時は空のデータフレームを返す（エラーにしない）
    return pd.DataFrame(columns=fallback_cols)

# データの読み込み
f_df = load_data_safe("friends", ['名前', '持ちハンディ', '写真'])
h_df = load_data_safe("history", ['日付', 'ゴルフ場', '対戦相手', '自分のスコア', '相手のスコア', '勝敗', 'ハンディ適用'])
c_df = load_data_safe("courses", ['Name', 'City', 'State'])

st.title("⛳️ GOLF BATTLE TRACKER PRO")

# --- 1. 通算成績の表示 ---
st.subheader("📈 通算成績（グロス勝負）")
if not f_df.empty and '名前' in f_df.columns:
    cols = st.columns(len(f_df))
    for i, (idx, row) in enumerate(f_df.iterrows()):
        with cols[i]:
            # TypeError対策: 値が必ず存在するように変換
            name = str(row['名前']) if pd.notnull(row['名前']) else "Unknown"
            hc = str(row['持ちハンディ']) if pd.notnull(row['持ちハンディ']) else "0"
            
            stats = h_df[h_df['対戦相手'] == name] if not h_df.empty else pd.DataFrame()
            w = (stats['勝敗'] == "勝ち").sum()
            l = (stats['勝敗'] == "負け").sum()
            
            st.metric(label=name, value=f"{w}勝 {l}敗", delta=f"HC: {hc}")
else:
    st.info("スプレッドシートの接続を確認してください。")

# --- 2. ラウンド結果入力 ---
st.divider()
with st.expander("📝 ラウンド結果を入力"):
    if not f_df.empty and '名前' in f_df.columns:
        col1, col2 = st.columns(2)
        with col1:
            p_date = st.date_input("日付", date.today())
            # コース選択 (Costa MesaやIrvineのコースを表示)
            if not c_df.empty:
                c_list = (c_df['Name'].fillna('') + " (" + c_df['City'].fillna('') + ")").tolist()
                st.selectbox("コースを選択", options=sorted(c_list))
            else:
                st.selectbox("コースを選択", options=["Rancho San Joaquin", "Costa Mesa CC"])
        with col2:
            st.multiselect("対戦相手", options=f_df['名前'].dropna().tolist())
            st.number_input("自分のスコア", 70, 150, 90)
    else:
        st.warning("データが取得できていません。")

# --- 3. デバッグ情報（困った時用） ---
with st.sidebar:
    if st.checkbox("デバッグ情報を表示"):
        st.write("Friendsデータ:", f_df)
        st.write("Historyデータ:", h_df)
    if st.button("最新データを強制取得"):
        st.cache_data.clear()
        st.rerun()
