import streamlit as st
import json
import math
import time
import re
from datetime import datetime, timedelta, timezone
from google import genai
import PIL.Image
from supabase import create_client
import pandas as pd

# --- 1. CÀI ĐẶT TRANG CƠ BẢN & GIAO DIỆN ---
st.set_page_config(page_title="Share Bills Super Ultimate", page_icon="💸", layout="wide")

st.markdown("""
<style>
    div[data-testid="InputInstructions"] { display: none !important; }
    button[kind="primary"] {
        background: linear-gradient(135deg, #ff4b4b, #ff7676) !important;
        border: none !important;
        color: white !important;
        border-radius: 12px !important; /* Bo góc mềm mại hơn */
        font-weight: 600 !important;
        transition: transform 0.15s ease, box-shadow 0.15s ease !important;
        box-shadow: 0 4px 6px rgba(255, 75, 75, 0.2) !important;
    }
    button[kind="primary"]:hover { 
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 12px rgba(255, 75, 75, 0.3) !important;
    }
    button[kind="primary"]:active {
        transform: translateY(0px) !important;
    }

    /* 4. Tối ưu khoảng cách các Expander (Thu gọn lại) */
    div[data-testid="stExpander"] {
        margin-bottom: 0.5rem !important;
        border-radius: 10px !important;
    }
    div[data-testid="stExpander"] details summary {
        padding-top: 0.5rem !important;
        padding-bottom: 0.5rem !important;
    }

    /* 5. Khắc phục lỗi nút bị rớt lề trên điện thoại (Tab 2) */
    @media (max-width: 768px) {
        .mobile-margin-fix { display: none !important; } /* Trên mobile cột sẽ tự xếp dọc, giấu cục gạch kê đệm đi */
        .block-container { padding-left: 1rem !important; padding-right: 1rem !important; }
    }

    /* 6. Thêm hiệu ứng sinh động cho icon (Rung rinh nhẹ) */
    @keyframes wiggle {
        0%, 100% { transform: rotate(-3deg); }
        50% { transform: rotate(3deg); }
    }
    .wiggle-icon {
        display: inline-block;
        animation: wiggle 2s ease-in-out infinite;
    }
</style>
""", unsafe_allow_html=True)

try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=API_KEY)
except Exception: client = None

@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)
supabase = init_supabase()

# --- 2. HỆ THỐNG ĐĂNG NHẬP (SUPABASE) ---
if 'logged_in' not in st.session_state:
    st.session_state.update(logged_in=False, username='', nickname='')

def get_user_from_db(username):
    res = supabase.table("users").select("*").eq("username", username).execute()
    return res.data[0] if res.data else None

# GIAO DIỆN ĐĂNG NHẬP
if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center;'>🔐 Đăng nhập Share Bills</h1>", unsafe_allow_html=True)
    tab_login, tab_reg = st.tabs(["Đăng nhập", "Đăng ký"])
    with tab_login:
        l_user = st.text_input("Tài khoản:", key="log_user")
        l_pass = st.text_input("Mật khẩu:", type="password", key="log_pass")
        if st.button("🚀 Đăng nhập", type="primary", use_container_width=True):
            user_data = get_user_from_db(l_user)
            if user_data and l_pass == user_data["password"]:
                st.session_state.update(logged_in=True, username=l_user, nickname=user_data["nickname"])
                st.rerun()
            else: st.error("Sai tài khoản hoặc mật khẩu!")
    with tab_reg:
        r_user = st.text_input("Tên đăng nhập (ID):", key="reg_user")
        r_pass = st.text_input("Mật khẩu:", type="password", key="reg_pass")
        r_nick = st.text_input("Bạn muốn được gọi là gì? (Ví dụ: Mori)", key="reg_nick")
        if st.button("📝 Đăng ký tài khoản", use_container_width=True):
            if get_user_from_db(r_user): st.error("ID này đã tồn tại!")
            elif r_user and r_pass and r_nick:
                supabase.table("users").insert({
                    "username": r_user, "password": r_pass, "nickname": r_nick,
                    "app_data": {"members": {}, "groups": {}, "history": []}
                }).execute()
                st.success("Đăng ký thành công! Mời bạn qua tab Đăng nhập.")
            else: st.warning("Vui lòng điền đủ thông tin!")
    st.stop()
# --- 3. DỮ LIỆU CÁ NHÂN HÓA (V7 - FIX IDENTITY BUG) ---
st.sidebar.markdown(f"### ✨ Xin chào, **{st.session_state.get('nickname', 'Bạn')}**!")
if st.sidebar.button("🚪 Đăng xuất"):
    st.session_state.update(logged_in=False, username='', nickname='')
    st.rerun()

def load_data():
    user_data = get_user_from_db(st.session_state.username)
    if user_data and user_data.get('app_data'):
        data = user_data['app_data']
        raw_members = data.get('members', {})
        
        # --- AUTO MIGRATION: Nâng cấp dữ liệu cũ lên chuẩn ID ---
        # Kiểm tra xem dữ liệu cũ có bị dính lỗi dùng Tên làm ID không (không có key 'name' bên trong)
        is_old_format = any('name' not in v for k, v in raw_members.items() if isinstance(v, dict))
        
        if is_old_format:
            new_members, name_to_id = {}, {}
            my_id = st.session_state.username
            
            for old_name, info in raw_members.items():
                if old_name == st.session_state.nickname:
                    new_id = my_id
                else:
                    new_id = f"user_{int(time.time()*1000)}_{len(new_members)}"
                new_members[new_id] = {"name": old_name, "bank": info.get("bank", ""), "acc": info.get("acc", "")}
                name_to_id[old_name] = new_id
            
            st.session_state.members = new_members
            st.session_state.groups = {g: [name_to_id.get(m, m) for m in m_list] for g, m_list in data.get('groups', {}).items()}
            
            new_history = []
            for b in data.get('history', []):
                b['payer_data'] = {name_to_id.get(k, k): v for k, v in b.get('payer_data', {}).items()}
                b['splits'] = {name_to_id.get(k, k): v for k, v in b.get('splits', {}).items()}
                b['paid_by'] = [name_to_id.get(k, k) for k in b.get('paid_by', [])]
                new_history.append(b)
            st.session_state.history = new_history
            save_data() # Lưu ngay định dạng mới lên Supabase
        else:
            st.session_state.members = raw_members
            st.session_state.groups = data.get('groups', {})
            st.session_state.history = data.get('history', [])
    else: st.session_state.update(members={}, groups={}, history=[])

