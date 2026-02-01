import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date
import os

# --- 1. デザイン設定 (視認性重視のグリーン＆縁取り文字) ---
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

def load_data(sheet_name, key_col):
    try:
        df = conn.read(worksheet=sheet_name, ttl="0s")
        if df is not None and not df.empty:
            df = df.dropna(subset=[key_col])
            # 日付列がある場合は型変換
            if '日付' in df.columns:
                df['日付'] = pd.to_datetime(df['日付']).dt.strftime('%Y-%m-%d')
            return df
        return pd.DataFrame()
    except:
        return pd.DataFrame()

def update_spreadsheet(df, sheet_name):
    try:
        conn.update(worksheet=sheet_name, data=df)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"保存失敗: {e}")
        return False

# データの読み込み
f_df = load_data("friends", "名前")
h_df = load_data("history", "日付")
c_df = load_data("courses", "Name")

st.title("⛳️ GOLF BATTLE TRACKER PRO")

# --- 3. 年別の集計設定 ---
st.subheader("📅 年度別・通算成績")
if not h_df.empty:
    # 履歴から存在する「年」を抽出
    h_df['Year'] = pd.to_datetime(h_df['日付']).dt.year
    available_years = sorted(h_df['Year'].unique(), reverse=True)
    current_year = date.today().year
    
    # 今年のデータがなくても選択肢に含める
    if current_year not in available_years:
        available_years = [current_year] + available_years
    
    selected_year = st.selectbox("集計対象の年を選択してください", options=available_years, index=0)
    
    # 選択された年でフィルタリング
    h_df_yearly = h_df[h_df['Year'] == selected_year]
else:
    selected_year = date.today().year
    h_df_yearly = pd.DataFrame()

# --- 4. メイン：通算成績（友達リスト） ---
if not f_df.empty:
    cols = st.columns(len(f_df))
    for i, (idx, row) in enumerate(f_df.iterrows()):
        with cols[i]:
            name = str(row['名前'])
            stats = h_df_yearly[h_df_yearly['対戦相手'] == name] if not h_df_yearly.empty else pd.DataFrame()
            w = (stats['勝敗'] == "勝ち").sum()
            l = (stats['勝敗'] == "負け").sum()
            
            # 写真の表示
            if '写真' in row and pd.notnull(row['写真']) and str(row['写真']) != "":
                st.image(row['写真'], width=120)
            else:
                st.write("📷 No Photo")
            
            st.metric(label=f"{name} ({selected_year})", value=f"{w}勝 {l}敗", delta=f"HC: {row['持ちハンディ']}")

# --- 5. ラウンド結果入力 ---
st.divider()
with st.expander("📝 ラウンド結果を記録する"):
    if not f_df.empty and not c_df.empty:
        col1, col2 = st.columns(2)
        with col1:
            p_date = st.date_input("日付", date.today())
            # 州を含めたコース表示
            c_df['Display'] = c_df['Name'] + " (" + c_df['City'].fillna('') + ", " + c_df['State'].fillna('') + ")"
            course = st.selectbox("コースを選択", options=["-- 選択 --"] + sorted(c_df['Display'].tolist()))
        with col2:
            opps = st.multiselect("対戦相手", options=f_df['名前'].tolist())
            my_gross = st.number_input("自分のスコア", 70, 150, 90)

        if opps and my_gross > 0:
            round_results = []
            for opp in opps:
                st.write(f"--- vs {opp} ---")
                cc1, cc2 = st.columns(2)
                o_score = cc1.number_input(f"{opp}のスコア", 0, 150, 0, key=f"s_{opp}")
                res = cc2.selectbox(f"結果", ["勝ち", "負け", "引き分け"], key=f"r_{opp}")
                round_results.append({"opp": opp, "score": o_score, "res": res})
            
            if st.button("🚀 ラウンド結果をスプレッドシートへ保存"):
                new_h = []
                for r in round_results:
                    new_h.append({
                        "日付": p_date.strftime('%Y-%m-%d'), "ゴルフ場": course, "対戦相手": r["opp"],
                        "自分のスコア": my_gross, "相手のスコア": r["score"], "勝敗": r["res"], "ハンディ適用": "なし"
                    })
                if update_spreadsheet(pd.concat([h_df, pd.DataFrame(new_h)], ignore_index=True), "history"):
                    st.success("保存完了しました！")
                    st.rerun()

# --- 6. 対戦履歴の確認（対戦相手ごとに表示） ---
st.divider()
st.subheader("📊 対戦履歴の確認・管理")
if not h_df.empty:
    opp_filter = st.selectbox("特定の対戦相手で絞り込む", options=["全員表示"] + f_df['名前'].tolist())
    
    # フィルタリング
    view_h_df = h_df.copy()
    if opp_filter != "全員表示":
        view_h_df = view_h_df[view_h_df['対戦相手'] == opp_filter]
    
    # 修正も可能な表を表示
    edited_h = st.data_editor(view_h_df.sort_values(by="日付", ascending=False), num_rows="dynamic", use_container_width=True)
    if st.button("履歴の修正内容を反映"):
        if update_spreadsheet(edited_h, "history"):
            st.success("履歴を更新しました")
            st.rerun()

# --- 7. サイドバー：友達・コース・写真の管理 ---
with st.sidebar:
    st.header("⚙️ メンテナンス")
    
    # 写真の追加・更新機能
    with st.expander("👤 友達の写真・プロフィールを更新"):
        if not f_df.empty:
            target_friend = st.selectbox("更新する友達を選択", options=f_df['名前'].tolist())
            uploaded_file = st.file_uploader(f"{target_friend}さんの写真をアップロード", type=['png', 'jpg', 'jpeg'])
            
            # 注：Streamlit Cloudで直接バイナリ保存は難しいため、通常はURLを指定
            new_url = st.text_input("または写真URLを入力", value=f_df.loc[f_df['名前']==target_friend, '写真'].values[0])
            
            if st.button("写真を反映"):
                f_df.loc[f_df['名前'] == target_friend, '写真'] = new_url
                if update_spreadsheet(f_df, "friends"): st.success("更新しました")
        
        st.divider()
        st.subheader("新規友達追加")
        new_f_name = st.text_input("新しい名前")
        new_f_hc = st.number_input("初期ハンディキャップ", value=0.0)
        if st.button("新規友達を保存"):
            if new_f_name:
                new_row = pd.DataFrame([{"名前": new_f_name, "持ちハンディ": new_f_hc, "写真": ""}])
                if update_spreadsheet(pd.concat([f_df, new_row], ignore_index=True), "friends"): st.rerun()

    with st.expander("⛳️ ゴルフ場を追加 (州を含める)"):
        c_name = st.text_input("コース名 (例: Oak Creek GC)")
        c_city = st.text_input("City", value="Irvine")
        c_state = st.text_input("State", value="CA") # 州入力を追加
        if st.button("コースを保存"):
            if c_name:
                new_course_row = pd.DataFrame([{"Name": c_name, "City": c_city, "State": c_state}])
                if update_spreadsheet(pd.concat([c_df, new_course_row], ignore_index=True), "courses"): st.rerun()

    st.divider()
    if st.button("🔄 最新データに強制更新"):
        st.cache_data.clear()
        st.rerun()
