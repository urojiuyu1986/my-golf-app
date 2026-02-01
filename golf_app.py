import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date
import base64
from io import BytesIO
from PIL import Image

# --- 1. デザイン設定 (視認性重視のプロ仕様) ---
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

# --- 2. データ連携 (Quota 429エラー対策) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data_safe(sheet_name, default_cols):
    try:
        # 【修正】ttlを"0s"から"1m"に変更。
        # 操作のたびにAPIを叩くのを防ぎ、Quota Exceededエラーを回避します。
        df = conn.read(worksheet=sheet_name, ttl="1m")
        if df is not None:
            df.columns = [str(c).strip() for c in df.columns]
            return df.dropna(how='all')
    except Exception as e:
        if "429" in str(e):
            st.warning("Google APIの制限中です。1分ほど待ってから操作してください。")
        pass
    return pd.DataFrame(columns=default_cols)

def safe_save(df, sheet_name):
    try:
        conn.update(worksheet=sheet_name, data=df)
        st.cache_data.clear() # 保存後はキャッシュを消して最新状態にする
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
current_year = 2026
h_df['日付DT'] = pd.to_datetime(h_df['日付'], errors='coerce')
valid_h = h_df.dropna(subset=['日付DT'])
available_years = sorted(valid_h['日付DT'].dt.year.unique().astype(int), reverse=True)
if current_year not in available_years: available_years = [current_year] + available_years

selected_year = st.selectbox("📅 年度別成績を集計", options=available_years, index=0)

# 友達リスト表示
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
        with col2_m2 := col2: # 誤字修正
            in_opps = st.multiselect("対戦相手", options=friend_names)
            in_my_score = st.number_input("自分のスコア (Gross)", 60, 150, 90)

        match_results = []
        if in_opps:
            for opp in in_opps:
                st.markdown(f"**vs {opp}**")
                c1, c2, c3 = st.columns(3)
                opp_s = c1.number_input(f"{opp}のスコア", 60, 150, 90, key=f"s_{opp}")
                use_hc = c2.checkbox("HC適用", value=False, key=f"hc_{opp}")
                res = c3.selectbox("結果", ["勝ち", "負け", "引き分け"], key=f"r_{opp}")
                match_results.append({"対戦相手": opp, "相手のスコア": opp_s, "勝敗": res, "ハンディ適用": "あり" if use_hc else "なし"})

        if st.button("🚀 対戦結果を保存する"):
            if in_course != "-- 選択 --" and match_results:
                new_entries = []
                for r in match_results:
                    new_entries.append({
                        "日付": in_date.strftime('%Y-%m-%d'), "ゴルフ場": in_course, 
                        "対戦相手": r["対戦相手"], "自分のスコア": in_my_score, 
                        "相手のスコア": r["相手のスコア"], "勝敗": r["勝敗"], "ハンディ適用": r["ハンディ適用"]
                    })
                if safe_save(pd.concat([h_df.drop(columns=['日付DT'], errors='ignore'), pd.DataFrame(new_entries)], ignore_index=True), "history"):
                    st.success("保存完了！")
                    st.rerun()

# --- 5. 対戦履歴のタイムライン表示 ---
st.divider()
st.subheader("📊 対戦履歴の確認")
if not h_df.empty:
    sel_opp = st.selectbox("対戦相手でフィルタ", options=["全員"] + friend_names)
    v_df = h_df.copy().sort_values(by="日付", ascending=False)
    if sel_opp != "全員": v_df = v_df[v_df['対戦相手'] == sel_opp]

    for _, r in v_df.head(10).iterrows():
        color = "#ffff00" if r['勝敗'] == "勝ち" else "#ff4b4b" if r['勝敗'] == "負け" else "#ffffff"
        with st.container():
            st.markdown(f"""
            <div class="match-card">
                <span style="font-size: 0.8em; opacity: 0.7;">{r['日付']}</span><br>
                <b style="font-size: 1.2em;">{r['ゴルフ場']}</b><br>
                <span style="color: {color}; font-size: 1.5em; font-weight: bold;">{r['勝敗']}</span> 
                vs <b>{r['対戦相手']}</b><br>
                自分: {r['自分のスコア']} / 相手: {r['相手のスコア']} (HC {r['ハンディ適用']})
            </div>
            """, unsafe_allow_html=True)
    
    with st.expander("表形式で管理（全履歴の修正・削除）"):
        edited = st.data_editor(v_df.drop(columns=['日付DT'], errors='ignore'), use_container_width=True, num_rows="dynamic")
        if st.button("履歴の修正を反映"):
            if safe_save(edited, "history"):
                st.success("更新しました！")
                st.rerun()

# --- 6. システムメンテナンス ---
with st.sidebar:
    st.header("⚙️ システムメンテナンス")
    with st.expander("👤 友達を新規追加", expanded=False):
        new_f_name = st.text_input("名前")
        new_f_hc = st.number_input("ハンディキャップ", value=0.0)
        if st.button("友達を保存"):
            if new_f_name:
                safe_save(pd.concat([f_df, pd.DataFrame([{"名前": new_f_name, "持ちハンディ": new_f_hc, "写真": ""}])], ignore_index=True), "friends")
                st.rerun()

    with st.expander("⛳️ 新しいコースを追加", expanded=False):
        nc_name = st.text_input("コース名")
        nc_city = st.text_input("City", value="Costa Mesa")
        nc_state = st.text_input("State", value="CA")
        if st.button("コース保存"):
            if nc_name:
                safe_save(pd.concat([c_df, pd.DataFrame([{"Name":nc_name,"City":nc_city,"State":nc_state}])], ignore_index=True), "courses")
                st.rerun()

    with st.expander("📸 写真をアップロード", expanded=False):
        if friend_names:
            t_f = st.selectbox("対象の友達", options=friend_names, key="side_photo")
            img_f = st.file_uploader("画像を選択", type=['png','jpg','jpeg'])
            if img_f and st.button(f"{t_f}さんの写真を保存"):
                img = Image.open(img_f).convert("RGB")
                img.thumbnail((150, 150))
                buf = BytesIO()
                img.save(buf, format="JPEG", quality=60)
                img_b64 = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
                f_df.loc[f_df['名前'] == t_f, '写真'] = img_b64
                if safe_save(f_df, "friends"): st.rerun()
    
    st.divider()
    if st.button("🔄 データを強制更新"):
        st.cache_data.clear()
        st.rerun()
