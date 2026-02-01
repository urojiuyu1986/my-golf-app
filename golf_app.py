import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date

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
            df = df.dropna(subset=[key_col]) # 空行を削除
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

# --- 3. メイン：通算成績（友達リスト） ---
if not f_df.empty:
    st.subheader("📈 通算成績（グロス勝負）")
    cols = st.columns(len(f_df))
    for i, (idx, row) in enumerate(f_df.iterrows()):
        with cols[i]:
            name = str(row['名前'])
            stats = h_df[h_df['対戦相手'] == name] if not h_df.empty else pd.DataFrame()
            w = (stats['勝敗'] == "勝ち").sum()
            l = (stats['勝敗'] == "負け").sum()
            
            # 写真の表示 (URLまたはパスがある場合)
            if '写真' in row and pd.notnull(row['写真']) and str(row['写真']) != "":
                st.image(row['写真'], width=120)
            else:
                st.write("📷 No Photo")
            
            st.metric(label=name, value=f"{w}勝 {l}敗", delta=f"HC: {row['持ちハンディ']}")

# --- 4. ラウンド結果入力 ---
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
            my_gross = st.number_input("自分のスコア", 70, 150, 90)

        if opps and my_gross > 0:
            round_results = []
            for opp in opps:
                st.write(f"--- vs {opp} ---")
                cc1, cc2 = st.columns(2)
                o_score = cc1.number_input(f"{opp}のスコア", 0, 150, 0, key=f"s_{opp}")
                res = cc2.selectbox(f"結果", ["勝ち", "負け", "引き分け"], key=f"r_{opp}")
                round_results.append({"opp": opp, "score": o_score, "res": res})
            
            if st.button("🚀 ラウンドを保存"):
                new_h = []
                for r in round_results:
                    new_h.append({
                        "日付": p_date.strftime('%Y-%m-%d'), "ゴルフ場": course, "対戦相手": r["opp"],
                        "自分のスコア": my_gross, "相手のスコア": r["score"], "勝敗": r["res"], "ハンディ適用": "なし"
                    })
                new_history_df = pd.concat([h_df, pd.DataFrame(new_h)], ignore_index=True)
                if update_spreadsheet(new_history_df, "history"):
                    st.success("履歴を保存しました！")
                    st.rerun()

# --- 5. 対戦履歴の表示・修正 ---
st.divider()
with st.expander("📊 対戦履歴の確認・修正"):
    if not h_df.empty:
        # 日付順にソートして表示
        sorted_h = h_df.sort_values(by="日付", ascending=False)
        edited_h = st.data_editor(sorted_h, num_rows="dynamic", use_container_width=True)
        if st.button("履歴の修正を保存"):
            if update_spreadsheet(edited_h, "history"):
                st.success("履歴を更新しました")
                st.rerun()

# --- 6. サイドバー：メンテナンス (友達・コース追加) ---
with st.sidebar:
    st.header("⚙️ メンテナンス")
    
    with st.expander("👤 友達を追加"):
        f_name = st.text_input("名前")
        f_hc = st.number_input("ハンディ", value=0.0)
        f_pic = st.text_input("写真URL (任意)")
        if st.button("友達を保存"):
            if f_name:
                new_f = pd.concat([f_df, pd.DataFrame([{"名前": f_name, "持ちハンディ": f_hc, "写真": f_pic}])], ignore_index=True)
                if update_spreadsheet(new_f, "friends"): st.rerun()

    with st.expander("⛳️ ゴルフ場を追加"):
        c_name = st.text_input("コース名")
        c_city = st.text_input("City", value="Costa Mesa")
        if st.button("コースを保存"):
            if c_name:
                new_c = pd.concat([c_df, pd.DataFrame([{"Name": c_name, "City": c_city, "State": "CA"}])], ignore_index=True)
                if update_spreadsheet(new_c, "courses"): st.rerun()

    st.divider()
    if st.button("最新データに更新"):
        st.cache_data.clear()
        st.rerun()