def save_data():
    new_data = {'members': st.session_state.members, 'groups': st.session_state.groups, 'history': st.session_state.history}
    supabase.table("users").update({"app_data": new_data}).eq("username", st.session_state.username).execute()

if 'members' not in st.session_state: load_data()

# Đảm bảo có bản thân trong danh bạ
my_id = st.session_state.username
if my_id not in st.session_state.members:
    st.session_state.members[my_id] = {"name": st.session_state.nickname, "bank": "", "acc": ""}
    save_data()

# Hàm hỗ trợ hiển thị tên
def get_name(u_id):
    if u_id == my_id: return f"Bản thân ({st.session_state.members.get(u_id, {}).get('name', 'Tôi')})"
    return st.session_state.members.get(u_id, {}).get('name', 'Người dùng đã xóa')

def get_pure_name(u_id):
    return st.session_state.members.get(u_id, {}).get('name', 'Khách')

def parse_amount(text):
    if not text: return 0
    clean = str(text).lower().replace(',', '').replace('.', '').replace(' ', '')
    has_k = 'k' in clean
    clean = re.sub(r'k\b', '*1000', clean)
    try:
        if all(c in "0123456789+-*/.() " for c in clean):
            val = eval(clean)
            if 0 < val < 1000 and not has_k: val *= 1000
            return int(round(val))
    except: pass
    return 0

def format_vn(num): return "{:,}".format(int(num))

st.title("💸 Share Bills Ultimate V7 (Fixed Identity)")
tab1, tab2, tab3, tab4, tab5 = st.tabs(["👥 Danh Bạ & Nhóm", "🧾 Ghi Hóa Đơn", "🔥 Chốt Sổ Nợ", "🕒 Nhật Ký Bill", "🎁 Wrapped & Thống Kê"])

