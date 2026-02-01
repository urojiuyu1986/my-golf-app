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
    if os.path.exists(FRIENDS_FILE):
        f_df = pd.read_csv(FRIENDS_FILE)
        if '写真' not in f_df.columns: f_df['写真'] = ""
    else:
        # 初期の友達リスト
        f_df = pd.DataFrame(columns=['名前', '持ちハンディ', '写真'])
    
    h_df = pd.read_csv(HISTORY_FILE) if os.path.exists(HISTORY_FILE) else pd.DataFrame(columns=['日付', 'ゴルフ場', '対戦相手', '自分のスコア', '相手のスコア', '勝敗', 'ハンディ適用'])
    if not h_df.empty:
        h_df['日付'] = pd.to_datetime(h_df['日付'], errors='coerce', format='mixed').dt.strftime('%Y-%m-%d')
        h_df = h_df.dropna(subset=['日付']).sort_values(by='日付', ascending=False)

    if os.path.exists(COURSES_FILE):
        c_df = pd.read_csv(COURSES_FILE)
    else:
        # あなたの活動拠点であるCosta Mesa/Irvine周辺のコースをプリセット
        data = [
            {"Name": "Costa Mesa CC (Los Lagos)", "City": "Costa Mesa", "State": "CA"},
            {"Name": "Costa Mesa CC (Mesa Linda)", "City": "Costa Mesa", "State": "CA"},
            {"Name": "Oak Creek GC", "City": "Irvine", "State": "CA"},
            {"Name": "Strawberry Farms GC", "City": "Irvine", "State": "CA"},
            {"Name": "Pelican Hill GC", "City": "Newport Coast", "State": "CA"}
        ]
        c_df = pd.DataFrame(data)
        c_df.to_csv(COURSES_FILE, index=False)
    return f_df, h_df, c_df

f_df, h_df, c_df = init_data()

