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
    .match-card {
        background: rgba(255, 255, 255, 0.1) !important;
        border-radius: 15px !important;
        border: 1px solid rgba(255,255,255,0.3) !important;
        padding: 20px !important;
        margin-bottom: 10px !important;
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

# --- 2. データ連携 ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data_safe(sheet_name, default_cols):
    try:
        df = conn.read(worksheet=sheet_name, ttl="1m")
        if df is not None:
            df.columns = [str(c).strip() for c in df.columns]
            return df.dropna(how='all')
    except:
        pass
    return pd.DataFrame(columns=default_cols)

def safe_save(df, sheet_name):
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

# --- 3. 年度別集計 (2026年) ---
current_year = 2026 #
h_df['日付DT'] = pd.to_datetime(h_df['日付'], errors='coerce')
valid_h = h_df.dropna(subset=['日付DT'])
available_years = sorted(valid_h['日付DT'].dt.year.unique().astype(int), reverse=True)
if current_year not in available_years: available_years = [current_year] + available_years
selected_year = st.selectbox("📅 年度別成績を集計", options=available_years, index=0)

friend_names = f_df['名前'].dropna().unique().tolist() if '名前' in f_df.columns else []
if friend_names:
    h_selected = h_df[pd.to_datetime(h_df['日付'], errors='coerce').dt.year == selected_year]
    cols = st.columns(len(friend_names))
    for i, name in enumerate(friend_names):
        with cols[i]:
            row = f_df[f_df['名前'] == name].iloc[0]
            stats = h_selected[h_selected['対戦相手'] == name] if not h_selected.empty else pd.DataFrame()
            w, l = (stats['勝敗']=="勝ち").sum(), (stats['勝敗']=="負け").sum()
            if '写真' in row and pd.notnull(row['写真']) and str(row['写真']).startswith("data:image"):
                st.image(row['写真'], width=120)
            else: st.write("📷 No Photo")
            st.metric(label=f"{name} ({selected_year}年)", value=f"{w}勝 {l}敗", delta=f"HC: {row['持ちハンディ']}")

# --- 4. ラウンド結果の入力フォーム ---
st.divider()
with st.container():
    st.subheader("📝 ラウンド結果を記録する")
    with st.expander("新しい対戦結果を入力する", expanded=False):
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            in_date = st.date_input("日付", date.today())
            c_df['Disp'] = c_df['Name'] + " (" + c_df['City'].fillna('') + ", " + c_df['State'].fillna('') + ")"
            in_course = st.selectbox("コースを選択", options=["-- 選択 --"] + sorted(c_df['Disp'].tolist()))
        with col_m2:
            in_opps = st.multiselect("対戦相手", options=friend_names)
            in_my_score = st.number_input("自分のスコア (Gross)", 60, 150, 90)

        match_results = []
        if in_opps:
            for opp in in_opps:
                st.markdown(f"**vs {opp}**")
                c1, c2, c3 = st.columns(3)
                opp_s = c1.number_input(f"{opp}のスコア", 60, 150, 90, key=f"s_{opp}")
                use_hc = c2.checkbox("HC適用", value=False, key=f"hc_{opp}")
                
                # --- 【重要】自分視点のHC判定ロジック ---
                opp_hc = pd.to_numeric(f_df.loc[f_df['名前'] == opp, '持ちハンディ']).iloc[0] if opp in friend_names else 0
                net_user_score = in_my_score - opp_hc if use_hc else in_my_score
                
                # 自分(ネット) vs 相手(グロス)
                if net_user_score < opp_s: auto_res_idx = 0 # 勝ち
                elif net_user_score > opp_s: auto_res_idx = 1 # 負け
                else: auto_res_idx = 2 # 引き分け
                
                res = c3.selectbox("結果", ["勝ち", "負け", "引き分け"], index=auto_res_idx, key=f"r_{opp}")
                match_results.append({"対戦相手": opp, "相手のスコア": opp_s, "勝敗": res, "ハンディ適用": "あり" if use_hc else "なし", "current_hc": opp_hc})

        if st.button("🚀 対戦結果を保存する"):
            if in_course != "-- 選択 --" and match_results:
                new_entries = []
                updated_f_df = f_df.copy()
                
                for r in match_results:
                    new_entries.append({
                        "日付": in_date.strftime('%Y-%m-%d'), "ゴルフ場": in_course, 
                        "対戦相手": r["対戦相手"], "自分のスコア": in_my_score, 
                        "相手のスコア": r["相手のスコア"], "勝敗": r["勝敗"], "ハンディ適用": r["ハンディ適用"]
                    })
                    
                    # --- 【重要】HC増減幅を「2」に適用 ---
                    if r["ハンディ適用"] == "あり":
                        if r["勝敗"] == "勝ち": # あなたが勝った場合、次回は厳しく
                            new_hc = r["current_hc"] - 2.0
                        elif r["勝敗"] == "負け": # あなたが負けた場合、次回は甘く
                            new_hc = r["current_hc"] + 2.0
                        else:
                            new_hc = r["current_hc"]
                        updated_f_df.loc[updated_f_df['名前'] == r["対戦相手"], '持ちハンディ'] = max(0.0, new_hc)
                
                if safe_save(pd.concat([h_df.drop(columns=['日付DT'], errors='ignore'), pd.DataFrame(new_entries)], ignore_index=True), "history") and safe_save(updated_f_df, "friends"):
                    st.success("対戦結果の保存とHCの更新（±2.0）が完了しました！")
                    st.rerun()

# --- 5. 対戦履歴のタイムライン表示と管理 ---
st.divider()
st.subheader("📊 対戦履歴の確認")
if not h_df.empty:
    sel_opp = st.selectbox("対戦相手でフィルタ", options=["全員"] + friend_names)
    v_df = h_df.copy().sort_values(by="日付", ascending=False)
    if sel_opp != "全員": v_df = v_df[v_df['対戦相手'] == sel_opp]

    # スタイリッシュなカード表示
    for _, r in v_df.head(10).iterrows():
        color = "#ffff00" if r['勝敗'] == "勝ち" else "#ff4b4b" if r['勝敗'] == "負け" else "#ffffff"
        st.markdown(f'<div class="match-card"><small>{r["日付"]}</small><br><b>{r["ゴルフ場"]}</b><br><span style="color: {color}; font-size: 1.5em; font-weight: bold;">{r["勝敗"]}</span> vs <b>{r["対戦相手"]}</b><br>自分: {r["自分のスコア"]} / 相手: {r["相手のスコア"]} (HC {r["ハンディ適用"]})</div>', unsafe_allow_html=True)
    
    # 【復活】過去履歴の直接修正機能
    with st.expander("💾 履歴を直接編集・修正する"):
        st.write("表の中をダブルクリックして値を書き換え、下のボタンで保存してください。")
        edited_h_df = st.data_editor(v_df.drop(columns=['日付DT'], errors='ignore'), use_container_width=True, num_rows="dynamic", key="history_editor")
        if st.button("履歴の修正内容を保存する"):
            if safe_save(edited_h_df, "history"):
                st.success("履歴を更新しました！")
                st.rerun()

# --- 6. システムメンテナンス (友達追加機能を再配置) ---
with st.sidebar:
    st.header("⚙️ システムメンテナンス")
    
    with st.expander("👤 友達を新規追加", expanded=False):
        nf_n = st.text_input("名前 (例: 田中さん)")
        nf_h = st.number_input("初期ハンディキャップ", value=0.0)
        if st.button("友達を保存"):
            if nf_n:
                safe_save(pd.concat([f_df, pd.DataFrame([{"名前":nf_n,"持ちハンディ":nf_h,"写真":""}])], ignore_index=True), "friends")
                st.rerun()

    with st.expander("⛳️ 新しいコースを追加"):
        nc_n = st.text_input("コース名")
        nc_c = st.text_input("City", value="Costa Mesa")
        nc_s = st.text_input("State", value="CA")
        if st.button("コース保存"):
            if nc_n:
                safe_save(pd.concat([c_df, pd.DataFrame([{"Name":nc_n,"City":nc_c,"State":nc_s}])], ignore_index=True), "courses")
                st.rerun()

    with st.expander("📸 写真をアップロード"):
        if friend_names:
            tf = st.selectbox("対象を選択", options=friend_names)
            if (im := st.file_uploader("写真を選択")) and st.button("写真を保存"):
                i = Image.open(im).convert("RGB"); i.thumbnail((150,150)); b = BytesIO(); i.save(b, format="JPEG", quality=60)
                f_df.loc[f_df['名前']==tf,'写真'] = "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()
                safe_save(f_df, "friends"); st.rerun()

    st.divider()
    if st.button("🔄 データを強制更新"):
        st.cache_data.clear()
        st.rerun()