# --- TAB 1: DANH BẠ & NHÓM ---
with tab1:
    st.markdown(f"### 👤 Thông tin cá nhân")
    bank_list = ["", "MB", "VCB", "TPB", "BIDV", "TCB", "VPB", "CTG", "ACB", "SHB", "STB", "VIB"]
    with st.expander("⚙️ Sửa thông tin của bạn"):
        c0, c1, c2 = st.columns([1,1,1])
        my_saved_name = st.session_state.members[my_id].get('name', st.session_state.nickname)
        saved_bank = st.session_state.members[my_id].get('bank', '')
        
        edit_my_name = c0.text_input("Tên hiển thị:", value=my_saved_name)
        edit_my_bank = c1.selectbox("Ngân hàng:", bank_list, index=bank_list.index(saved_bank) if saved_bank in bank_list else 0)
        edit_my_acc = c2.text_input("Số tài khoản:", value=st.session_state.members[my_id].get('acc', ''))
        
        if st.button("💾 Cập nhật bản thân", type="primary"):
            st.session_state.members[my_id] = {"name": edit_my_name, "bank": edit_my_bank, "acc": edit_my_acc}
            # Cập nhật luôn nickname của hệ thống
            st.session_state.nickname = edit_my_name
            save_data(); st.toast("Đã cập nhật!", icon="✅"); st.rerun()

    st.write("---")
    st.markdown("### 👥 Quản lý Bạn bè")
    c_add, c_list = st.columns([1, 1.5], gap="large")
    with c_add:
        st.markdown("#### ➕ Thêm bạn mới")
        with st.container(border=True):
            new_f_name = st.text_input("Tên người bạn:")
            new_f_bank = st.selectbox("Ngân hàng (Tùy chọn):", bank_list, key="new_f_bank")
            new_f_acc = st.text_input("Số tài khoản (Tùy chọn):", key="new_f_acc")
            if st.button("➕ Thêm người này", type="primary", use_container_width=True):
                if not new_f_name.strip(): st.warning("Tên không được để trống!")
                else:
                    new_id = f"user_{int(time.time()*1000)}"
                    st.session_state.members[new_id] = {"name": new_f_name.strip(), "bank": new_f_bank, "acc": new_f_acc.strip()}
                    save_data(); st.toast(f"Đã thêm {new_f_name}!", icon="🎉"); st.rerun()

    with c_list:
        st.markdown("#### 📜 Danh sách đã lưu")
        friend_ids = [u_id for u_id in st.session_state.members.keys() if u_id != my_id]
        if not friend_ids: st.info("Chưa có ai trong danh bạ.")
        else:
            if 'friend_page' not in st.session_state: st.session_state.friend_page = 1
            per_page = 5
            total_pages = max(1, math.ceil(len(friend_ids) / per_page))
            if st.session_state.friend_page > total_pages: st.session_state.friend_page = total_pages
            start_idx = (st.session_state.friend_page - 1) * per_page
            
            for f_id in friend_ids[start_idx:start_idx + per_page]:
                f_data = st.session_state.members[f_id]
                with st.expander(f"👤 {f_data['name']}"):
                    fc0, fc1, fc2 = st.columns([1.5, 1, 1.5])
                    f_bank_saved = f_data.get('bank', '')
                    
                    # Cho phép đổi tên thoải mái ở đây!
                    edit_f_name = fc0.text_input("Đổi tên:", value=f_data['name'], key=f"en_{f_id}")
                    edit_f_bank = fc1.selectbox("Bank:", bank_list, index=bank_list.index(f_bank_saved) if f_bank_saved in bank_list else 0, key=f"eb_{f_id}")
                    edit_f_acc = fc2.text_input("STK:", value=f_data.get('acc', ''), key=f"ea_{f_id}")
                    
                    bc1, bc2 = st.columns(2)
                    if bc1.button("💾 Lưu", key=f"sb_{f_id}", use_container_width=True):
                        st.session_state.members[f_id] = {"name": edit_f_name, "bank": edit_f_bank, "acc": edit_f_acc}
                        save_data(); st.rerun()
                    if bc2.button("🗑️ Xóa", key=f"db_{f_id}", type="primary", use_container_width=True):
                        st.session_state.members.pop(f_id)
                        for g_name in list(st.session_state.groups.keys()):
                            if f_id in st.session_state.groups[g_name]: st.session_state.groups[g_name].remove(f_id)
                        save_data(); st.rerun()
            
            if total_pages > 1:
                # Đổi tỷ lệ cột để đẩy 2 nút ra sát lề
                cp1, cp2, cp3 = st.columns([1.5, 7, 1.5]) 
                
                # Thêm use_container_width=True vào nút Trước
                if cp1.button("⬅️ Trước", disabled=(st.session_state.friend_page == 1), use_container_width=True): 
                    st.session_state.friend_page -= 1; st.rerun()
                    
                cp2.markdown(f"<div style='text-align: center; margin-top: 5px; font-weight: 500;'>Trang {st.session_state.friend_page} / {total_pages}</div>", unsafe_allow_html=True)
                
                # Thêm use_container_width=True vào nút Sau
                if cp3.button("Sau ➡️", disabled=(st.session_state.friend_page == total_pages), use_container_width=True): 
                    st.session_state.friend_page += 1; st.rerun()

    st.write("---")
    st.markdown("### 🧑‍🤝‍🧑 Quản lý Nhóm đi chơi")
    cg_add, cg_list = st.columns([1, 1.5], gap="large")
    all_mem_ids = list(st.session_state.members.keys())
    with cg_add:
        st.markdown("#### ➕ Tạo nhóm mới")
        with st.container(border=True):
            new_g_name = st.text_input("Tên nhóm:")
            new_g_members = st.multiselect("Thành viên:", all_mem_ids, default=[my_id], format_func=get_name)
            if st.button("➕ Lập nhóm", type="primary", use_container_width=True):
                if new_g_name and len(new_g_members) >= 2 and new_g_name not in st.session_state.groups:
                    st.session_state.groups[new_g_name.strip()] = new_g_members; save_data(); st.rerun()
    with cg_list:
        st.markdown("#### 📌 Danh sách nhóm")
        if not st.session_state.groups: st.info("Chưa có hội nhóm nào.")
        else:
            # --- TÍCH HỢP PHÂN TRANG NHÓM ---
            group_names = list(st.session_state.groups.keys())
            if 'group_page' not in st.session_state: st.session_state.group_page = 1
            per_page_g = 5
            total_pages_g = max(1, math.ceil(len(group_names) / per_page_g))
            
            if st.session_state.group_page > total_pages_g: 
                st.session_state.group_page = total_pages_g
                
            start_idx_g = (st.session_state.group_page - 1) * per_page_g
            
            for g_name in group_names[start_idx_g : start_idx_g + per_page_g]:
                g_members = st.session_state.groups[g_name]
                with st.expander(f"📌 {g_name} ({len(g_members)} thành viên)"):
                    edit_g_members = st.multiselect("Thành viên:", all_mem_ids, default=[m for m in g_members if m in all_mem_ids], format_func=get_name, key=f"eg_{g_name}")
                    gc1, gc2 = st.columns(2)
                    if gc1.button("💾 Lưu", key=f"sg_{g_name}", use_container_width=True) and len(edit_g_members) >= 2:
                        st.session_state.groups[g_name] = edit_g_members; save_data(); st.rerun()
                    if gc2.button("🗑️ Xóa nhóm", key=f"dg_{g_name}", type="primary", use_container_width=True):
                        st.session_state.groups.pop(g_name); save_data(); st.rerun()

            if total_pages_g > 1:
                # Đổi tỷ lệ cột tương tự như trên
                gp1, gp2, gp3 = st.columns([1.5, 7, 1.5])
                
                # Thêm use_container_width=True
                if gp1.button("⬅️ Trước", key="g_prev", disabled=(st.session_state.group_page == 1), use_container_width=True): 
                    st.session_state.group_page -= 1; st.rerun()
                    
                gp2.markdown(f"<div style='text-align: center; margin-top: 5px; font-weight: 500;'>Trang {st.session_state.group_page} / {total_pages_g}</div>", unsafe_allow_html=True)
                
                # Thêm use_container_width=True
                if gp3.button("Sau ➡️", key="g_next", disabled=(st.session_state.group_page == total_pages_g), use_container_width=True): 
                    st.session_state.group_page += 1; st.rerun()

