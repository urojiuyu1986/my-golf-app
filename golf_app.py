import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date

# --- 1. デザイン設定 (視認性・縁取り文字の完全維持) ---
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

# --- 2. GSheets接続と「空行」徹底排除ロジック ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data_safe(sheet_name, key_col):
    try:
        # データを読み込み (キャッシュを無効化して最新を取得)
        df = conn.read(worksheet=sheet_name, ttl="0s")
        if df is not None and not df.empty:
            # 1. 列名の空白を削除
            df.columns = [str(c).strip() for c in df.columns]
            # 2. 指定したキー列（名前など）が空の行を完全に削除 (TypeError対策)
            df = df.dropna(subset=[key_col])
            # 3. 前後の余計な空白を削除
            df[key_col] = df[key_col].astype(str).str.strip()
            return df
        return pd.DataFrame()
    except Exception as e:
        # エラー時はサイドバーに詳細を表示（デバッグ用）
        st.sidebar.error(f"【{sheet_name}】読み込み失敗: {e}")
        return pd.DataFrame()

# データの読み込み
f_df = load_data_safe("friends", "名前")  # 八木さん・ケンさんのシート
h_df = load_data_safe("history", "日付")  # 過去の戦績
c_df = load_data_safe("courses", "Name")  # ゴルフ場リスト

st.title("⛳️ GOLF BATTLE TRACKER PRO")

# --- 3. メイン：通算成績表示 ---
if not f_df.empty:
    st.subheader("📈 通算成績（グロス勝負）")
    # 友達の人数に合わせて列を自動分割
    cols = st.columns(len(f_df))
    for i, (idx, row) in enumerate(f_df.iterrows()):
        with cols[i]:
            name = str(row['名前'])
            # 履歴からこの人の戦績を計算
            stats = h_df[h_df['対戦相手'] == name] if not h_df.empty else pd.DataFrame()
            wins = (stats['勝敗'] == "勝ち").sum()
            losses = (stats['勝敗'] == "負け").sum()
            
            # 安全に表示
            st.metric(label=name, value=f"{wins}勝 {losses}敗", delta=f"HC: {row['持ちハンディ']}")
            st.write("📷 No Photo")
else:
    st.info("スプレッドシートのデータを読み込めていません。Secretsと共有設定を再確認してください。")

# --- 4. ラウンド結果入力 (Rancho San Joaquin等) ---
st.divider()
with st.expander("📝 ラウンド結果を入力"):
    if not f_df.empty and not c_df.empty:
        col1, col2 = st.columns(2)
        with col1:
            p_date = st.date_input("日付", date.today())
            # コース名 (City) の形式でリスト化
            c_list = c_df['Name'] + " (" + c_df['City'].fillna('') + ")"
            course = st.selectbox("コースを選択", options=["-- 選択 --"] + sorted(c_list.tolist()))
        with col2:
            opps = st.multiselect("対戦相手", options=f_df['名前'].tolist())
            score = st.number_input("自分のスコア", 70, 150, 90)
    else:
        st.warning("データ不足のため入力フォームを表示できません。")

# --- 5. メンテナンス機能 ---
with st.sidebar:
    st.header("⚙️ システム")
    if st.button("最新データに強制更新"):
        st.cache_data.clear()
        st.rerun()
