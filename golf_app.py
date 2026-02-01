import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date

# --- 1. デザイン設定 (縁取り文字・グリーン背景の復活) ---
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

# --- 2. GSheets接続とデータクリーニング ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(sheet_name, key_col):
    try:
        df = conn.read(worksheet=sheet_name, ttl="0s")
        if df is not None and not df.empty:
            # 【TypeError対策】名前や日付が空（NaN/None）の行を完全に削除
            df = df.dropna(subset=[key_col])
            # 文字列として扱う
            df[key_col] = df[key_col].astype(str)
            return df
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

# データの読み込み (各シートの主キーを指定して空行を排除)
f_df = load_data("friends", "名前")
h_df = load_data("history", "日付")
c_df = load_data("courses", "Name")

st.title("⛳️ GOLF BATTLE TRACKER PRO")

# --- 3. メイン：通算成績表示 ---
if not f_df.empty:
    st.subheader("📈 通算成績（グロス勝負）")
    # 友達の人数に合わせて列を作成
    cols = st.columns(len(f_df))
    for i, (idx, row) in enumerate(f_df.iterrows()):
        with cols[i]:
            name = str(row['名前'])
            # 履歴からこの人の戦績を計算
            stats = h_df[h_df['対戦相手'] == name] if not h_df.empty else pd.DataFrame()
            w = (stats['勝敗'] == "勝ち").sum()
            l = (stats['勝敗'] == "負け").sum()
            
            st.metric(label=name, value=f"{w}勝 {l}敗", delta=f"HC: {row['持ちハンディ']}")
            st.write("📷 No Photo") # 写真機能は今後実装可能
else:
    st.info("スプレッドシートから友達データが読み込めませんでした。")

# --- 4. ラウンド結果入力 (以前の多機能フォーム) ---
st.divider()
with st.expander("📝 ラウンド結果を入力"):
    if not f_df.empty and not c_df.empty:
        col1, col2 = st.columns(2)
        with col1:
            p_date = st.date_input("日付", date.today())
            c_list = c_df['Name'] + " (" + c_df['City'].fillna('') + ")"
            course = st.selectbox("コースを選択", options=["-- 選択 --"] + sorted(c_list.tolist()))
        with col2:
            opps = st.multiselect("対戦相手", options=f_df['名前'].tolist())
            score = st.number_input("自分のスコア", 70, 150, 90)
        
        if st.button("🚀 保存"):
            st.warning("現在、読み込みテスト完了のため保存機能は停止しています。")
    else:
        st.warning("friendsシートまたはcoursesシートにデータがありません。")

# --- 5. サイドバー：メンテナンス機能 ---
with st.sidebar:
    st.header("⚙️ メンテナンス")
    with st.expander("👤 友達・HC管理"):
        if not f_df.empty:
            st.data_editor(f_df[['名前', '持ちハンディ']], use_container_width=True, key="f_editor")
    
    with st.expander("⛳️ ゴルフ場を追加"):
        if not c_df.empty:
            st.data_editor(c_df[['Name', 'City']], use_container_width=True, key="c_editor")
            
    st.divider()
    if st.button("最新データを取得（再起動）"):
        st.cache_data.clear()
        st.rerun()
