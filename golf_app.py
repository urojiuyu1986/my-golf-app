import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date
import base64
from io import BytesIO
from PIL import Image

# --- 1. デザイン設定 (視認性重視) ---
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

# --- 2. Googleスプレッドシート連携と安全な読み込み ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data_safe(sheet_name, key_col):
    try:
        df = conn.read(worksheet=sheet_name, ttl="0s")
        if df is not None and not df.empty:
            df.columns = [str(c).strip() for c in df.columns]
            # 指定されたキー列（名前や日付）が空の行を排除
            df = df.dropna(subset=[key_col])
            return df
        return pd.DataFrame()
    except:
        return pd.DataFrame()

# データのロード
f_df = load_data_safe("friends", "名前")
h_df = load_data_safe("history", "日付")
c_df = load_data_safe("courses", "Name")

# 日付処理の安全性強化（エラーの原因を解消）
if not h_df.empty:
    # errors='coerce' で変換不能な日付を NaT（欠損値）にし、その後削除する
    h_df['日付DT'] = pd.to_datetime(h_df['日付'], errors='coerce')
    h_df = h_df.dropna(subset=['日付DT'])
    h_df['Year'] = h_df['日付DT'].dt.year

st.title("⛳️ GOLF BATTLE TRACKER PRO")

# --- 3. 年度別の選択と集計 (初期表示は現在の2026年) ---
st.subheader("📅 年度別・通算成績")
current_year = date.today().year # 2026年

if not h_df.empty:
    available_years = sorted(h_df['Year'].unique().astype(int), reverse=True)
    if current_year not in available_years:
        available_years = [current_year] + available_years
else:
    available_years = [current_year]

selected_year = st.selectbox("集計する年を選択", options=available_years, index=0)

# --- 4. 通算成績の表示 ---
if not f_df.empty:
    h_selected = h_df[h_df['Year'] == selected_year] if not h_df.empty else pd.DataFrame()
    cols = st.columns(len(f_df))
    for i, (idx, row) in enumerate(f_df.iterrows()):
        with cols[i]:
            name = str(row['名前'])
            stats = h_selected[h_selected['対戦相手'] == name] if not h_selected.empty else pd.DataFrame()
            
            # 安全に計算
            w = (stats['勝敗'] == "勝ち").sum() if '勝敗' in stats.columns else 0
            l = (stats['勝敗'] == "負け").sum() if '勝敗' in stats.columns else 0
            
            # 写真表示 (Base64またはURLに対応)
            if '写真' in row and pd.notnull(row['写真']) and str(row['写真']).startswith("data:image"):
                st.image(row['写真'], width=120)
            else:
                st.write("📷 No Photo")
            
            st.metric(label=f"{name} ({selected_year}年)", value=f"{w}勝 {l}敗", delta=f"HC: {row['持ちハンディ']}")

# --- 5. 対戦相手別の履歴確認 ---
st.divider()
st.subheader("📊 対戦履歴の確認（相手別）")
if not h_df.empty:
    target_opp = st.selectbox("表示する対戦相手", options=["全員"] + f_df['名前'].tolist())
    view_df = h_df.copy()
    if target_opp != "全員":
        view_df = view_df[view_df['対戦相手'] == target_opp]
    
    st.data_editor(view_df[['日付', 'ゴルフ場', '対戦相手', '自分のスコア', '相手のスコア', '勝敗', 'ハンディ適用']].sort_values(by="日付", ascending=False), use_container_width=True)

# --- 6. メンテナンス (写真アップロード・追加機能) ---
with st.sidebar:
    st.header("⚙️ システムメンテナンス")
    
    with st.expander("📸 写真をアップロード・更新"):
        if not f_df.empty:
            target_f = st.selectbox("対象の友達", options=f_df['名前'].tolist())
            img_file = st.file_uploader("画像を選択 (PNG/JPG)", type=['png', 'jpg', 'jpeg'])
            if img_file and st.button(f"{target_f}さんの写真を保存"):
                img = Image.open(img_file)
                img.thumbnail((200, 200))
                buf = BytesIO()
                img.save(buf, format="PNG")
                img_b64 = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
                f_df.loc[f_df['名前'] == target_f, '写真'] = img_b64
                conn.update(worksheet="friends", data=f_df)
                st.cache_data.clear()
                st.success("写真を更新しました！")
                st.rerun()

    with st.expander("⛳️ ゴルフ場を追加 (州対応)"):
        nc_name = st.text_input("コース名")
        nc_city = st.text_input("City", value="Costa Mesa")
        nc_state = st.text_input("State", value="CA") # 州も含める要望に対応
        if st.button("コースを保存"):
            new_row = pd.DataFrame([{"Name": nc_name, "City": nc_city, "State": nc_state}])
            conn.update(worksheet="courses", data=pd.concat([c_df, new_row], ignore_index=True))
            st.cache_data.clear()
            st.success("コースを追加しました。")
            st.rerun()

    st.divider()
    if st.button("🔄 最新データに強制更新"):
        st.cache_data.clear()
        st.rerun()
