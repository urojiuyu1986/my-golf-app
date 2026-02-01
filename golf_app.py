import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date
import base64
from io import BytesIO
from PIL import Image

# --- 1. キラキラ・ゴージャスデザイン設定 ---
st.set_page_config(page_title="YUJI'S GOLF BATTLE TRACKER", page_icon="💎", layout="wide")

st.markdown("""
    <style>
    /* 全体の背景：深緑からゴールドへのグラデーション */
    .stApp { 
        background: linear-gradient(135deg, #1e5631 0%, #0c331a 50%, #b8860b 100%); 
    }
    
    /* テキストスタイル：白抜き・強いシャドウで視認性アップ */
    h1, h2, h3, p, label, .stMarkdown, .stSelectbox label, .stMultiSelect label, .stNumberInput label {
        color: #ffffff !important;
        text-shadow: 2px 2px 4px #000, 0px 0px 10px #ffd700 !important;
        font-weight: 900 !important;
    }

    /* カードデザイン：ガラスのような質感にゴールドの縁取り */
    .match-card {
        background: rgba(255, 255, 255, 0.15) !important;
        border-radius: 20px !important;
        border: 2px solid #ffd700 !important;
        padding: 25px !important;
        margin-bottom: 15px !important;
        box-shadow: 0 4px 15px rgba(255, 215, 0, 0.3) !important;
    }

    /* コンテナ・フォーム：高級感のあるスタイル */
    div[data-testid="stExpander"], .stForm, div[data-testid="metric-container"] {
        background-color: rgba(255, 255, 255, 0.1) !important;
        border: 2px solid #ffd700 !important;
        border-radius: 20px !important;
        padding: 15px !important;
        box-shadow: inset 0 0 10px rgba(255,215,0,0.2);
    }

    /* メトリック（勝敗数）：ネオンイエロー */
    div[data-testid="stMetricValue"] { 
        color: #ffff00 !important; 
        text-shadow: 0 0 10px #ffd700, 2px 2px 2px #000 !important;
        font-size: 2.5rem !important;
    }

    /* サイドバー：ダークグリーン */
    section[data-testid="stSidebar"] { 
        background-color: #051a0d !important; 
        border-right: 2px solid #ffd700;
    }
    
    /* ボタン：ゴールドグラデーション */
    .stButton>button {
        background: linear-gradient(90deg, #ffd700, #ff8c00) !important;
        color: black !important;
        font-weight: bold !important;
        border-radius: 10px !important;
        border: none !important;
        box-shadow: 0 4px 8px rgba(0,0,0,0.3) !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. データ連携 ---
conn = st.connection("gsheets", type=GSheetsConnection)

if 'submission_id' not in st.session_state:
    st.session_state.submission_id = 0

def load_data_safe(sheet_name, default_cols):
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        if df is not None:
            df.columns = [str(c).strip() for c in df.columns]
            for col in df.columns:
                if df[col].dtype == 'object':
                    df[col] = df[col].astype(str).str.strip()
            for col in default_cols:
                if col not in df.columns: df[col] = None
            return df.dropna(how='all')
    except: pass
    return pd.DataFrame(columns=default_cols)

def safe_save(df, sheet_name):
    try:
        conn.update(worksheet=sheet_name, data=df)
        st.cache_data.clear() 
        return True
    except Exception as e:
        st.error(f"❌ 保存失敗: {e}")
        return False

# データロード
f_df = load_data_safe("friends", ['名前', '持ちハンディ', '写真'])
h_df = load_data_safe("history", ['日付', 'ゴルフ場', '対戦相手', '自分のスコア', '相手のスコア', '勝敗', 'ハンディ適用'])
c_df = load_data_safe("courses", ['Name', 'City', 'State'])

# --- タイトル ---
st.title("🏆 YUJI'S GOLF BATTLE TRACKER 💎✨")
st.markdown("### 🌟 Welcome back, Yuji! Let's conquer the course today! ⛳️🔥")

# --- 3. 年度別エグゼクティブ集計 ---
current_year = 2026 
h_df['Year'] = pd.to_datetime(h_df['日付'], errors='coerce').dt.year
h_df.loc[h_df['Year'].isna(), 'Year'] = h_df['日付'].astype(str).apply(lambda x: int(x[:4]) if x[:4].isdigit() else None)

available_years = sorted(h_df['Year'].dropna().unique().astype(int), reverse=True)
if current_year not in available_years: available_years = [current_year] + available_years
selected_year = st.selectbox("📅 成績を表示するシーズンを選択 ✨", options=available_years, index=available_years.index(current_year) if current_year in available_years else 0)

friend_names = f_df['名前'].dropna().unique().tolist() if '名前' in f_df.columns else []

if friend_names:
    h_selected = h_df[h_df['Year'] == selected_year]
    cols = st.columns(len(friend_names))
    for i, name in enumerate(friend_names):
        with cols[i]:
            row = f_df[f_df['名前'] == name].iloc[0]
            stats = h_selected[h_selected['対戦相手'] == name] if not h_selected.empty else pd.DataFrame()
            w = (stats['勝敗'] == "勝ち").sum()
            l = (stats['勝敗'] == "負け").sum()
            
            if '写真' in row and pd.notnull(row['写真']) and str(row['写真']).startswith("data:image"):
                st.image(row['写真'], width=150)
            else: st.write("📸 No Photo")
            st.metric(label=f"👑 {name} ({selected_year}年)", value=f"{w}勝 {l}敗", delta=f"HC: {row['持ちハンディ']}")

# --- 4. ラウンド結果のプレミアム入力フォーム ---
st.divider()
with st.container():
    st.subheader("📝 本日の栄光を記録する 🥂")
    form_key = f"form_{st.session_state.submission_id}"
    with st.expander("✨ 新しい対戦結果を入力する ✨", expanded=False):
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            in_date = st.date_input("🗓 ラウンド日", date.today(), key=f"date_{form_key}")
            c_df['Disp'] = c_df['Name'] + " (" + c_df['City'].fillna('') + ", " + c_df['State'].fillna('') + ")"
            in_course = st.selectbox("⛳️ コースを選択", options=["-- 選択 --"] + sorted(c_df['Disp'].tolist()), key=f"course_{form_key}")
        with col_m2:
            in_opps = st.multiselect("🤝 対戦相手", options=friend_names, default=[], key=f"opps_{form_key}")
            in_my_score = st.number_input("🏌️‍♂️ 自分のスコア (Gross)", 60, 150, value=None, placeholder="スコアを入力...", key=f"my_score_{form_key}")

        match_results = []
        if in_opps:
            for opp in in_opps:
                st.markdown(f"#### ⚔️ VS {opp}")
                c1, c2, c3 = st.columns(3)
                opp_s = c1.number_input(f"🔢 {opp}のスコア", 0, 150, 0, key=f"s_{opp}_{form_key}")
                use_hc = c2.checkbox("⚖️ HCを適用する", value=False, key=f"hc_{opp}_{form_key}")
                
                opp_hc_raw = f_df.loc[f_df['名前'] == opp, '持ちハンディ'].iloc[0] if opp in friend_names else 0
                opp_hc = pd.to_numeric(opp_hc_raw, errors='coerce') if pd.notnull(opp_hc_raw) else 0
                
                net_user_score = (in_my_score - opp_hc) if (use_hc and in_my_score is not None) else in_my_score
                
                auto_res_idx = 0
                if opp_s > 0 and in_my_score is not None:
                    if net_user_score < opp_s: auto_res_idx = 0 
                    elif net_user_score > opp_s: auto_res_idx = 1
                    else: auto_res_idx = 2
                
                res = c3.selectbox("🏁 最終結果", ["勝ち", "負け", "引き分け"], index=auto_res_idx, key=f"r_{opp}_{form_key}")
                match_results.append({"対戦相手": opp, "相手のスコア": opp_s if opp_s > 0 else "-", "勝敗": res, "ハンディ適用": "あり" if use_hc else "なし", "current_hc": opp_hc})

        if st.button("🚀 この対戦結果を永久保存する ✨"):
            if in_course != "-- 選択 --" and in_opps and in_my_score is not None:
                new_entries = []
                updated_f_df = f_df.copy()
                for r in match_results:
                    new_entries.append({
                        "日付": in_date.strftime('%Y-%m-%d'), "ゴルフ場": in_course, "対戦相手": r["対戦相手"], 
                        "自分のスコア": in_my_score, "相手のスコア": r["相手のスコア"], "勝敗": r["勝敗"], "ハンディ適用": r["ハンディ適用"]
                    })
                    if r["ハンディ適用"] == "あり":
                        if r["勝敗"] == "勝ち": new_hc = r["current_hc"] - 2.0
                        elif r["勝敗"] == "負け": new_hc = r["current_hc"] + 2.0
                        else: new_hc = r["current_hc"]
                        updated_f_df.loc[updated_f_df['名前'] == r["対戦相手"], '持ちハンディ'] = max(0.0, float(new_hc))
                
                if safe_save(pd.concat([h_df.drop(columns=['Year'], errors='ignore'), pd.DataFrame(new_entries)], ignore_index=True), "history") and safe_save(updated_f_df, "friends"):
                    st.session_state.submission_id += 1 
                    st.balloons() # お祝いのアニメーション
                    st.success("🎉 保存完了！Yuji、ナイスプレー！")
                    st.rerun()

# --- 5. ヒストリー・ギャラリー ---
st.divider()
st.subheader("📊 伝説の対戦履歴 🏅")
if not h_df.empty:
    sel_opp = st.selectbox("🔍 相手で絞り込む", options=["全員"] + friend_names)
    display_h = h_df.copy()
    display_h['日付表示'] = pd.to_datetime(display_h['日付'], errors='coerce').dt.strftime('%Y-%m-%d').fillna(display_h['日付'])
    display_h = display_h.sort_values(by="日付", ascending=False)
    
    if sel_opp != "全員": display_h = display_h[display_h['対戦相手'] == sel_opp]

    for _, r in display_h.head(5).iterrows():
        color = "#ffff00" if r['勝敗'] == "勝ち" else "#ff4b4b" if r['勝敗'] == "負け" else "#ffffff"
        st.markdown(f'<div class="match-card"><small>📅 {r["日付表示"]}</small><br>⛳️ <b>{r["ゴルフ場"]}</b><br><span style="color: {color}; font-size: 1.8em; font-weight: bold;">{r["勝敗"]}</span> vs 👑 <b>{r["対戦相手"]}</b><br>自分: {r["自分のスコア"]} / 相手: {r["相手のスコア"]} (HC {r["ハンディ適用"]})</div>', unsafe_allow_html=True)
    
    with st.expander("🛠 履歴を管理・修正する (管理者モード)"):
        original_h = h_df.copy().drop(columns=['Year'], errors='ignore')
        edited_h_df = st.data_editor(original_h, use_container_width=True, num_rows="dynamic", key="h_editor_main")
        
        if st.button("💾 変更をスプレッドシートに反映"):
            updated_f_df = f_df.copy()
            for _, old_r in original_h.iterrows():
                is_deleted = True
                for _, new_r in edited_h_df.iterrows():
                    if all(old_r.astype(str) == new_r.astype(str)): 
                        is_deleted = False
                        break
                
                if is_deleted and old_r['ハンディ適用'] == "あり":
                    opp_name = old_r['対戦相手']
                    if opp_name in updated_f_df['名前'].values:
                        curr_hc = pd.to_numeric(updated_f_df.loc[updated_f_df['名前'] == opp_name, '持ちハンディ']).iloc[0]
                        if old_r['勝敗'] == "勝ち": new_hc = curr_hc + 2.0
                        elif old_r['勝敗'] == "負け": new_hc = max(0.0, curr_hc - 2.0)
                        else: new_hc = curr_hc
                        updated_f_df.loc[updated_f_df['名前'] == opp_name, '持ちハンディ'] = new_hc

            if safe_save(edited_h_df, "history") and safe_save(updated_f_df, "friends"):
                st.success("🔄 データの同期が完了しました！")
                st.rerun()

# --- 6. メンテナンス（サイドバー） ---
with st.sidebar:
    st.header("⚙️ SYSTEM SETTINGS")
    
    with st.expander("👤 友達を新規追加 🆕"):
        nf = st.text_input("名前", key="side_new_name")
        nh = st.number_input("初期HC", value=0.0, key="side_new_hc")
        new_photo_file = st.file_uploader("📸 写真を撮る/選ぶ (Option)", type=['png', 'jpg', 'jpeg'], key="side_new_photo")
        
        if st.button("💎 友達として登録"):
            if nf:
                photo_b64 = ""
                if new_photo_file:
                    img = Image.open(new_photo_file).convert("RGB")
                    img.thumbnail((150,150))
                    buffer = BytesIO()
                    img.save(buffer, format="JPEG", quality=60)
                    photo_b64 = "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode()
                
                new_friend = pd.DataFrame([{"名前": nf, "持ちハンディ": nh, "写真": photo_b64}])
                if safe_save(pd.concat([f_df, new_friend], ignore_index=True), "friends"):
                    st.rerun()

    with st.expander("⛳️ ゴルフコースを追加 🗺"):
        nc_n = st.text_input("コース名", key="side_c_name")
        nc_c = st.text_input("City", value="Costa Mesa", key="side_c_city")
        nc_s = st.text_input("State", value="CA", key="side_c_state")
        if st.button("📍 コースを登録"):
            if nc_n: safe_save(pd.concat([c_df, pd.DataFrame([{"Name":nc_n,"City":nc_c,"State":nc_s}])], ignore_index=True), "courses"); st.rerun()
    
    with st.expander("📸 既存の写真をアップデート"):
        if friend_names:
            tf = st.selectbox("対象者を選択", options=friend_names, key="side_p_target")
            if (im := st.file_uploader("新しい写真を選択")) and st.button("🖼 写真を更新"):
                i = Image.open(im).convert("RGB"); i.thumbnail((150,150)); b = BytesIO(); i.save(b, format="JPEG", quality=60)
                f_df.loc[f_df['名前']==tf,'写真'] = "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()
                safe_save(f_df, "friends"); st.rerun()
    
    st.divider()
    st.button("🔄 最新データに同期", on_click=lambda: st.cache_data.clear())
    st.caption("Produced for Yuji ✨")
