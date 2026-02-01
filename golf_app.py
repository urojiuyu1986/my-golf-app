import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date

# --- 1. デザイン設定 (視認性・縁取り文字の維持) ---
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

# --- 2. Googleスプレッドシート連携とデータクリーニング ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_cleaned_data(sheet_name, key_column):
    try:
        # スプレッドシートから読み込み
        df = conn.read(worksheet=sheet_name, ttl="0s")
        if df is not None and not df.empty:
            # 名前や日付が入っていない「空の行」を完全に削除する
            df = df.dropna(subset=[key_column])
            # データの型を整理（名前は文字列、スコアは数値など）
            df[key_column] = df[key_column].astype(str).str.strip()
            return df
        return pd.DataFrame()
    except Exception as e:
        # 読み込み失敗時は空の表を返す
        return pd.DataFrame()

# データの読み込み（friendsは'名前'、historyは'日付'、coursesは'Name'を基準に空行を削除）
f_df = load_cleaned_data("friends", "名前")
h_df = load_cleaned_data("history", "日付")
c_df = load_cleaned_data("courses", "Name")

st.title("⛳️ GOLF BATTLE TRACKER PRO")

# --- 3. メイン：通算成績表示 ---
if not f_df.empty:
    st.subheader("📈 通算成績（グロス勝負）")
    # 登録されている人数に合わせて横並びに表示
    cols = st.columns(len(f_df))
    for i, (idx, row) in enumerate(f_df.iterrows()):
        with cols[i]:
            name = row['名前']
            # historyからこの人の戦績を計算
            stats = h_df[h_df['対戦相手'] == name] if not h_df.empty else pd.DataFrame()
            wins = (stats['勝敗'] == "勝ち").sum()
            losses = (stats['勝敗'] == "負け").sum()
            
            # 視覚的なカード表示
            st.metric(label=name, value=f"{wins}勝 {losses}敗", delta=f"HC: {row['持ちハンディ']}")
            st.write("📷 No Photo")
else:
    st.info("スプレッドシートの 'friends' シートにデータが見つかりません。")

# --- 4. ラウンド結果入力 ---
st.divider()
with st.expander("📝 ラウンド結果を入力"):
    if not f_df.empty and not c_df.empty:
        col1, col2 = st.columns(2)
        with col1:
            play_date = st.date_input("日付", date.today())
            # コースリストの作成 (Rancho San Joaquin 等)
            course_options = (c_df['Name'] + " (" + c_df['City'].fillna('') + ")").tolist()
            selected_course = st.selectbox("コースを選択", options=["-- 選択 --"] + sorted(course_options))
        with col2:
            selected_opps = st.multiselect("対戦相手", options=f_df['名前'].tolist())
            my_score = st.number_input("自分のスコア", 70, 150, 90)
        
        if st.button("🚀 保存（テスト中）"):
            st.warning("現在読み込みを優先して確認中です。")
    else:
        st.warning("ゴルフ場データ、または友達データが不足しています。")

# --- 5. サイドバー：最新化ボタン ---
with st.sidebar:
    st.header("⚙️ システム")
    if st.button("最新データに更新"):
        st.cache_data.clear()
        st.rerun()
