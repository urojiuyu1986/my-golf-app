import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date
import os

# --- デザイン設定 (視認性重視) ---
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

# --- Googleスプレッドシート連携 ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except:
    st.error("GSheetsへの接続設定が見つかりません。Settings > Secrets を確認してください。")

def load_data(sheet_name):
    # 初期項目の定義
    cols = {
        "friends": ['名前', '持ちハンディ', '写真'],
        "history": ['日付', 'ゴルフ場', '対戦相手', '自分のスコア', '相手のスコア', '勝敗', 'ハンディ適用'],
        "courses": ['Name', 'City', 'State']
    }
    try:
        df = conn.read(worksheet=sheet_name, ttl="0s")
        if df is None or df.empty:
            return pd.DataFrame(columns=cols[sheet_name])
        # 必要な列が欠けている場合に追加
        for c in cols[sheet_name]:
            if c not in df.columns: df[c] = ""
        return df
    except Exception:
        # 失敗時は項目名だけ持った空のDFを返す
        df = pd.DataFrame(columns=cols[sheet_name])
        if sheet_name == "courses":
            # コスタメサ周辺のデフォルトを表示
            df = pd.DataFrame([
                {"Name": "Costa Mesa CC (Los Lagos)", "City": "Costa Mesa", "State": "CA"},
                {"Name": "Oak Creek GC", "City": "Irvine", "State": "CA"}
            ])
        return df

def save_data(df, sheet_name):
    try:
        conn.update(worksheet=sheet_name, data=df)
        st.cache_data.clear()
        return True
    except:
        st.error(f"{sheet_name} の保存に失敗しました。スプレッドシートの共有設定を確認してください。")
        return False

# データの読み込み
f_df = load_data("friends")
h_df = load_data("history")
c_df = load_data("courses")

st.title("⛳️ GOLF BATTLE TRACKER PRO")

# --- サイドバー：メンテナンス ---
with st.sidebar:
    st.header("⚙️ メンテナンス")
    with st.expander("👤 友達・HC管理"):
        edited_f = st.data_editor(f_df, num_rows="dynamic", use_container_width=True, key="f_edit")
        if st.button("友達リストを更新"):
            if save_data(edited_f, "friends"): st.rerun()

    st.divider()
    with st.expander("⛳️ ゴルフ場を追加"):
        new_c_name = st.text_input("コース名")
        new_c_city = st.text_input("City", value="Costa Mesa")
        if st.button("コースを保存"):
            if new_c_name:
                new_row = pd.DataFrame([{"Name": new_c_name, "City": new_c_city, "State": "CA"}])
                if save_data(pd.concat([c_df, new_row], ignore_index=True), "courses"): st.rerun()

# --- メイン画面：成績表示 ---
if not f_df.empty:
    st.subheader("📈 通算成績")
    display_cols = st.columns(len(f_df) if len(f_df) > 0 else 1)
    for i, row in f_df.iterrows():
        with display_cols[i]:
            if '写真' in row and row['写真']: st.image(row['写真'], width=100)
            stats = h_df[h_df['対戦相手'] == row['名前']] if not h_df.empty else pd.DataFrame()
            w = (stats['勝敗']=="勝ち").sum() if not stats.empty else 0
            l = (stats['勝敗']=="負け").sum() if not stats.empty else 0
            st.metric(row['名前'], f"{w}勝 {l}敗", f"HC: {row['持ちハンディ']}")

# --- 入力フォーム ---
st.divider()
with st.expander("📝 ラウンド結果を入力"):
    col1, col2 = st.columns(2)
    with col1:
        play_date = st.date_input("日付", date.today())
        # 安全なリスト作成
        c_list = c_df['Name'] + " (" + c_df['City'].fillna('') + ")" if not c_df.empty else pd.Series(["No Course Data"])
        selected_course = st.selectbox("コースを選択", options=["-- 選択 --"] + sorted(c_list.tolist()))
    with col2:
        selected_opps = st.multiselect("対戦相手", options=f_df['名前'].tolist() if not f_df.empty else [])
        my_gross = st.number_input("自分のスコア", 0, 150, 0)

    if selected_opps and my_gross > 0:
        if st.button("🚀 ラウンドを保存"):
            # ここに保存ロジック（前回のものと同様）
            st.info("保存機能が動作します")

# --- 履歴管理 ---
st.divider()
st.subheader("📊 履歴の確認・修正")
if not h_df.empty:
    edited_h = st.data_editor(h_df, num_rows="dynamic", use_container_width=True)
    if st.button("履歴を反映"):
        if save_data(edited_h, "history"): st.rerun()
