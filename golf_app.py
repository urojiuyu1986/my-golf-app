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
    section[data-testid="stSidebar"] { background-color: #0c331a !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. Googleスプレッドシート連携 ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"接続設定エラー: {e}")

def load_data(sheet_name):
    try:
        # データを読み込む
        df = conn.read(worksheet=sheet_name, ttl="0s")
        if df is not None:
            # 完全に空の行を削除
            df = df.dropna(how='all')
            # 列名の前後の余計なスペースを削除
            df.columns = [str(c).strip() for c in df.columns]
            return df
    except Exception as e:
        st.sidebar.warning(f"シート '{sheet_name}' の読み込みに失敗: {e}")
    return pd.DataFrame()

def save_data(df, sheet_name):
    try:
        conn.update(worksheet=sheet_name, data=df)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"保存に失敗しました: {e}")
        st.info("スプレッドシートの共有設定が『編集者』になっているか確認してください。")
        return False

# データの読み込み
f_df = load_data("friends")
h_df = load_data("history")
c_df = load_data("courses")

st.title("⛳️ GOLF BATTLE TRACKER PRO")

# --- 3. メイン：通算成績表示 ---
if not f_df.empty and '名前' in f_df.columns:
    st.subheader("📈 通算成績（グロス勝負）")
    cols = st.columns(len(f_df))
    for i, (idx, row) in enumerate(f_df.iterrows()):
        with cols[i]:
            name = str(row['名前'])
            hc = row.get('持ちハンディ', 0)
            stats = h_df[h_df['対戦相手'] == name] if not h_df.empty and '対戦相手' in h_df.columns else pd.DataFrame()
            w = (stats['勝敗'] == "勝ち").sum() if not stats.empty else 0
            l = (stats['勝敗'] == "負け").sum() if not stats.empty else 0
            st.metric(label=name, value=f"{w}勝 {l}敗", delta=f"HC: {hc}")
            st.write("📷 No Photo")
else:
    st.info("スプレッドシートの 'friends' シートからデータが取得できません。ヘッダーの『名前』を確認してください。")

# --- 4. ラウンド結果入力 (保存機能復活) ---
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
            results = []
            for opp in opps:
                st.write(f"--- vs {opp} ---")
                cc1, cc2 = st.columns(2)
                opp_score = cc1.number_input(f"{opp}のスコア", 0, 150, 0, key=f"s_{opp}")
                res = cc2.selectbox(f"結果", ["勝ち", "負け", "引き分け"], key=f"r_{opp}")
                results.append({"opp": opp, "score": opp_score, "res": res})
            
            if st.button("🚀 このラウンドを保存"):
                new_history = []
                for r in results:
                    new_history.append({
                        "日付": p_date.strftime('%Y-%m-%d'),
                        "ゴルフ場": course,
                        "対戦相手": r["opp"],
                        "自分のスコア": my_gross,
                        "相手のスコア": r["score"],
                        "勝敗": r["res"],
                        "ハンディ適用": "なし"
                    })
                combined_history = pd.concat([h_df, pd.DataFrame(new_history)], ignore_index=True)
                if save_data(combined_history, "history"):
                    st.success("保存完了！")
                    st.rerun()
    else:
        st.warning("データが不足しています。")

# --- 5. サイドバー：追加・メンテナンス機能復活 ---
with st.sidebar:
    st.header("⚙️ メンテナンス")
    
    with st.expander("👤 友達を追加"):
        add_name = st.text_input("名前")
        add_hc = st.number_input("ハンディ", value=0)
        if st.button("友達を保存"):
            if add_name:
                new_f = pd.DataFrame([{"名前": add_name, "持ちハンディ": add_hc, "写真": ""}])
                if save_data(pd.concat([f_df, new_f], ignore_index=True), "friends"): st.rerun()

    with st.expander("⛳️ ゴルフ場を追加"):
        add_c_name = st.text_input("コース名")
        add_c_city = st.text_input("City", value="Costa Mesa")
        if st.button("コースを保存"):
            if add_c_name:
                new_c = pd.DataFrame([{"Name": add_c_name, "City": add_c_city, "State": "CA"}])
                if save_data(pd.concat([c_df, new_c], ignore_index=True), "courses"): st.rerun()

    st.divider()
    if st.button("最新データに更新"):
        st.cache_data.clear()
        st.rerun()
