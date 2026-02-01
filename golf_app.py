import streamlit as st
import pandas as pd
from datetime import date
import os
from PIL import Image

# --- 1. ファイル・フォルダ設定 ---
HISTORY_FILE = 'golf_history.csv'
FRIENDS_FILE = 'friends_master.csv'
COURSES_FILE = 'courses_master.csv'
PHOTO_DIR = 'photos'

if not os.path.exists(PHOTO_DIR):
    os.makedirs(PHOTO_DIR)

# --- 2. データの初期化・読み込み ---
def init_data():
    # 友達データ
    if os.path.exists(FRIENDS_FILE):
        f_df = pd.read_csv(FRIENDS_FILE)
    else:
        f_df = pd.DataFrame(columns=['名前', '持ちハンディ', '写真'])
    
    # 履歴データ（日付エラー対策済み）
    if os.path.exists(HISTORY_FILE):
        h_df = pd.read_csv(HISTORY_FILE)
        h_df['日付'] = pd.to_datetime(h_df['日付'], errors='coerce', format='mixed').dt.strftime('%Y-%m-%d')
        h_df = h_df.dropna(subset=['日付']).sort_values(by='日付', ascending=False)
    else:
        h_df = pd.DataFrame(columns=['日付', 'ゴルフ場', '対戦相手', '自分のスコア', '相手のスコア', '勝敗', 'ハンディ適用'])

    # コースデータ（Costa Mesa/Irvineエリアをプリセット）
    if os.path.exists(COURSES_FILE):
        c_df = pd.read_csv(COURSES_FILE)
    else:
        data = [
            {"Name": "Costa Mesa CC (Los Lagos)", "City": "Costa Mesa", "State": "CA"},
            {"Name": "Oak Creek GC", "City": "Irvine", "State": "CA"},
            {"Name": "Strawberry Farms GC", "City": "Irvine", "State": "CA"}
        ]
        c_df = pd.DataFrame(data)
        c_df.to_csv(COURSES_FILE, index=False)
    
    return f_df, h_df, c_df

f_df, h_df, c_df = init_data()

