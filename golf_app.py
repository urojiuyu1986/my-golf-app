import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date
import base64
from io import BytesIO
from PIL import Image

# --- 1. DESIGN & LAYOUT ---
st.set_page_config(page_title="YUJI'S GOLF BATTLE TRACKER", page_icon="💎", layout="wide")

st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #1e5631 0%, #0c331a 50%, #b8860b 100%); }
    h1, h2, h3, p, label, .stMarkdown, .stSelectbox label, .stMultiSelect label, .stNumberInput label {
        color: #ffffff !important;
        text-shadow: 2px 2px 4px #000, 0px 0px 10px #ffd700 !important;
        font-weight: 900 !important;
    }
    .match-card {
        background: rgba(255, 255, 255, 0.15) !important;
        border-radius: 20px !important;
        border: 2px solid #ffd700 !important;
        padding: 25px !important;
        margin-bottom: 15px !important;
        box-shadow: 0 4px 15px rgba(255, 215, 0, 0.3) !important;
    }
    div[data-testid="stExpander"], .stForm, div[data-testid="metric-container"] {
        background-color: rgba(255, 255, 255, 0.1) !important;
        border: 2px solid #ffd700 !important;
        border-radius: 20px !important;
        padding: 15px !important;
    }
    div[data-testid="stMetricValue"] { 
        color: #ffff00 !important; 
        text-shadow: 0 0 10px #ffd700, 2px 2px 2px #000 !important;
        font-size: 2.5rem !important;
    }
    section[data-testid="stSidebar"] { background-color: #051a0d !important; border-right: 2px solid #ffd700; }
    .stButton>button {
        background: linear-gradient(90deg, #ffd700, #ff8c00) !important;
        color: black !important;
        font-weight: bold !important;
        border-radius: 10px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA CONNECTION ---
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
        st.error(f"❌ Save Failed: {e}")
        return False

# Localization Maps
res_map = {"勝ち": "Win", "負け": "Loss", "引き分け": "Draw", "Win": "Win", "Loss": "Loss", "Draw": "Draw"}
hc_map = {"あり": "Applied", "なし": "None", "Yes": "Applied", "No": "None"}

# Load Data
f_df = load_data_safe("friends", ['名前', '持ちハンディ', '写真'])
h_df = load_data_safe("history", ['日付', 'ゴルフ場', '対戦相手', '自分のスコア', '相手のスコア', '勝敗', 'ハンディ適用'])
c_df = load_data_safe("courses", ['Name', 'City', 'State'])

# --- 3. HERO SECTION (YUJI'S PROFILE) ---
st.title("🏆 YUJI'S GOLF BATTLE TRACKER 💎✨")

# Search for Yuji in friends list
yuji_row = f_df[f_df['名前'].str.contains("Yuji|ユウジ", case=False, na=False)]
col_h1, col_h2 = st.columns([1, 4])

with col_h1:
    if not yuji_row.empty and pd.notnull(yuji_row.iloc[0]['写真']) and str(yuji_row.iloc[0]['写真']).startswith("data:image"):
        st.image(yuji_row.iloc[0]['写真'], caption="THE CHAMP: YUJI", width=200)
    else:
        st.info("💡 Tip: Add 'Yuji' in the sidebar with your photo to show it here!")

with col_h2:
    st.markdown(f"### 🌟 Welcome back, Yuji! Ready to dominate the green? ⛳️🔥")
    current_year = 2026
    h_df['Year'] = pd.to_datetime(h_df['日付'], errors='coerce').dt.year
    h_selected = h_df[h_df['Year'] == current_year]
    total_wins = (h_selected['勝敗'].isin(["Win", "勝ち"])).sum()
    total_losses = (h_selected['勝敗'].isin(["Loss", "負け"])).sum()
    st.metric(label=f"{current_year} Season Overall Record", value=f"{total_wins}W {total_losses}L")

# --- 4. SEASONAL STATS (FRIENDS) ---
st.divider()
available_years = sorted(h_df['Year'].dropna().unique().astype(int), reverse=True)
if current_year not in available_years: available_years = [current_year] + available_years
selected_year = st.selectbox("📅 Select Season ✨", options=available_years, index=available_years.index(current_year) if current_year in available_years else 0)

friend_names = f_df['名前'].dropna().unique().tolist() if '名前' in f_df.columns else []
friend_names_without_yuji = [n for n in friend_names if "Yuji" not in n]

if friend_names_without_yuji:
    h_selected_year = h_df[h_df['Year'] == selected_year]
    cols = st.columns(len(friend_names_without_yuji))
    for i, name in enumerate(friend_names_without_yuji):
        with cols[i]:
            row = f_df[f_df['名前'] == name].iloc[0]
            stats = h_selected_year[h_selected_year['対戦相手'] == name] if not h_selected_year.empty else pd.DataFrame()
            w = (stats['勝敗'].isin(["Win", "勝ち"])).sum()
            l = (stats['勝敗'].isin(["Loss", "負け"])).sum()
            
            if '写真' in row and pd.notnull(row['写真']) and str(row['写真']).startswith("data:image"):
                st.image(row['写真'], width=120)
            else: st.write("📸 No Photo")
            st.metric(label=f"vs {name}", value=f"{w}W {l}L", delta=f"HC: {row['持ちハンディ']}")

# --- 5. RECORD NEW ROUND ---
st.divider()
with st.container():
    st.subheader("📝 Record Match Results 🥂")
    form_key = f"form_{st.session_state.submission_id}"
    with st.expander("✨ Enter New Match ✨", expanded=False):
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            in_date = st.date_input("🗓 Date", date.today(), key=f"date_{form_key}")
            # Dynamic course display
            c_df['Disp'] = c_df['Name'] + " (" + c_df['City'].fillna('') + ", " + c_df['State'].fillna('') + ")"
            in_course = st.selectbox("⛳️ Select Course", options=["-- Select --"] + sorted(c_df['Disp'].tolist()), key=f"course_{form_key}")
        with col_m2:
            in_opps = st.multiselect("🤝 Opponents", options=friend_names_without_yuji, default=[], key=f"opps_{form_key}")
            in_my_score = st.number_input("🏌️‍♂️ My Gross Score", 60, 150, value=None, placeholder="Enter score...", key=f"my_score_{form_key}")

        match_results = []
        if in_opps:
            for opp in in_opps:
                st.markdown(f"#### ⚔️ VS {opp}")
                c1, c2, c3 = st.columns(3)
                opp_s = c1.number_input(f"🔢 {opp}'s Score", 0, 150, 0, key=f"s_{opp}_{form_key}")
                use_hc = c2.checkbox("⚖️ Apply HC", value=False, key=f"hc_{opp}_{form_key}")
                
                opp_hc_raw = f_df.loc[f_df['名前'] == opp, '持ちハンディ'].iloc[0] if opp in friend_names else 0
                opp_hc = pd.to_numeric(opp_hc_raw, errors='coerce') if pd.notnull(opp_hc_raw) else 0
                net_user_score = (in_my_score - opp_hc) if (use_hc and in_my_score is not None) else in_my_score
                
                auto_res_idx = 0 
                if opp_s > 0 and in_my_score is not None:
                    if net_user_score < opp_s: auto_res_idx = 0 
                    elif net_user_score > opp_s: auto_res_idx = 1
                    else: auto_res_idx = 2
                
                res = c3.selectbox("🏁 Result", ["Win", "Loss", "Draw"], index=auto_res_idx, key=f"r_{opp}_{form_key}")
                match_results.append({"Opponent": opp, "Opp Score": opp_s if opp_s > 0 else "-", "Result": res, "HC Applied": "Yes" if use_hc else "No", "current_hc": opp_hc})

        if st.button("🚀 Save Match to History ✨"):
            if in_course != "-- Select --" and in_opps and in_my_score is not None:
                new_entries = []
                updated_f_df = f_df.copy()
                for r in match_results:
                    new_entries.append({
                        "日付": in_date.strftime('%Y-%m-%d'), "ゴルフ場": in_course, "対戦相手": r["Opponent"], 
                        "自分のスコア": in_my_score, "相手のスコア": r["Opp Score"], "勝敗": r["Result"], "ハンディ適用": r["HC Applied"]
                    })
                    if r["HC Applied"] == "Yes":
                        if r["Result"] == "Win": new_hc = r["current_hc"] - 2.0
                        elif r["Result"] == "Loss": new_hc = r["current_hc"] + 2.0
                        else: new_hc = r["current_hc"]
                        updated_f_df.loc[updated_f_df['名前'] == r["Opponent"], '持ちハンディ'] = max(0.0, float(new_hc))
                
                if safe_save(pd.concat([h_df.drop(columns=['Year'], errors='ignore'), pd.DataFrame(new_entries)], ignore_index=True), "history") and safe_save(updated_f_df, "friends"):
                    st.session_state.submission_id += 1 
                    st.balloons()
                    st.success("🎉 Match Saved! Excellent round, Yuji!")
                    st.rerun()

# --- 6. MATCH HISTORY & ADMIN EDIT ---
st.divider()
st.subheader("📊 Legendary History 🏅")
if not h_df.empty:
    sel_opp = st.selectbox("🔍 Filter by Opponent", options=["All"] + friend_names_without_yuji)
    display_h = h_df.copy()
    display_h['DateStr'] = pd.to_datetime(display_h['日付'], errors='coerce').dt.strftime('%Y-%m-%d').fillna(display_h['日付'])
    display_h = display_h.sort_values(by="日付", ascending=False)
    
    if sel_opp != "All": display_h = display_h[display_h['対戦相手'] == sel_opp]

    for _, r in display_h.head(5).iterrows():
        clean_res = res_map.get(r['勝敗'], r['勝敗'])
        clean_hc = hc_map.get(r['ハンディ適用'], r['ハンディ適用'])
        color = "#ffff00" if clean_res == "Win" else "#ff4b4b" if clean_res == "Loss" else "#ffffff"
        st.markdown(f'<div class="match-card"><small>📅 {r["DateStr"]}</small><br>⛳️ <b>{r["ゴルフ場"]}</b><br><span style="color: {color}; font-size: 1.8em; font-weight: bold;">{clean_res}</span> vs 👑 <b>{r["対戦相手"]}</b><br>Me: {r["自分のスコア"]} / Opp: {r["相手のスコア"]} (HC: {clean_hc})</div>', unsafe_allow_html=True)
    
    with st.expander("🛠 Admin Mode: Edit History (Handicap Sync Enabled)"):
        st.warning("Deletions here will automatically restore the opponent's Handicap.")
        original_h = h_df.copy().drop(columns=['Year'], errors='ignore')
        edited_h_df = st.data_editor(original_h, use_container_width=True, num_rows="dynamic", key="h_editor_main")
        
        if st.button("💾 Sync Changes"):
            updated_f_df = f_df.copy()
            for _, old_r in original_h.iterrows():
                is_deleted = True
                for _, new_r in edited_h_df.iterrows():
                    if all(old_r.astype(str) == new_r.astype(str)): 
                        is_deleted = False
                        break
                
                if is_deleted and old_r['ハンディ適用'] in ["Yes", "Applied"]:
                    opp_name = old_r['対戦相手']
                    if opp_name in updated_f_df['名前'].values:
                        curr_hc = pd.to_numeric(updated_f_df.loc[updated_f_df['名前'] == opp_name, '持ちハンディ']).iloc[0]
                        if old_r['勝敗'] in ["Win"]: new_hc = curr_hc + 2.0
                        elif old_r['勝敗'] in ["Loss"]: new_hc = max(0.0, curr_hc - 2.0)
                        else: new_hc = curr_hc
                        updated_f_df.loc[updated_f_df['名前'] == opp_name, '持ちハンディ'] = new_hc

            if safe_save(edited_h_df, "history") and safe_save(updated_f_df, "friends"):
                st.success("🔄 Sync Completed!")
                st.rerun()

# --- 7. MAINTENANCE (SIDEBAR) ---
with st.sidebar:
    st.header("⚙️ MAINTENANCE")
    
    # Restored: Specialized photo update for existing friends
    with st.expander("📸 Update Friend Photo"):
        if friend_names:
            target_friend = st.selectbox("Select Friend", options=friend_names, key="side_p_target")
            new_img = st.file_uploader("Upload New Image", type=['png', 'jpg', 'jpeg'], key="side_p_upload")
            if st.button("🖼 Refresh Photo"):
                if new_img:
                    i = Image.open(new_img).convert("RGB")
                    i.thumbnail((200,200))
                    b = BytesIO()
                    i.save(b, format="JPEG", quality=75)
                    photo_data = "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()
                    f_df.loc[f_df['名前'] == target_friend, '写真'] = photo_data
                    safe_save(f_df, "friends")
                    st.rerun()

    with st.expander("👤 Add New Friend"):
        nf = st.text_input("Name", key="side_new_name")
        nh = st.number_input("Initial HC", value=0.0, key="side_new_hc")
        if st.button("💎 Register Friend"):
            if nf:
                new_friend = pd.DataFrame([{"名前": nf, "持ちハンディ": nh, "写真": ""}])
                safe_save(pd.concat([f_df, new_friend], ignore_index=True), "friends")
                st.rerun()

    with st.expander("⛳️ Add Course"):
        nc_n = st.text_input("Course Name", key="side_c_name")
        nc_c = st.text_input("City", value="Costa Mesa", key="side_c_city")
        nc_s = st.text_input("State", value="CA", key="side_c_state")
        if st.button("📍 Register Course"):
            if nc_n: safe_save(pd.concat([c_df, pd.DataFrame([{"Name":nc_n,"City":nc_c,"State":nc_s}])], ignore_index=True), "courses"); st.rerun()
    
    st.divider()
    st.button("🔄 Force Refresh Data", on_click=lambda: st.cache_data.clear())
    st.caption("Customized for Yuji ✨")
