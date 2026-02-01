import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date
import base64
from io import BytesIO
from PIL import Image

# --- 1. デザイン設定 (縁取り文字・グリーン背景) ---
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
    section[data-testid="stSidebar"] { background-color: #0c331a !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. Googleスプレッドシート連携 ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data_safe(sheet_name, default_cols):
    try:
        df = conn.read(worksheet=sheet_name, ttl="0s")
        if df is not None:
            df.columns = [str(c).strip() for c in df.columns]
            return df.dropna(how='all')
    except:
        pass
    return pd.DataFrame(columns=default_cols)

def safe_save(df, sheet_name, key_col):
    if df is None or df.empty:
        st.error("保存するデータがありません。")
        return False
    try:
        conn.update(worksheet=sheet_name, data=df)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"保存失敗: {e}")
        return False

# データのロード
f_df = load_data_safe("friends", ['名前', '持ちハンディ', '写真'])
h_df = load_data_safe("history", ['日付', 'ゴルフ場', '対戦相手', '自分のスコア', '相手のスコア', '勝敗', 'ハンディ適用'])
c_df = load_data_safe("courses", ['Name', 'City', 'State'])

st.title("⛳️ GOLF BATTLE TRACKER PRO")

# --- 3. 年度別集計 (2026年初期表示) ---
current_year = 2026
if not h_df.empty and '日付' in h_df.columns:
    h_df['日付DT'] = pd.to_datetime(h_df['日付'], errors='coerce')
    valid_h = h_df.dropna(subset=['日付DT'])
    available_years = sorted(valid_h['日付DT'].dt.year.unique().astype(int), reverse=True)
    if current_year not in available_years:
        available_years = [current_year] + list(available_years)
else:
    available_years = [current_year]
selected_year = st.selectbox("集計する年を選択", options=available_years, index=0)

# --- 4. 通算成績の表示 ---
friend_names = f_df['名前'].dropna().unique().tolist() if '名前' in f_df.columns else []
if friend_names:
    h_selected = h_df[pd.to_datetime(h_df['日付'], errors='coerce').dt.year == selected_year] if not h_df.empty else pd.DataFrame()
    cols = st.columns(len(friend_names))
    for i, name in enumerate(friend_names):
        with cols[i]:
            row = f_df[f_df['名前'] == name].iloc[0]
            stats = h_selected[h_selected['対戦相手'] == name] if not h_selected.empty and '対戦相手' in h_selected.columns else pd.DataFrame()
            w = (stats['勝敗'] == "勝ち").sum() if '勝敗' in stats.columns else 0
            l = (stats['勝敗'] == "負け").sum() if '勝敗' in stats.columns else 0
            
            if '写真' in row and pd.notnull(row['写真']) and str(row['写真']).startswith("data:image"):
                st.image(row['写真'], width=120)
            else:
                st.write("📷 No Photo")
            st.metric(label=f"{name} ({selected_year}年)", value=f"{w}勝 {l}敗", delta=f"HC: {row['持ちハンディ']}")

# --- 5. 対戦履歴の確認 ---
st.divider()
st.subheader("📊 対戦履歴の確認（相手別）")
if not h_df.empty:
    target_opp = st.selectbox("表示する対戦相手", options=["全員"] + friend_names)
    view_df = h_df.copy()
    if target_opp != "全員":
        view_df = view_df[view_df['対戦相手'] == target_opp]
    cols_to_show = [c for c in ['日付', 'ゴルフ場', '対戦相手', '自分のスコア', '相手のスコア', '勝敗', 'ハンディ適用'] if c in view_df.columns]
    st.data_editor(view_df[cols_to_show].sort_values(by="日付", ascending=False), use_container_width=True)

# --- 6. システムメンテナンス (独立したブロック) ---
with st.sidebar:
    st.header("⚙️ システムメンテナンス")
    
    # 【修正点】コース追加を独立させ、エラーに影響されないように配置
    with st.expander("⛳️ 新しいコースを追加", expanded=False):
        nc_name = st.text_input("コース名")
        nc_city = st.text_input("City", value="Costa Mesa")
        nc_state = st.text_input("State", value="CA")
        if st.button("コースを保存"):
            if nc_name:
                new_row = pd.DataFrame([{"Name": nc_name, "City": nc_city, "State": nc_state}])
                if safe_save(pd.concat([c_df, new_row], ignore_index=True), "courses", "Name"):
                    st.success("追加しました！")
                    st.rerun()

    # 【修正点】写真アップロード時のOSError対策
    with st.expander("📸 友達の写真をアップロード", expanded=False):
        if friend_names:
            target_f = st.selectbox("対象の友達", options=friend_names, key="up_target")
            img_file = st.file_uploader("画像を選択", type=['png', 'jpg', 'jpeg'])
            if img_file and st.button(f"{target_f}さんの写真を保存"):
                try:
                    img = Image.open(img_file)
                    # 【重要】透明度(RGBA)があるPNGでも保存できるよう、強制的にRGBに変換
                    img = img.convert("RGB")
                    img.thumbnail((100, 100))
                    buf = BytesIO()
                    img.save(buf, format="JPEG", quality=60)
                    img_b64 = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
                    
                    f_df.loc[f_df['名前'] == target_f, '写真'] = img_b64
                    if safe_save(f_df, "friends", "名前"):
                        st.success("写真を更新しました！")
                        st.rerun()
                except Exception as e:
                    st.error(f"写真の処理に失敗しました: {e}")
        else:
            st.write("友達データがありません。")

    st.divider()
    if st.button("🔄 最新データに強制更新"):
        st.cache_data.clear()
        st.rerun()
