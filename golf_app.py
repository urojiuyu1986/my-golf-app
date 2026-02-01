import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date

# --- デザイン設定 (縁取り文字・グリーン背景の維持) ---
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
        padding: 10px !important;
    }
    div[data-testid="stMetricValue"] { color: #ffff00 !important; text-shadow: 2px 2px 2px #000 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 接続とエラー回避機能 ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_and_clean(sheet_name, key_col):
    try:
        # 読み込み (ttl=0で常に最新を取得)
        df = conn.read(worksheet=sheet_name, ttl="0s")
        if df is not None and not df.empty:
            # 【TypeError対策】名前や日付が空の行を完全に削除
            df = df.dropna(subset=[key_col])
            # 文字列として扱い、余計な空白を消す
            df[key_col] = df[key_col].astype(str).str.strip()
            return df
        return pd.DataFrame()
    except Exception as e:
        st.sidebar.error(f"{sheet_name}の読込失敗: {e}")
        return pd.DataFrame()

# データの読み込み
f_df = load_and_clean("friends", "名前") # 八木さん・ケンさんのデータ
h_df = load_and_clean("history", "日付") # 過去の対戦履歴
c_df = load_and_clean("courses", "Name") # ゴルフ場リスト

st.title("⛳️ GOLF BATTLE TRACKER PRO")

# --- 3. メイン：通算成績表示 ---
if not f_df.empty:
    st.subheader("📈 通算成績（グロス勝負）")
    cols = st.columns(len(f_df))
    for i, (idx, row) in enumerate(f_df.iterrows()):
        with cols[i]:
            name = row['名前']
            # 履歴からこの人の成績を抽出
            stats = h_df[h_df['対戦相手'] == name] if not h_df.empty else pd.DataFrame()
            w = (stats['勝敗'] == "勝ち").sum()
            l = (stats['勝敗'] == "負け").sum()
            
            # TypeErrorを防ぐための安全な表示
            st.metric(label=name, value=f"{w}勝 {l}敗", delta=f"HC: {row['持ちハンディ']}")
            st.write("📷 No Photo")
else:
    st.info("データが読み込めていません。Secretsの設定と共有権限を確認してください。")

# --- 4. ラウンド結果入力 ---
st.divider()
with st.expander("📝 ラウンド結果を入力"):
    if not f_df.empty and not c_df.empty:
        col1, col2 = st.columns(2)
        with col1:
            p_date = st.date_input("日付", date.today())
            # Rancho San Joaquin などのコースリスト
            c_list = c_df['Name'] + " (" + c_df['City'].fillna('') + ")"
            course = st.selectbox("コースを選択", options=["-- 選択 --"] + sorted(c_list.tolist()))
        with col2:
            opps = st.multiselect("対戦相手", options=f_df['名前'].tolist())
            score = st.number_input("自分のスコア", 70, 150, 90)
        
        if st.button("🚀 保存（テスト中）"):
            st.info("読み込みテスト完了後、保存機能を稼働させます。")