# --- 3. 視認性・デザイン設定 (CSS) ---
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
        padding: 15px !important;
    }
    div[data-testid="stMetricValue"] { color: #ffff00 !important; text-shadow: 2px 2px 2px #000 !important; }
    section[data-testid="stSidebar"] { background-color: #0c331a !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("⛳️ GOLF BATTLE TRACKER PRO")

# --- 4. サイドバー：管理・設定 ---
with st.sidebar:
    st.header("⚙️ メンテナンス")
    
    # 友達登録・写真更新
    with st.expander("👤 友達・HC管理"):
        # 新規登録
        new_name = st.text_input("名前")
        new_hc = st.number_input("初期HC", value=0)
        if st.button("新規追加"):
            if new_name:
                new_f = pd.DataFrame([{"名前": new_name, "持ちハンディ": new_hc, "写真": ""}])
                f_df = pd.concat([f_df, new_f], ignore_index=True)
                f_df.to_csv(FRIENDS_FILE, index=False)
                st.rerun()
        
        st.divider()
        # 写真の更新
        if not f_df.empty:
            target_f = st.selectbox("写真を更新する友達", options=f_df['名前'].tolist())
            pic_file = st.file_uploader("写真を選択", type=['png', 'jpg', 'jpeg'], key="pic_up")
            if st.button("写真を保存"):
                if pic_file:
                    path = os.path.join(PHOTO_DIR, f"{target_f}.png")
                    Image.open(pic_file).save(path)
                    f_df.loc[f_df['名前'] == target_f, '写真'] = path
                    f_df.to_csv(FRIENDS_FILE, index=False)
                    st.rerun()

    # ゴルフ場追加
    with st.expander("⛳️ ゴルフ場を追加"):
        c_name = st.text_input("コース名")
        c_city = st.text_input("City", value="Costa Mesa")
        if st.button("コース保存"):
            if c_name:
                new_c = pd.DataFrame([{"Name": c_name, "City": c_city, "State": "CA"}])
                c_df = pd.concat([c_df, new_c], ignore_index=True)
                c_df.to_csv(COURSES_FILE, index=False)
                st.rerun()

    st.divider()
    # 既存データの修正
    if not f_df.empty:
        st.subheader("友達リストの編集")
        edited_f = st.data_editor(f_df[['名前', '持ちハンディ']], num_rows="dynamic")
        if st.button("リストを更新"):
            edited_f['写真'] = f_df['写真']
            edited_f.to_csv(FRIENDS_FILE, index=False)
            st.rerun()

# --- 5. メイン：成績表示 ---
if not f_df.empty:
    st.subheader("📈 通算成績（グロス勝負）")
    cols = st.columns(len(f_df))
    for i, row in f_df.iterrows():
        with cols[i]:
            pic = row['写真']
            if pic and os.path.exists(str(pic)): st.image(pic, width=120)
            else: st.write("📷 No Photo")
            
            stats = h_df[h_df['対戦相手'] == row['名前']]
            w, l = (stats['勝敗']=="勝ち").sum(), (stats['勝敗']=="負け").sum()
            st.metric(row['名前'], f"{w}勝 {l}敗", f"HC: {row['持ちハンディ']}")

# --- 6. ラウンド結果入力 ---
st.divider()
with st.expander("📝 ラウンド結果を記録", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        play_date = st.date_input("日付", date.today())
        c_df['Display'] = c_df['Name'] + " (" + c_df['City'].fillna('') + ")"
        selected_course = st.selectbox("コースを選択", options=["-- 選択 --"] + sorted(c_df['Display'].tolist()))
    with col2:
        selected_opps = st.multiselect("対戦相手", options=f_df['名前'].tolist())
        my_gross = st.number_input("自分のスコア", 0, 150, 0)

    if selected_opps:
        results = {}
        for opp in selected_opps:
            st.write(f"--- vs {opp} ---")
            cc1, cc2, cc3 = st.columns(3)
            o_score = cc1.number_input(f"{opp}のスコア", 0, 150, 0, key=f"s_{opp}")
            
            current_h = f_df[f_df['名前'] == opp]['持ちハンディ'].values[0]
            use_hc = cc2.checkbox(f"HC適用 (現在:{current_h})", value=True, key=f"h_{opp}")
            
            if my_gross > 0 and o_score > 0:
                net = my_gross - (current_h if use_hc else 0)
                calc_res = "勝ち" if net < o_score else ("負け" if net > o_score else "引き分け")
                final_res = cc3.selectbox(f"結果", ["自動計算", "勝ち", "負け", "引き分け"], key=f"r_{opp}")
                if final_res == "自動計算": final_res = calc_res
            else:
                final_res = cc3.selectbox(f"手動選定", ["勝ち", "負け", "引き分け"], key=f"r_{opp}")
            results[opp] = {"score": o_score, "hc": use_hc, "res": final_res}

        if st.button("🚀 保存（成績とHCを更新）"):
            new_entries = []
            for opp, d in results.items():
                new_entries.append({
                    "日付": play_date.strftime('%Y-%m-%d'), "ゴルフ場": selected_course, "対戦相手": opp,
                    "自分のスコア": my_gross, "相手のスコア": d["score"], "勝敗": d["res"], "ハンディ適用": "あり" if d["hc"] else "なし"
                })
                # HC自動増減ルール (-2 for win, +2 for loss)
                if d["hc"]:
                    if d["res"] == "勝ち": f_df.loc[f_df['名前'] == opp, '持ちハンディ'] -= 2
                    elif d["res"] == "負け": f_df.loc[f_df['名前'] == opp, '持ちハンディ'] += 2
            
            pd.concat([h_df, pd.DataFrame(new_entries)], ignore_index=True).to_csv(HISTORY_FILE, index=False)
            f_df.to_csv(FRIENDS_FILE, index=False)
            st.success("保存完了！")
            st.rerun()

# --- 7. 履歴管理 ---
st.divider()
st.subheader("📊 履歴の確認・修正")
if not h_df.empty:
    edited_h = st.data_editor(h_df, num_rows="dynamic", use_container_width=True)
    if st.button("履歴を更新保存"):
        edited_h.to_csv(HISTORY_FILE, index=False)
        st.success("更新しました")
        st.rerun()