# --- 3. 視認性重視のデザイン (CSS) ---
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
    section[data-testid="stSidebar"] { background-color: #0c331a !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("⛳️ GOLF BATTLE TRACKER PRO")

# --- 4. サイドバー：各種メンテナンス ---
with st.sidebar:
    st.header("⚙️ メンテナンス・設定")
    
    # 【機能1】友達の新規登録と初期HC設定
    with st.expander("👤 友達を新規登録"):
        new_f_name = st.text_input("名前")
        new_f_hc = st.number_input("初期ハンディ (自分から引く点数)", value=0)
        if st.button("友達を登録"):
            if new_f_name:
                new_f = pd.DataFrame([{"名前": new_f_name, "持ちハンディ": new_f_hc, "写真": ""}])
                f_df = pd.concat([f_df, new_f], ignore_index=True)
                f_df.to_csv(FRIENDS_FILE, index=False)
                st.success(f"{new_f_name}を登録しました！")
                st.rerun()

    st.divider()

    # 【機能2】HCの途中変更（データエディタで直接編集）
    if not f_df.empty:
        st.subheader("👥 友達・HCリストの修正")
        st.write("名前やハンディを直接書き換えて保存できます。")
        edited_f = st.data_editor(f_df[['名前', '持ちハンディ']], num_rows="dynamic", use_container_width=True, key="f_edit_main")
        if st.button("友達・HC情報を更新保存"):
            # 写真データと合体させて保存
            edited_f['写真'] = f_df['写真'] 
            edited_f.to_csv(FRIENDS_FILE, index=False)
            st.success("設定を更新しました！")
            st.rerun()

    st.divider()

    # ゴルフ場追加
    with st.expander("⛳️ ゴルフ場を追加"):
        new_c_name = st.text_input("コース名")
        new_c_city = st.text_input("City")
        if st.button("コース登録"):
            if new_c_name:
                new_course = pd.DataFrame([{"Name": new_c_name, "City": new_c_city, "State": "CA"}])
                c_df = pd.concat([c_df, new_course], ignore_index=True)
                c_df.to_csv(COURSES_FILE, index=False)
                st.rerun()

    # 写真更新
    if not f_df.empty:
        st.subheader("📷 写真の更新")
        target_f = st.selectbox("友達を選択", options=f_df['名前'].tolist(), key="pic_sel")
        uploaded_pic = st.file_uploader("写真を選択", type=['png', 'jpg', 'jpeg'], key="pic_up")
        if st.button("写真を保存"):
            if uploaded_pic:
                p_path = os.path.join(PHOTO_DIR, f"{target_f}.png")
                Image.open(uploaded_pic).save(p_path)
                f_df.loc[f_df['名前'] == target_f, '写真'] = p_path
                f_df.to_csv(FRIENDS_FILE, index=False)
                st.rerun()

# --- 5. メイン：成績表示 ---
if not f_df.empty:
    st.subheader("📈 通算成績")
    cols = st.columns(len(f_df))
    for i, row in f_df.iterrows():
        with cols[i]:
            pic = row['写真']
            if pic and os.path.exists(str(pic)): st.image(pic, width=120)
            else: st.write("📷 No Photo")
            
            stats = h_df[h_df['対戦相手'] == row['名前']]
            w, l = (stats['勝敗']=="勝ち").sum(), (stats['勝敗']=="負け").sum()
            st.metric(row['名前'], f"{w}勝 {l}敗", f"現在HC: {row['持ちハンディ']}")

# --- 6. ラウンド結果入力 ---
st.divider()
with st.expander("📝 ラウンド結果を記録する", expanded=False):
    c1, c2 = st.columns(2)
    with c1:
        play_date = st.date_input("日付", date.today())
        c_df['Display'] = c_df['Name'] + " (" + c_df['City'].fillna('') + ")"
        selected_course = st.selectbox("コースを選択", options=["-- 選択 --"] + sorted(c_df['Display'].tolist()))
    with c2:
        selected_opps = st.multiselect("対戦相手", options=f_df['名前'].tolist())
        my_gross = st.number_input("自分のスコア", 0, 150, 0)

    if selected_opps:
        battle_results = {}
        for opp in selected_opps:
            st.write(f"--- vs {opp} ---")
            cc1, cc2, cc3 = st.columns(3)
            o_gross = cc1.number_input(f"{opp}のスコア", 0, 150, 0, key=f"g_{opp}")
            
            # 最新のハンディを反映
            current_h = f_df[f_df['名前'] == opp]['持ちハンディ'].values[0]
            u_hc = cc2.checkbox(f"HC適用 (現在:{current_h})", value=True, key=f"h_{opp}")
            
            if my_gross > 0 and o_gross > 0:
                net = my_gross - (current_h if u_hc else 0)
                res = "勝ち" if net < o_gross else ("負け" if net > o_gross else "引き分け")
                final_res = cc3.selectbox(f"判定", ["自動計算", "勝ち", "負け", "引き分け"], key=f"r_{opp}")
                if final_res == "自動計算": final_res = res
            else:
                final_res = cc3.selectbox(f"手動選定", ["勝ち", "負け", "引き分け"], key=f"r_{opp}")
            battle_results[opp] = {"gross": o_gross, "hc": u_hc, "res": final_res}

        if st.button("🚀 保存（HC更新）"):
            new_h_list = []
            for opp, d in battle_results.items():
                new_h_list.append({"日付": play_date.strftime('%Y-%m-%d'), "ゴルフ場": selected_course, "対戦相手": opp, "自分のスコア": my_gross, "相手のスコア": d["gross"], "勝敗": d["res"], "ハンディ適用": "あり" if d["hc"] else "なし"})
                # 勝ったら-2、負けたら+2の自動更新
                if d["hc"]:
                    if d["res"] == "勝ち": f_df.loc[f_df['名前'] == opp, '持ちハンディ'] -= 2
                    elif d["res"] == "負け": f_df.loc[f_df['名前'] == opp, '持ちハンディ'] += 2
            
            pd.concat([h_df, pd.DataFrame(new_h_list)], ignore_index=True).to_csv(HISTORY_FILE, index=False)
            f_df.to_csv(FRIENDS_FILE, index=False)
            st.success("保存完了しました！")
            st.rerun()

# --- 7. 履歴管理 ---
st.divider()
st.subheader("📊 履歴の管理")
if not h_df.empty:
    edited_h = st.data_editor(h_df, num_rows="dynamic", use_container_width=True)
    if st.button("履歴を更新"):
        edited_h.to_csv(HISTORY_FILE, index=False)
        st.rerun()