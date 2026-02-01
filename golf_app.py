import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date
import base64
from io import BytesIO
from PIL import Image

# --- 1. デザイン設定 ---
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

# --- 2. Googleスプレッドシート連携 ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(sheet_name, key_col):
    try:
        df = conn.read(worksheet=sheet_name, ttl="0s")
        if df is not None and not df.empty:
            # 【KeyError対策】列名の前後の空白を削除してクリーンにする
            df.columns = [str(c).strip() for c in df.columns]
            df = df.dropna(subset=[key_col])
            return df
        return pd.DataFrame()
    except:
        return pd.DataFrame()

def save_to_gsheet(df, sheet_name):
    try:
        conn.update(worksheet=sheet_name, data=df)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"保存に失敗しました: {e}")
        return False

# データのロード
f_df = load_data("friends", "名前")
h_df = load_data("history", "日付")
c_df = load_data("courses", "Name")

st.title("⛳️ GOLF BATTLE TRACKER PRO")

# --- 3. 年別集計（現在の年：2026年を初期値に設定） ---
st.subheader("📅 年度別・通算成績")
current_year = date.today().year # 2026
if not h_df.empty:
    h_df['日付DT'] = pd.to_datetime(h_df['日付'], errors='coerce')
    available_years = sorted(h_df['日付DT'].dt.year.dropna().unique().astype(int), reverse=True)
    if current_year not in available_years:
        available_years = [current_year] + list(available_years)
    
    selected_year = st.selectbox("集計対象の年を選択", options=available_years, index=0)
    # 選択された年でフィルタリング
    h_df_yearly = h_df[pd.to_datetime(h_df['日付']).dt.year == selected_year]
else:
    selected_year = current_year
    h_df_yearly = pd.DataFrame()

# --- 4. メイン：成績表示 ---
if not f_df.empty:
    cols = st.columns(len(f_df))
    for i, (idx, row) in enumerate(f_df.iterrows()):
        with cols[i]:
            name = str(row['名前'])
            # 2026年度（選択年）の成績を計算
            stats = h_df_yearly[h_df_yearly['対戦相手'] == name] if not h_df_yearly.empty else pd.DataFrame()
            
            # 安全にカラムへアクセス (KeyError防止)
            w = (stats['勝敗'] == "勝ち").sum() if '勝敗' in stats.columns else 0
            l = (stats['勝敗'] == "負け").sum() if '勝敗' in stats.columns else 0
            
            # 写真表示
            if '写真' in row and pd.notnull(row['写真']) and row['写真'].startswith("data:image"):
                st.image(row['写真'], width=120)
            else:
                st.write("📷 No Photo")
            
            st.metric(label=f"{name} ({selected_year})", value=f"{w}勝 {l}敗", delta=f"HC: {row['持ちハンディ']}")

# --- 5. ラウンド結果入力（State対応） ---
st.divider()
with st.expander("📝 ラウンド結果を保存する"):
    if not f_df.empty and not c_df.empty:
        col1, col2 = st.columns(2)
        with col1:
            p_date = st.date_input("日付", date.today())
            # 州（State）を含めた表示
            c_df['Disp'] = c_df['Name'] + " (" + c_df['City'].fillna('') + ", " + c_df['State'].fillna('') + ")"
            selected_c = st.selectbox("コースを選択", options=["-- 選択 --"] + sorted(c_df['Disp'].tolist()))
        with col2:
            selected_opps = st.multiselect("対戦相手", options=f_df['名前'].tolist())
            my_score = st.number_input("自分のスコア", 70, 150, 90)

        if st.button("🚀 記録を保存"):
            # ここに保存ロジックを追加（既存と同様）
            st.success("（デモ）保存されました。")

# --- 6. 対戦相手別の履歴確認 ---
st.divider()
st.subheader("📊 対戦履歴の確認（対戦相手別）")
if not h_df.empty:
    target_opp = st.selectbox("履歴を見る相手を選択", options=["全員"] + f_df['名前'].tolist())
    view_df = h_df.copy()
    if target_opp != "全員":
        view_df = view_df[view_df['対戦相手'] == target_opp]
    
    st.data_editor(view_df.sort_values(by="日付", ascending=False), use_container_width=True)

# --- 7. サイドバー：写真アップロード・友達・コース管理 ---
with st.sidebar:
    st.header("⚙️ システムメンテナンス")
    
    with st.expander("📸 友達の写真をアップロード"):
        if not f_df.empty:
            target_f = st.selectbox("写真を変える友達", options=f_df['名前'].tolist())
            img_file = st.file_uploader("写真を選択", type=['png', 'jpg', 'jpeg'])
            if img_file and st.button(f"{target_f}さんの写真を保存"):
                # 画像をBase64に変換してスプレッドシートに保存
                img = Image.open(img_file)
                img.thumbnail((150, 150))
                buffered = BytesIO()
                img.save(buffered, format="PNG")
                img_str = "data:image/png;base64," + base64.b64encode(buffered.getvalue()).decode()
                f_df.loc[f_df['名前'] == target_f, '写真'] = img_str
                if save_to_gsheet(f_df, "friends"): st.rerun()

    with st.expander("⛳️ 新しいゴルフ場を追加"):
        nc_name = st.text_input("コース名")
        nc_city = st.text_input("City", value="Costa Mesa")
        nc_state = st.text_input("State", value="CA")
        if st.button("コースを保存"):
            new_c = pd.concat([c_df[['Name','City','State']], pd.DataFrame([{"Name":nc_name,"City":nc_city,"State":nc_state}])], ignore_index=True)
            if save_to_gsheet(new_c, "courses"): st.rerun()

    if st.button("🔄 データを最新にする"):
        st.cache_data.clear()
        st.rerun()
