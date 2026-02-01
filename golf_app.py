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
    section[data-testid="stSidebar"] { background-color: #0c331a !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. Googleスプレッドシート連携 (キャッシュ対策強化) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data_safe(sheet_name, default_cols):
    try:
        # キャッシュを無視して最新を取得
        df = conn.read(worksheet=sheet_name, ttl="0s")
        if df is not None:
            # 列名の前後の空白を削除
            df.columns = [str(c).strip() for c in df.columns]
            # 完全に空の行を削除
            df = df.dropna(how='all')
            # 指定された列名が見つからない場合の防御
            for col in default_cols:
                if col not in df.columns: df[col] = ""
            return df
    except Exception as e:
        st.sidebar.warning(f"{sheet_name}の読み込み中に軽微な問題が発生しました。")
    return pd.DataFrame(columns=default_cols)

# データのロード
f_df = load_data_safe("friends", ['名前', '持ちハンディ', '写真'])
h_df = load_data_safe("history", ['日付', 'ゴルフ場', '対戦相手', '自分のスコア', '相手のスコア', '勝敗', 'ハンディ適用'])
c_df = load_data_safe("courses", ['Name', 'City', 'State'])

st.title("⛳️ GOLF BATTLE TRACKER PRO")

# --- 3. 年度別の選択と集計 (初期表示は現在の2026年) ---
st.subheader("📅 年度別・通算成績")
current_year = 2026 #

if not h_df.empty and '日付' in h_df.columns:
    # 日付変換の安全ガード
    h_df['日付DT'] = pd.to_datetime(h_df['日付'], errors='coerce')
    valid_h = h_df.dropna(subset=['日付DT'])
    available_years = sorted(valid_h['日付DT'].dt.year.unique().astype(int), reverse=True)
    if current_year not in available_years:
        available_years = [current_year] + list(available_years)
else:
    available_years = [current_year]

selected_year = st.selectbox("集計する年を選択", options=available_years, index=available_years.index(current_year) if current_year in available_years else 0)

# --- 4. メイン：通算成績の表示 (友達データの読み込みを最優先) ---
# 名前が入力されている有効な友達だけを抽出
if '名前' in f_df.columns:
    valid_friends = f_df.dropna(subset=['名前'])
    friend_names = valid_friends['名前'].unique().tolist()
else:
    friend_names = []

if friend_names:
    # 選択された年の履歴をフィルタリング
    h_selected = h_df[pd.to_datetime(h_df['日付'], errors='coerce').dt.year == selected_year] if not h_df.empty else pd.DataFrame()
    
    cols = st.columns(len(friend_names))
    for i, name in enumerate(friend_names):
        with cols[i]:
            row = valid_friends[valid_friends['名前'] == name].iloc[0]
            stats = h_selected[h_selected['対戦相手'] == name] if not h_selected.empty and '対戦相手' in h_selected.columns else pd.DataFrame()
            
            # 勝敗集計
            w = (stats['勝敗'] == "勝ち").sum() if '勝敗' in stats.columns else 0
            l = (stats['勝敗'] == "負け").sum() if '勝敗' in stats.columns else 0
            
            # 写真表示の安全性
            pic_data = str(row['写真']) if '写真' in row and pd.notnull(row['写真']) else ""
            if pic_data.startswith("data:image"):
                st.image(pic_data, width=120)
            else:
                st.write("📷 No Photo")
            
            st.metric(label=f"{name} ({selected_year}年)", value=f"{w}勝 {l}敗", delta=f"HC: {row['持ちハンディ']}")
else:
    st.info("成績を表示する友達データがありません。サイドバーから「最新データに更新」を押すか、友達を再登録してください。")

# --- 5. 対戦相手別の履歴確認 (ご要望通り維持) ---
st.divider()
st.subheader("📊 対戦履歴の確認（相手別）")
if not h_df.empty:
    target_opp = st.selectbox("表示する対戦相手", options=["全員"] + friend_names)
    view_df = h_df.copy()
    if target_opp != "全員":
        view_df = view_df[view_df['対戦相手'] == target_opp]
    
    cols_to_show = [c for c in ['日付', 'ゴルフ場', '対戦相手', '自分のスコア', '相手のスコア', '勝敗', 'ハンディ適用'] if c in view_df.columns]
    st.data_editor(view_df[cols_to_show].sort_values(by="日付", ascending=False), use_container_width=True)

# --- 6. メンテナンス (写真アップロード・追加機能) ---
with st.sidebar:
    st.header("⚙️ システムメンテナンス")
    
    with st.expander("📸 友達の写真をアップロード", expanded=False):
        if friend_names:
            target_f = st.selectbox("対象の友達", options=friend_names, key="side_upload")
            img_file = st.file_uploader("画像を選択", type=['png', 'jpg', 'jpeg'])
            if img_file and st.button(f"{target_f}さんの写真を保存"):
                img = Image.open(img_file)
                img.thumbnail((200, 200)) # 容量削減のためリサイズ
                buf = BytesIO()
                img.save(buf, format="PNG")
                img_b64 = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
                
                # 友達データの更新
                f_df.loc[f_df['名前'] == target_f, '写真'] = img_b64
                conn.update(worksheet="friends", data=f_df)
                st.cache_data.clear()
                st.success("写真を更新しました！")
                st.rerun()
        else:
            st.write("友達データが見つかりません。")

    with st.expander("⛳️ 新しいゴルフ場を追加 (州対応)"):
        nc_name = st.text_input("コース名")
        nc_city = st.text_input("City", value="Costa Mesa")
        nc_state = st.text_input("State", value="CA")
        if st.button("コースを保存"):
            if nc_name:
                new_row = pd.DataFrame([{"Name": nc_name, "City": nc_city, "State": nc_state}])
                conn.update(worksheet="courses", data=pd.concat([c_df, new_row], ignore_index=True))
                st.cache_data.clear()
                st.success("コースを追加しました。")
                st.rerun()

    st.divider()
    if st.button("🔄 データを強制更新"):
        st.cache_data.clear()
        st.rerun()