# --- TAB 2: GHI HÓA ĐƠN ---
with tab2:
    st.subheader("📝 Ghi hóa đơn mới")
    if 'current_items' not in st.session_state: st.session_state.current_items = []
    
    st.subheader("🤖 AI đọc bill nhanh")
    c_ai1, c_ai2 = st.columns(2)
    current_time_str = datetime.now(timezone(timedelta(hours=7))).strftime('%d/%m/%Y %H:%M')
    
    with c_ai1:
        up_files = st.file_uploader("📸 Nhập bill ở đây", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
        if up_files and st.button("✨ Phân tích tất cả ảnh", type="primary"):
            with st.spinner("🤖 AI đang dán mắt vào đọc bill... Vui lòng đợi xíu!"):
                try:
                    images = [PIL.Image.open(f).copy() for f in up_files]
                    for img in images: img.thumbnail((800, 800))
                    prompt = f"Hôm nay là {current_time_str}. Đọc bill, gộp chung món. Trả về:\nNGÀY: dd/mm/yyyy hh:mm\nTÊN|GIÁ|SL"
                    res = client.models.generate_content(model='gemini-2.5-flash', contents=[prompt] + images)
                    for line in res.text.strip().split('\n'):
                        if line.upper().startswith("NGÀY:"): st.session_state.ai_date = line[5:].strip()
                        else:
                            p = line.split('|')
                            if len(p) == 3: st.session_state.current_items.append({"name": p[0], "price": parse_amount(p[1]), "qty": int(p[2])})
                    st.rerun()
                except Exception as e: st.error(e)
    with c_ai2:
        txt_ai = st.text_area("💬 Dán tin nhắn của bạn ở đây:")
        if txt_ai and st.button("✨ Phân tích chữ", type="primary"):
            with st.spinner("🤖 AI đang đọc tin nhắn..."):
                try:
                    res = client.models.generate_content(model='gemini-3-flash', contents=f"Hôm nay là {current_time_str}. Đọc tin nhắn:\n{txt_ai}\nTrả về:\nNGÀY: dd/mm/yyyy hh:mm\nTÊN|GIÁ|SL")
                    for line in res.text.strip().split('\n'):
                        if line.upper().startswith("NGÀY:"): st.session_state.ai_date = line[5:].strip()
                        else:
                            p = line.split('|')
                            if len(p) == 3: st.session_state.current_items.append({"name": p[0], "price": parse_amount(p[1]), "qty": int(p[2])})
                    st.rerun()
                except Exception as e: st.error(e)

    st.write("---")
    st.subheader("📝 Nhập món lẻ")
    ic1, ic2, ic3, ic4 = st.columns([4, 3, 2, 2])
    im_n = ic1.text_input("Tên món:")
    im_p = ic2.text_input("Giá:")
    im_q = ic3.number_input("SL", 1, 100, 1)
    with ic4:
        st.markdown("<div style='margin-top: 28.5px;'></div>", unsafe_allow_html=True)
        if st.button("➕ Thêm", type="primary", use_container_width=True) and im_n and parse_amount(im_p) > 0:
            st.session_state.current_items.append({"name": im_n, "price": parse_amount(im_p), "qty": im_q}); st.rerun()

    total_bill = 0
    if st.session_state.current_items:
        st.write("---")
        for idx, it in enumerate(st.session_state.current_items):
            c_n, c_p, c_q, c_d = st.columns([4, 3, 2, 1])
            new_price = parse_amount(c_p.text_input("Giá", str(it['price']), key=f"ep_{idx}", label_visibility="collapsed"))
            new_qty = c_q.number_input("SL", value=it['qty'], min_value=1, key=f"eq_{idx}", label_visibility="collapsed")
            st.session_state.current_items[idx] = {"name": c_n.text_input("Tên", it['name'], key=f"en_{idx}", label_visibility="collapsed"), "price": new_price, "qty": new_qty}
            total_bill += new_price * new_qty
            if c_d.button("❌", key=f"d_{idx}"): st.session_state.current_items.pop(idx); st.rerun()

    st.write("---")
    c_info1, c_info2 = st.columns(2)
    b_title = c_info1.text_input("Tiêu đề bill:", value="Đi ăn")
    b_date = c_info2.text_input("Thời gian:", value=st.session_state.get("ai_date", datetime.now().strftime("%d/%m/%Y %H:%M")))
    if total_bill == 0: total_bill = parse_amount(st.text_input("💰 Tổng bill nhanh:", "0"))

    st.write("---")
    st.markdown(f"#### 💳 Ai thanh toán hóa đơn này? (Tổng: {format_vn(total_bill)}đ)")
    all_mem_ids = list(st.session_state.members.keys())
    selected_payers = st.multiselect("Người ứng tiền:", all_mem_ids, default=[my_id], format_func=get_name)
    
    payer_data = {}
    if len(selected_payers) > 1:
        pay_method = st.radio("Cách chia tiền ứng:", ["Chia đều", "Theo tỉ lệ (%)", "Số tiền cụ thể"], horizontal=True)
        if pay_method == "Chia đều":
            for p_id in selected_payers: payer_data[p_id] = total_bill / len(selected_payers)
        elif pay_method == "Theo tỉ lệ (%)":
            cols = st.columns(len(selected_payers))
            for i, p_id in enumerate(selected_payers):
                pct = cols[i].number_input(f"% của {get_pure_name(p_id)}", min_value=0, max_value=100, value=0, key=f"pct_{p_id}")
                payer_data[p_id] = (pct / 100) * total_bill
        else:
            cols = st.columns(len(selected_payers))
            for i, p_id in enumerate(selected_payers): 
                payer_data[p_id] = cols[i].number_input(f"Tiền {get_pure_name(p_id)} ứng", min_value=0, value=0, step=1000, key=f"amt_{p_id}")
    elif len(selected_payers) == 1: payer_data[selected_payers[0]] = total_bill

    st.write("---")
    st.markdown("#### 🍴 Ai tham gia ăn?")
    use_g = st.selectbox("Chọn nhóm nhanh:", ["-- Chọn lẻ --"] + list(st.session_state.groups.keys()))
    def_m = st.session_state.groups.get(use_g, all_mem_ids) if use_g != "-- Chọn lẻ --" else all_mem_ids
    b_cons = st.multiselect("Danh sách ăn:", def_m, default=def_m, format_func=get_name)

    if b_cons and total_bill > 0:
        method = st.radio("Cách chia tiền ăn:", ["Chia đều", "Chia theo món lẻ"], horizontal=True)
        splits = {c_id: 0 for c_id in b_cons}
        if method == "Chia theo món lẻ" and st.session_state.current_items:
            pool = 0
            for idx, it in enumerate(st.session_state.current_items):
                st.write(f"🍴 {it['name']} ({format_vn(it['price']*it['qty'])}đ)")
                who = st.multiselect(f"Ai ăn?", b_cons, default=b_cons, format_func=get_pure_name, key=f"w_{idx}")
                if who:
                    for w in who: splits[w] += (it['price']*it['qty'])/len(who)
                else: pool += it['price']*it['qty']
            if pool > 0:
                for c_id in b_cons: splits[c_id] += pool/len(b_cons)
        else:
            for c_id in b_cons: splits[c_id] = total_bill / len(b_cons)
            
        has_deadline = st.checkbox("📅 Đặt hạn chót thanh toán?")
        b_deadline = st.date_input("Hạn chót:", value=datetime.now().date()).strftime("%d/%m/%Y") if has_deadline else None

        if st.button("💾 LƯU SỔ NỢ", type="primary", use_container_width=True):
            if not selected_payers: st.error("Chưa chọn người trả tiền!")
            elif sum(payer_data.values()) != total_bill: st.error(f"Tổng ứng lệch với tổng bill!")
            else:
                st.session_state.history.append({
                    "id": time.time(), "date": b_date, "deadline": b_deadline, "name": b_title, "amount": total_bill, 
                    "payer_data": payer_data, "splits": splits, 
                    "status": "unpaid", "paid_by": [], "items": st.session_state.current_items.copy()
                })
                st.session_state.current_items = []
                st.session_state.ai_date = datetime.now().strftime("%d/%m/%Y %H:%M")
                save_data(); st.balloons(); st.success("🎉 Đã lưu!"); time.sleep(1.5); st.rerun()

# --- TAB 3: CHỐT SỔ ---
with tab3:
    unpaid = [b for b in st.session_state.history if b['status'] == 'unpaid']
    
    # Cảnh báo deadline
    today = datetime.now().date()
    for b in unpaid:
        if b.get('deadline'):
            try:
                days_left = (datetime.strptime(b['deadline'], "%d/%m/%Y").date() - today).days
                if 0 <= days_left <= 7: st.warning(f"⏰ Hạn chót bill **{b['name']}**: còn **{days_left} ngày**")
            except: pass

    if not unpaid: st.success("Tất cả hóa đơn đã thanh toán xong! 🎉")
    else:
        st.subheader("⚙️ Tùy chọn chốt nợ")
        
        # ==========================================
        # MỤC 1: CÔNG TẮC BÙ TRỪ
        # ==========================================
        use_netting = st.toggle("🔀 Bật tính nhanh nợ chéo", value=True)
        
        # --- BẮT ĐẦU XỬ LÝ TOÁN HỌC TRƯỚC ---
        matrix = {m1: {m2: 0 for m2 in st.session_state.members} for m1 in st.session_state.members}
        details = {m1: {m2: [] for m2 in st.session_state.members} for m1 in st.session_state.members}
        debts_dict = {}

        # 1. Quét dữ liệu lấy nợ gốc
        for b in unpaid:
            p_data = b.get('payer_data', {})
            splits = b.get('splits', {})
            paid_by = b.get('paid_by', [])
            
            bals = {}
            for p, a in p_data.items(): 
                if p not in paid_by: bals[p] = bals.get(p, 0) + a
            for c, a in splits.items(): 
                if c not in paid_by: bals[c] = bals.get(c, 0) - a

            pos = {k: v for k, v in bals.items() if v > 1}
            neg = {k: v for k, v in bals.items() if v < -1}
            tot_pos = sum(pos.values())

            if tot_pos > 0:
                for debtor, d_bal in neg.items():
                    for creditor, c_bal in pos.items():
                        amt = abs(d_bal) * (c_bal / tot_pos)
                        if amt > 1:
                            pair = (debtor, creditor)
                            if pair not in debts_dict: debts_dict[pair] = []
                            debts_dict[pair].append({"date": b['date'], "name": b['name'], "amount": amt, "deadline": b.get('deadline'), "b_id": b.get('id')})
                            matrix[debtor][creditor] += amt
                            details[debtor][creditor].append({"name": b['name'], "amount": amt, "b_id": b.get('id')})
        
        # 2. Tạo sẵn Tin nhắn KHÔNG bù trừ
        msg_raw = "📣 TỔNG KẾT CHỐT SỔ NỢ (Chưa bù trừ):\n"
        if debts_dict:
            for (d_raw, c_raw), items_raw in debts_dict.items():
                tot_amt = sum(it['amount'] for it in items_raw)
                msg_raw += f"🔸 {get_pure_name(d_raw)} nợ {get_pure_name(c_raw)}: {format_vn(tot_amt)}đ\n"
        else:
            msg_raw += "Không có khoản nợ nào.\n"

        # 3. Tạo sẵn Tin nhắn CÓ bù trừ
        msg_netting = "📣 TỔNG KẾT CHỐT SỔ NỢ (Đã bù trừ):\n"
        net_bal = {m: 0 for m in st.session_state.members}
        for d in matrix:
            for c in matrix[d]:
                net_bal[c] += matrix[d][c]
                net_bal[d] -= matrix[d][c]
        
        debtors_l = [[m, abs(v)] for m, v in net_bal.items() if v < -1]
        creditors_l = [[m, v] for m, v in net_bal.items() if v > 1]
        
        found_netting = False
        if debtors_l:
            while debtors_l and creditors_l:
                debtors_l.sort(key=lambda x: x[1], reverse=True); creditors_l.sort(key=lambda x: x[1], reverse=True)
                d_n, d_a = debtors_l[0]; c_n, c_a = creditors_l[0]
                s_a = min(d_a, c_a)
                msg_netting += f"✨ {get_pure_name(d_n)} chuyển cho {get_pure_name(c_n)}: {format_vn(s_a)}đ\n"
                debtors_l[0][1] -= s_a; creditors_l[0][1] -= s_a
                if debtors_l[0][1] < 1: debtors_l.pop(0)
                if creditors_l[0][1] < 1: creditors_l.pop(0)
        else:
            msg_netting += "Không có khoản nợ nào cần chốt.\n"
            
        for i in range(len(list(st.session_state.members.keys()))):
            for j in range(i + 1, len(list(st.session_state.members.keys()))):
                m1, m2 = list(st.session_state.members.keys())[i], list(st.session_state.members.keys())[j]
                if matrix[m1][m2] > matrix[m2][m1] and (matrix[m1][m2] - matrix[m2][m1]) > 1: found_netting = True
                elif matrix[m2][m1] > matrix[m1][m2] and (matrix[m2][m1] - matrix[m1][m2]) > 1: found_netting = True


        # ==========================================
        # MỤC 2: COPY TIN NHẮN (Luôn hiển thị)
        # ==========================================
        st.write("---")
        st.subheader("📋 Copy tin nhắn gửi nhóm")
        if use_netting:
            st.code(msg_netting, language="text")
        else:
            st.code(msg_raw, language="text")
            
        st.write("---")
        
        # ==========================================
        # MỤC 3: DANH SÁCH NỢ & THANH TOÁN
        # ==========================================
        if not use_netting:
            st.subheader("📜 Danh sách nợ chi tiết (Không bù trừ)")
            for (debtor, creditor), items in debts_dict.items():
                total_owed = sum(item['amount'] for item in items)
                with st.expander(f"🔴 **{get_pure_name(debtor)}** nợ **{get_pure_name(creditor)}**: {format_vn(total_owed)}đ"):
                    for item in items: st.write(f"- {item['date']} | {item['name']} | **{format_vn(item['amount'])}đ**")
                    
                    c_info = st.session_state.members.get(creditor, {"bank": "", "acc": ""})
                    if c_info['bank'] and c_info['acc']:
                        st.image(f"https://img.vietqr.io/image/{c_info['bank']}-{c_info['acc']}-compact2.png?amount={int(total_owed)}", width=250)
                    
                    if st.button(f"✅ Đã thanh toán xong!", key=f"p_{debtor}_{creditor}", type="primary"):
                        item_ids = [it['b_id'] for it in items]
                        for b in st.session_state.history:
                            if b.get('id') in item_ids and b['status'] == 'unpaid':
                                b.setdefault('paid_by', []).append(debtor)
                                t_bals = {}
                                for p, a in b.get('payer_data', {}).items(): 
                                    if p not in b['paid_by']: t_bals[p] = t_bals.get(p, 0) + a
                                for c, a in b['splits'].items(): 
                                    if c not in b['paid_by']: t_bals[c] = t_bals.get(c, 0) - a
                                if not any(v < -1 for v in t_bals.values()): b['status'] = 'paid'
                        save_data(); st.rerun()
        else:
            st.subheader("📜 Danh sách nợ chéo (Đã bù trừ)")
            if not found_netting: 
                st.info("Không có khoản nợ nào cần chốt.")
            else:
                for i in range(len(list(st.session_state.members.keys()))):
                    for j in range(i + 1, len(list(st.session_state.members.keys()))):
                        m1, m2 = list(st.session_state.members.keys())[i], list(st.session_state.members.keys())[j]
                        if matrix[m1][m2] > matrix[m2][m1]:
                            net_amt = matrix[m1][m2] - matrix[m2][m1]
                            if net_amt > 1:
                                with st.expander(f"👉 **{get_pure_name(m1)}** cần chuyển **{get_pure_name(m2)}**: {format_vn(net_amt)}đ"):
                                    c_info = st.session_state.members.get(m2, {})
                                    if c_info.get('bank') and c_info.get('acc'):
                                        st.image(f"https://img.vietqr.io/image/{c_info['bank']}-{c_info['acc']}-compact2.png?amount={int(net_amt)}", width=250)
                                    
                                    if st.button(f"✅ Xác nhận thanh toán xong", key=f"n_{m1}_{m2}", type="primary"):
                                        b_ids = [it['b_id'] for it in details[m1][m2]]
                                        for b in st.session_state.history:
                                            if b.get('id') in b_ids and b['status'] == 'unpaid':
                                                b.setdefault('paid_by', []).append(m1)
                                                t_b = {}
                                                for p, a in b.get('payer_data', {}).items(): 
                                                    if p not in b['paid_by']: t_b[p] = t_b.get(p, 0) + a
                                                for c, a in b['splits'].items(): 
                                                    if c not in b['paid_by']: t_b[c] = t_b.get(c, 0) - a
                                                if not any(v < -1 for v in t_b.values()): b['status'] = 'paid'
                                        save_data(); st.rerun()
                        elif matrix[m2][m1] > matrix[m1][m2]:
                            net_amt = matrix[m2][m1] - matrix[m1][m2]
                            if net_amt > 1:
                                with st.expander(f"👉 **{get_pure_name(m2)}** cần chuyển **{get_pure_name(m1)}**: {format_vn(net_amt)}đ"):
                                    c_info = st.session_state.members.get(m1, {})
                                    if c_info.get('bank') and c_info.get('acc'):
                                        st.image(f"https://img.vietqr.io/image/{c_info['bank']}-{c_info['acc']}-compact2.png?amount={int(net_amt)}", width=250)
                                    if st.button(f"✅ Xác nhận thanh toán xong", key=f"n_{m2}_{m1}", type="primary"):
                                        b_ids = [it['b_id'] for it in details[m2][m1]]
                                        for b in st.session_state.history:
                                            if b.get('id') in b_ids and b['status'] == 'unpaid':
                                                b.setdefault('paid_by', []).append(m2)
                                                t_b = {}
                                                for p, a in b.get('payer_data', {}).items(): 
                                                    if p not in b['paid_by']: t_b[p] = t_b.get(p, 0) + a
                                                for c, a in b['splits'].items(): 
                                                    if c not in b['paid_by']: t_b[c] = t_b.get(c, 0) - a
                                                if not any(v < -1 for v in t_b.values()): b['status'] = 'paid'
                                        save_data(); st.rerun()

            if not found_netting: st.info("Không có khoản nợ nào cần chốt.")

# --- TAB 4: NHẬT KÝ ---
with tab4:
    st.subheader("🕒 Lịch sử hóa đơn gốc")
    @st.dialog("⚠️ Xác nhận xóa hóa đơn")
    def confirm_delete_bill(real_index, bill_name):
        st.write(f"Bạn có chắc chắn xóa bill **{bill_name}** không?")
        c1, c2 = st.columns(2)
        if c1.button("Hủy", use_container_width=True): st.rerun()
        if c2.button("Xóa luôn!", type="primary", use_container_width=True):
            st.session_state.history.pop(real_index)
            save_data(); st.toast("Đã xóa!", icon="✅"); st.rerun()

    if not st.session_state.history: st.markdown("<h3 style='text-align: center; color: #ff4b4b; padding: 50px 0;'>🙌 Chưa có hoá đơn, lên kèo đi chơi thôi!!! 🙌</h3>", unsafe_allow_html=True)
    else:
        # Bộ lọc
        filter_col1, filter_col2 = st.columns(2)
        status_filter = filter_col1.selectbox("Bộ lọc:", ["Tất cả", "🔴 Đang nợ", "✅ Đã thanh toán xong"])
        sort_order = filter_col2.radio("Sắp xếp theo:", ["Mới nhất trước", "Cũ nhất trước"], horizontal=True)
        st.write("---")
        
        display_history = []
        for i, b in enumerate(st.session_state.history):
            if status_filter == "🔴 Đang nợ" and b.get('status') == 'paid': continue
            if status_filter == "✅ Đã thanh toán xong" and b.get('status') == 'unpaid': continue
            display_history.append((i, b))
            
        if sort_order == "Mới nhất trước": display_history = list(reversed(display_history))
        
        for real_idx, b in display_history:
            status_txt = " (Đã xong ✅)" if b.get('status') == 'paid' else ""
            with st.expander(f"[{b['date']}] {b['name']} - {format_vn(b['amount'])}đ{status_txt}"):
                p_str = ", ".join([f"{get_pure_name(k)} ({format_vn(v)}đ)" for k,v in b.get('payer_data', {}).items()])
                st.write(f"**Nguồn tiền:** {p_str}")
                for p_id, amt in b['splits'].items():
                    if amt > 0:
                        is_done = "✅ Xong" if p_id in b.get('paid_by', []) or b.get('status') == 'paid' else "🔴 Nợ"
                        st.write(f"- {get_pure_name(p_id)} ăn: {format_vn(amt)}đ ({is_done})")
                st.write("---")
                if st.button(f"🗑️ Xóa bill", key=f"del_b_{b['id']}", type="primary"): confirm_delete_bill(real_idx, b['name'])

# --- TAB 5: WRAPPED & ANALYTICS ---
with tab5:
    my_id = st.session_state.username
    my_name = get_pure_name(my_id)
    st.markdown(f"<h2 style='text-align: center; color: #ff4b4b;'>🎉 Share Bills Wrapped - {my_name}</h2>", unsafe_allow_html=True)
    
    if not st.session_state.history:
        st.info("Chưa có dữ liệu. Hãy ghi bill để mở khóa báo cáo!")
    else:
        # Tự động lấy tháng và năm hiện tại để mốc thời gian không bao giờ bị lỗi thời
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        # TÍNH NĂNG THỐNG KÊ CHI TIẾT
        time_filter = st.radio("⏳ Mốc thời gian:", [f"Tháng này (Tháng {current_month})", f"Từ đầu năm ({current_year})"], horizontal=True)
        filtered_history = []
        for b in st.session_state.history:
            try:
                match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', str(b['date']))
                if match:
                    d_m, d_y = int(match.group(2)), int(match.group(3))
                    if ("Tháng này" in time_filter and d_m == current_month and d_y == current_year) or ("đầu năm" in time_filter and d_y == current_year):
                        filtered_history.append(b)
            except: pass

        if not filtered_history: 
            st.warning("Không có dữ liệu trong khoảng thời gian này.")
        else:
            my_spent = 0
            others_owe_me = {}
            i_owe_others = {}
            group_stats = {}
            all_unpaid_debts = []

            for b in filtered_history:
                splits = b.get('splits', {})
                paid_by = b.get('paid_by', [])
                p_data = b.get('payer_data', {})
                
                # Check nhanh: Nếu ID của mình nằm trong những người ăn -> Cộng tiền ăn
                if my_id in splits: 
                    my_spent += splits[my_id]
                
                if b.get('status') == 'unpaid':
                    bals = {}
                    for p, a in p_data.items():
                        if p not in paid_by: bals[p] = bals.get(p, 0) + a
                    for c, a in splits.items():
                        if c not in paid_by: bals[c] = bals.get(c, 0) - a
                        
                    pos_bals = {k: v for k, v in bals.items() if v > 1000}
                    neg_bals = {k: v for k, v in bals.items() if v < -1000}
                    tot_pos = sum(pos_bals.values())
                    
                    if my_id in bals and tot_pos > 0:
                        my_bal = bals[my_id]
                        if my_bal > 1000: # Mình ứng tiền -> Người khác nợ mình
                            for k, v in neg_bals.items(): 
                                others_owe_me[k] = others_owe_me.get(k, 0) + abs(v) * (my_bal / tot_pos)
                        elif my_bal < -1000: # Mình ăn nợ -> Mình nợ người khác
                            for k, v in pos_bals.items(): 
                                i_owe_others[k] = i_owe_others.get(k, 0) + abs(my_bal) * (v / tot_pos)

                    if tot_pos > 0:
                        for d_id, d_bal in neg_bals.items():
                            for c_id, c_bal in pos_bals.items():
                                owed_amt = abs(d_bal) * (c_bal / tot_pos)
                                if owed_amt > 1000: 
                                    all_unpaid_debts.append({
                                        "debtor": get_pure_name(d_id), # Dịch ID sang Tên khi in ra biểu đồ
                                        "creditor": get_pure_name(c_id), 
                                        "amount": int(owed_amt), 
                                        "item": b.get('name', 'Bill')
                                    })

                # Tính toán xếp hạng Nhóm 
                gn = "Nhóm chung"
                for g_name, g_members in st.session_state.groups.items():
                    if set(splits.keys()) == set(g_members): 
                        gn = g_name; break
                if gn not in group_stats: group_stats[gn] = {"count": 0, "money": 0}
                group_stats[gn]["count"] += 1
                group_stats[gn]["money"] += b.get('amount', 0)

            st.markdown(f"### 📊 Dashboard của {my_name}")
            c1, c2, c3 = st.columns(3)
            c1.metric("Tiền bạn đã chi (Tiền ăn)", f"{format_vn(my_spent)}đ")
            
            tot_o_me = sum(others_owe_me.values())
            tot_i_o = sum(i_owe_others.values())
            
            # Lấy ra ID người nợ nhiều nhất và dịch ra tên
            m_debtor_id = max(others_owe_me, key=others_owe_me.get) if others_owe_me else None
            if m_debtor_id: 
                c2.metric("Nợ bạn nhiều nhất", get_pure_name(m_debtor_id), f"{format_vn(others_owe_me.get(m_debtor_id, 0))}đ / Tổng: {format_vn(tot_o_me)}đ", delta_color="normal")
            else: 
                c2.metric("Nợ bạn nhiều nhất", "Không ai", "0đ / Tổng: 0đ", delta_color="off")
            
            # Lấy ra ID chủ nợ lớn nhất và dịch ra tên
            m_creditor_id = max(i_owe_others, key=i_owe_others.get) if i_owe_others else None
            if m_creditor_id: 
                c3.metric("Bạn nợ nhiều nhất", get_pure_name(m_creditor_id), f"-{format_vn(i_owe_others.get(m_creditor_id, 0))}đ / Tổng: -{format_vn(tot_i_o)}đ", delta_color="inverse")
            else: 
                c3.metric("Bạn nợ nhiều nhất", "Không ai", "0đ / Tổng: 0đ", delta_color="off")

            st.write("---")
            st.subheader("🔥 Bảng Xếp Hạng Nhóm (Leaderboard)")
            for i, (name, s) in enumerate(sorted(group_stats.items(), key=lambda x: x[1]['count'], reverse=True)):
                medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else "🔹"
                st.write(f"{medal} **{name}**: {s['count']} kèo - Tổng chi: {format_vn(s['money'])}đ")

            st.write("---")
            st.subheader("📊 Biểu đồ Xếp hạng Nợ (Top 10)")
            if all_unpaid_debts:
                top_10 = sorted(all_unpaid_debts, key=lambda x: x['amount'], reverse=True)[:10]
                df_chart = pd.DataFrame({"Khoản nợ": [f"{d['debtor']} ➜ {d['creditor']}\n({d['item']})" for d in top_10], "Số tiền (VNĐ)": [d['amount'] for d in top_10]}).set_index("Khoản nợ")
                st.bar_chart(df_chart, color="#ff4b4b")
                with st.expander("🔍 Xem chi tiết bảng số liệu"): st.table(df_chart.style.format("{:,}₫"))
            else: 
                st.info("Sổ nợ trống, không có gì để vẽ biểu đồ cả! 🎉")
