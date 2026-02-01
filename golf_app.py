import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date
from PIL import Image
import os

# --- デザイン設定 (以前の縁取り・ゴルフ風を維持) ---
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
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(sheet_name):
    return conn.read(worksheet=sheet_name, ttl="0s")

def save_data(df, sheet_name):
    conn.update(worksheet=sheet_name, data=df)
    st.cache_data.clear()

# データの読み込み
f_df = load_data("friends")
h_df = load_data("history")
c_df = load_data("courses")

st.title("⛳️ GOLF BATTLE TRACKER PRO")

# --- サイドバー：メンテナンス ---
with st.sidebar:
    st.header("⚙️ メンテナンス")
    
    # 友達・HC設定の変更
    st.subheader("👥 友達・HC管理")
    edited_f = st.data_editor(f_df, num_rows="dynamic", use_container_width=True, key="f_edit")
    if st.button("友達リストを保存"):
        save_data(edited_f, "friends")
        st.rerun()

    st.divider()
    
    # ゴルフ場追加
    with st.expander("⛳️ 新しいゴルフ場を追加"):
        new_c_name = st.text_input("コース名")
        new_c_city = st.text_input("City")
        if st.button("コースを保存"):
            new_row = pd.DataFrame([{"Name": new_c_name, "City": new_c_city, "State": "CA"}])
            updated_c = pd.concat([c_df, new_row], ignore_index=True)
            save_data(updated_c, "courses")
            st.rerun()

# --- メイン画面：成績表示 ---
if not f_df.empty:
    st.subheader("📈 通算成績")
    cols = st.columns(len(f_df))
    for i, row in f_df.iterrows():
        with cols[i]:
            # 写真表示 (クラウド公開時はURL形式が推奨されます)
            if row['写真']: st.image(row['写真'], width=100)
            
            stats = h_df[h_df['対戦相手'] == row['名前']]
            w, l = (stats['勝敗']=="勝ち").sum(), (stats['勝敗']=="負け").sum()
            st.metric(row['名前'], f"{w}勝 {l}敗", f"HC: {row['持ちハンディ']}")

# --- 入力フォーム ---
st.divider()
with st.expander("📝 ラウンド結果を入力"):
    col1, col2 = st.columns(2)
    with col1:
        play_date = st.date_input("日付", date.today())
        c_df['Display'] = c_df['Name'] + " (" + c_df['City'].fillna('') + ")"
        selected_course = st.selectbox("コースを選択", options=["-- 選択 --"] + sorted(c_df['Display'].tolist()))
    with col2:
        selected_opps = st.multiselect("対戦相手", options=f_df['名前'].tolist())
        my_gross = st.number_input("自分のスコア", 0, 150, 0)

    if selected_opps:
        battle_results = {}
        for opp in selected_opps:
            st.write(f"--- vs {opp} ---")
            cc1, cc2, cc3 = st.columns(3)
            o_gross = cc1.number_input(f"{opp}のスコア", 0, 150, 0, key=f"g_{opp}")
            
            current_h = f_df[f_df['名前'] == opp]['持ちハンディ'].values[0]
            u_hc = cc2.checkbox(f"HC適用 (現在:{current_h})", value=True, key=f"h_{opp}")
            
            # ロジック：自分のスコアからHCを引く
            if my_gross > 0 and o_gross > 0:
                net = my_gross - (current_h if u_hc else 0)
                res = "勝ち" if net < o_gross else ("負け" if net > o_gross else "引き分け")
                final_res = cc3.selectbox(f"判定", ["自動計算", "勝ち", "負け", "引き分け"], key=f"r_{opp}")
                if final_res == "自動計算": final_res = res
            else:
                final_res = cc3.selectbox(f"手動選択", ["勝ち", "負け", "引き分け"], key=f"r_{opp}")
            battle_results[opp] = {"gross": o_gross, "hc": u_hc, "res": final_res}

        if st.button("🚀 保存（自動でHCを変動させます）"):
            new_rows = []
            for opp, d in battle_results.items():
                new_rows.append({"日付": play_date.strftime('%Y-%m-%d'), "ゴルフ場": selected_course, "対戦相手": opp, "自分のスコア": my_gross, "相手のスコア": d["gross"], "勝敗": d["res"], "ハンディ適用": "あり" if d["hc"] else "なし"})
                # HC自動更新
                if d["hc"]:
                    if d["res"] == "勝ち": f_df.loc[f_df['名前'] == opp, '持ちハンディ'] -= 2
                    elif d["res"] == "負け": f_df.loc[f_df['名前'] == opp, '持ちハンディ'] += 2
            
            save_data(pd.concat([h_df, pd.DataFrame(new_rows)], ignore_index=True), "history")
            save_data(f_df, "friends")
            st.success("スプレッドシートへ保存完了！")
            st.rerun()

# --- 履歴管理 ---
st.divider()
st.subheader("📊 履歴の確認・修正")
edited_h = st.data_editor(h_df, num_rows="dynamic", use_container_width=True)
if st.button("履歴をスプレッドシートへ反映"):
    save_data(edited_h, "history")
    st.rerun()
