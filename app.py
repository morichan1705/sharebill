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

# CSS TUỲ CHỈNH: Đổi màu nền, màu ô nhập liệu, ẩn "Enter to apply" và đổi màu nút đỏ
st.markdown("""
<style>
  
    /* Ẩn dòng chữ "Press Enter to apply" mặc định của Streamlit */
    div[data-testid="InputInstructions"] {
        display: none !important;
    }

    /* Đổi màu các nút bấm có type="primary" thành màu Đỏ */
    button[kind="primary"] {
        background-color: #ff4b4b !important;
        border-color: #ff4b4b !important;
        color: white !important;
    }
    button[kind="primary"]:hover {
        background-color: #e03e3e !important;
    }
</style>
""", unsafe_allow_html=True)

# Lấy Key từ Secrets
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=API_KEY)
except Exception as e:
    client = None

# --- KHỞI TẠO SUPABASE ---
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# --- 2. HỆ THỐNG ĐĂNG NHẬP / ĐĂNG KÝ (SUPABASE) ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ''
    st.session_state.nickname = ''

def get_user_from_db(username):
    res = supabase.table("users").select("*").eq("username", username).execute()
    return res.data[0] if res.data else None

# GIAO DIỆN ĐĂNG NHẬP
if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center;'>🔐 Đăng nhập Share Bills</h1>", unsafe_allow_html=True)
    tab_login, tab_reg = st.tabs(["Đăng nhập", "Đăng ký"])
    
    with tab_login:
        l_user = st.text_input("Tài khoản:")
        l_pass = st.text_input("Mật khẩu:", type="password")
        if st.button("🚀 Đăng nhập", type="primary", use_container_width=True):
            user_data = get_user_from_db(l_user)
            if user_data:
                if l_pass == user_data["password"]:
                    st.session_state.logged_in = True
                    st.session_state.username = l_user
                    st.session_state.nickname = user_data["nickname"]
                    st.rerun()
                else:
                    st.error("Sai mật khẩu!")
            else:
                st.error("Tài khoản không tồn tại!")
                
    with tab_reg:
        r_user = st.text_input("Tên đăng nhập (ID):", key="reg_id")
        r_pass = st.text_input("Mật khẩu:", type="password", key="reg_pass")
        r_nick = st.text_input("Bạn muốn được gọi là gì? (Ví dụ: Mori)", key="reg_nick")
        
        if st.button("📝 Đăng ký tài khoản", use_container_width=True):
            if get_user_from_db(r_user): 
                st.error("ID này đã tồn tại!")
            elif r_user and r_pass and r_nick:
                supabase.table("users").insert({
                    "username": r_user,
                    "password": r_pass,
                    "nickname": r_nick,
                    "app_data": {"members": {}, "groups": {}, "history": []}
                }).execute()
                st.success("Đăng ký thành công! Mời bạn qua tab Đăng nhập.")
            else: 
                st.warning("Vui lòng điền đủ 3 thông tin!")
                
    st.stop() 

# --- 3. CHUẨN BỊ DỮ LIỆU CÁ NHÂN HÓA (SUPABASE) ---
st.sidebar.markdown(f"### ✨ Xin chào, **{st.session_state.get('nickname', 'Bạn')}**!")
if st.sidebar.button("🚪 Đăng xuất"):
    st.session_state.logged_in = False
    st.session_state.username = ''
    st.session_state.nickname = ''
    st.rerun()

def load_data():
    user_data = get_user_from_db(st.session_state.username)
    if user_data and user_data.get('app_data'):
        data = user_data['app_data']
        st.session_state.members = data.get('members', {})
        st.session_state.groups = data.get('groups', {})
        st.session_state.history = data.get('history', [])
    else:
        st.session_state.members, st.session_state.groups, st.session_state.history = {}, {}, []

def save_data():
    new_app_data = {
        'members': st.session_state.members, 
        'groups': st.session_state.groups, 
        'history': st.session_state.history
    }
    supabase.table("users").update({"app_data": new_app_data}).eq("username", st.session_state.username).execute()

if 'members' not in st.session_state: load_data()

# Hàm bổ trợ
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

def format_vn(num):
    return "{:,}".format(int(num))

st.title("💸 Share Bills Ultimate V6")
tab1, tab2, tab3, tab4, tab5 = st.tabs(["👥 Danh Bạ & Nhóm", "🧾 Ghi Hóa Đơn", "🔥 Chốt Sổ Nợ", "🕒 Nhật Ký Bill", "🎁 Wrapped & Thống Kê"])

# --- TAB 1: DANH BẠ & THÔNG TIN CÁ NHÂN ---
with tab1:
    nickname = st.session_state.get('nickname', 'Bản thân')
    st.markdown(f"### 👤 Thông tin cá nhân ({nickname})")
    
    if nickname not in st.session_state.members:
        st.session_state.members[nickname] = {"bank": "", "acc": ""}
        if 'groups' not in st.session_state: st.session_state.groups = {}

    bank_list = ["", "MB", "VCB", "TPB", "BIDV", "TCB", "VPB", "CTG", "ACB", "SHB", "STB", "VIB"]

    with st.expander("⚙️ Sửa thông tin nhận tiền của bạn"):
        c1, c2 = st.columns(2)
        saved_bank = st.session_state.members[nickname].get('bank', '')
        saved_acc = st.session_state.members[nickname].get('acc', '')
        default_idx = bank_list.index(saved_bank) if saved_bank in bank_list else 0
        
        my_bank = c1.selectbox("Ngân hàng:", bank_list, index=default_idx, key="my_bank_select")
        my_acc = c2.text_input("Số tài khoản:", value=saved_acc, key="my_acc_input")
        
        if st.button("💾 Cập nhật", type="primary"):
            st.session_state.members[nickname] = {"bank": my_bank, "acc": my_acc}
            save_data()
            st.toast("Đã cập nhật số tài khoản!", icon="✅")
            st.rerun()

    st.write("---")
    st.markdown("### 👥 Quản lý Bạn bè")
    col_add_friend, col_list_friend = st.columns([1, 1.5], gap="large")

    with col_add_friend:
        st.markdown("#### ➕ Thêm bạn mới")
        with st.container(border=True):
            new_f_name = st.text_input("Tên người bạn:", placeholder="Ví dụ: Hồng, Thắng...")
            new_f_bank = st.selectbox("Ngân hàng (Tùy chọn):", bank_list, key="new_f_bank")
            new_f_acc = st.text_input("Số tài khoản (Tùy chọn):", key="new_f_acc")
            
            if st.button("➕ Thêm người này", type="primary", use_container_width=True):
                if not new_f_name.strip(): st.warning("Tên không được để trống!")
                elif new_f_name.strip() in st.session_state.members: st.error("Tên người này đã có trong danh bạ!")
                else:
                    st.session_state.members[new_f_name.strip()] = {"bank": new_f_bank, "acc": new_f_acc.strip()}
                    save_data()
                    st.toast(f"Đã thêm {new_f_name}!", icon="🎉")
                    st.rerun()

    with col_list_friend:
        st.markdown("#### 📜 Danh sách đã lưu")
        friends = [m for m in st.session_state.members.keys() if m != nickname]
        
        if not friends:
            st.info("Chưa có ai trong danh bạ. Hãy thêm bạn bè ở bên cạnh nhé!")
        else:
            if 'friend_page' not in st.session_state:
                st.session_state.friend_page = 1
            
            per_page = 6
            total_pages = max(1, math.ceil(len(friends) / per_page))
            
            if st.session_state.friend_page > total_pages: st.session_state.friend_page = total_pages
            if st.session_state.friend_page < 1: st.session_state.friend_page = 1
            
            start_idx = (st.session_state.friend_page - 1) * per_page
            end_idx = start_idx + per_page
            
            for f_name in friends[start_idx:end_idx]:
                with st.expander(f"👤 {f_name}"):
                    fc1, fc2 = st.columns(2)
                    f_bank_saved = st.session_state.members[f_name].get('bank', '')
                    f_idx = bank_list.index(f_bank_saved) if f_bank_saved in bank_list else 0
                    
                    edit_f_bank = fc1.selectbox("Ngân hàng:", bank_list, index=f_idx, key=f"edit_bank_{f_name}")
                    edit_f_acc = fc2.text_input("Số tài khoản:", value=st.session_state.members[f_name].get('acc', ''), key=f"edit_acc_{f_name}")
                    
                    bc1, bc2 = st.columns(2)
                    if bc1.button("💾 Lưu", key=f"save_btn_{f_name}", use_container_width=True):
                        st.session_state.members[f_name] = {"bank": edit_f_bank, "acc": edit_f_acc}
                        save_data()
                        st.toast(f"Đã cập nhật {f_name}!", icon="✅")
                        st.rerun()
                    if bc2.button("🗑️ Xóa bạn", key=f"del_btn_{f_name}", type="primary", use_container_width=True):
                        st.session_state.members.pop(f_name)
                        for g_name in list(st.session_state.groups.keys()):
                            if f_name in st.session_state.groups[g_name]:
                                st.session_state.groups[g_name].remove(f_name)
                        save_data()
                        st.toast(f"Đã xóa {f_name}!", icon="🗑️")
                        st.rerun()
            
            if total_pages > 1:
                cp1, cp2, cp3 = st.columns([1, 2, 1])
                if cp1.button("⬅️ Trước", disabled=(st.session_state.friend_page == 1), use_container_width=True):
                    st.session_state.friend_page -= 1
                    st.rerun()
                cp2.markdown(f"<div style='text-align: center; margin-top: 10px; font-weight: bold;'>{st.session_state.friend_page} of {total_pages}</div>", unsafe_allow_html=True)
                if cp3.button("Sau ➡️", disabled=(st.session_state.friend_page == total_pages), use_container_width=True):
                    st.session_state.friend_page += 1
                    st.rerun()

    st.write("---")
    st.markdown("### 🧑‍🤝‍🧑 Quản lý Nhóm đi chơi")
    col_add_group, col_list_group = st.columns([1, 1.5], gap="large")
    all_members_list = list(st.session_state.members.keys())

    with col_add_group:
        st.markdown("#### ➕ Tạo nhóm mới")
        with st.container(border=True):
            new_g_name = st.text_input("Tên nhóm:", placeholder="Ví dụ: Nhóm Trà Sữa...")
            new_g_members = st.multiselect("Chọn thành viên:", all_members_list, default=[nickname], format_func=lambda x: f"Bản thân ({x})" if x == nickname else x, key="new_g_members")
            if st.button("➕ Lập nhóm", type="primary", use_container_width=True):
                if not new_g_name.strip(): st.warning("Vui lòng đặt tên cho nhóm!")
                elif len(new_g_members) < 2: st.warning("Một nhóm phải có ít nhất 2 người!")
                elif new_g_name.strip() in st.session_state.groups: st.error("Tên nhóm này đã tồn tại!")
                else:
                    st.session_state.groups[new_g_name.strip()] = new_g_members
                    save_data()
                    st.toast(f"Đã tạo nhóm {new_g_name}!", icon="🎉")
                    st.rerun()

    with col_list_group:
        st.markdown("#### 📌 Danh sách các nhóm")
        if not st.session_state.groups:
            st.info("Bạn chưa có hội nhóm nào.")
        else:
            for g_name, g_members in list(st.session_state.groups.items()):
                with st.expander(f"📌 Nhóm: {g_name} ({len(g_members)} thành viên)"):
                    valid_members = [m for m in g_members if m in all_members_list]
                    edit_g_members = st.multiselect("Chỉnh sửa thành viên:", all_members_list, default=valid_members, format_func=lambda x: f"Bản thân ({x})" if x == nickname else x, key=f"edit_g_{g_name}")
                    gc1, gc2 = st.columns(2)
                    if gc1.button("💾 Lưu", key=f"save_g_{g_name}", use_container_width=True):
                        if len(edit_g_members) < 2: st.error("Nhóm không thể ít hơn 2 người!")
                        else:
                            st.session_state.groups[g_name] = edit_g_members
                            save_data()
                            st.rerun()
                    if gc2.button("🗑️ Xóa nhóm", key=f"del_g_{g_name}", type="primary", use_container_width=True):
                        st.session_state.groups.pop(g_name)
                        save_data()
                        st.rerun()

# --- TAB 2: GHI HÓA ĐƠN ---
with tab2:
    my_nick = st.session_state.get('nickname', 'Bản thân')
    st.subheader("📝 Ghi hóa đơn mới")
    if 'current_items' not in st.session_state: st.session_state.current_items = []
   
    st.subheader("🤖 AI giúp bạn ghi hoá đơn nhanh")
    c_ai1, c_ai2 = st.columns(2)
    
    gmt7 = timezone(timedelta(hours=7))
    current_time_str = datetime.now(gmt7).strftime('%d/%m/%Y %H:%M')
    
    with c_ai1:
        up_files = st.file_uploader("📸 Nhập bill ở đây", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
        if up_files and st.button("✨ Phân tích tất cả ảnh", type="primary"):
            # THÊM SPINNER Ở ĐÂY
            with st.spinner("🤖 AI đang dán mắt vào đọc bill... Vui lòng đợi xíu!"):
                try:
                    images = []
                    for f in up_files:
                        img = PIL.Image.open(f)
                        img.thumbnail((800, 800))
                        images.append(img)
                    prompt_img = f"Hôm nay là {current_time_str} (Giờ Việt Nam). Đọc TẤT CẢ các bill trong các ảnh được cung cấp. Gộp chung tất cả các món ăn lại thành một danh sách duy nhất. Tìm ngày giờ hóa đơn (lấy ngày giờ của bill đầu tiên hoặc rõ ràng nhất). Trả về đúng định dạng:\nDòng 1: NGÀY: dd/mm/yyyy hh:mm\nCác dòng sau: TÊN|GIÁ|SL"
                    res = client.models.generate_content(model='gemini-2.5-flash', contents=[prompt_img] + images)
                    for line in res.text.strip().split('\n'):
                        line = line.strip()
                        if line.upper().startswith("NGÀY:"): st.session_state.ai_date = line[5:].strip()
                        else:
                            p = line.split('|')
                            if len(p) == 3: st.session_state.current_items.append({"name": p[0], "price": parse_amount(p[1]), "qty": int(p[2])})
                    st.rerun()
                except Exception as e: st.error(e)
            
    with c_ai2:
        txt_ai = st.text_area("💬 Dán tin nhắn của bạn ở đây:")
        if txt_ai and st.button("✨ Phân tích chữ", type="primary"):
            # THÊM SPINNER Ở ĐÂY
            with st.spinner("🤖 AI đang phân tích tin nhắn..."):
                try:
                    prompt_txt = f"Hôm nay là {current_time_str}. Đọc tin nhắn, tự suy luận ngày giờ. Trả về đúng định dạng:\nDòng 1: NGÀY: dd/mm/yyyy hh:mm\nCác dòng sau: TÊN|GIÁ|SL\n\nTin nhắn: {txt_ai}"
                    res = client.models.generate_content(model='gemini-2.5-flash', contents=prompt_txt)
                    for line in res.text.strip().split('\n'):
                        line = line.strip()
                        if line.upper().startswith("NGÀY:"): st.session_state.ai_date = line[5:].strip()
                        else:
                            p = line.split('|')
                            if len(p) == 3: st.session_state.current_items.append({"name": p[0], "price": parse_amount(p[1]), "qty": int(p[2])})
                    st.rerun()
                except Exception as e: st.error(e)
                
    st.divider()
    st.subheader("📝 Nhập món lẻ (tuỳ chọn)")
    i_c1, i_c2, i_c3, i_c4 = st.columns([4, 3, 2, 2])
    im_n = i_c1.text_input("Tên món:")
    im_p = i_c2.text_input("Giá (VD: 50k, 200...):")
    im_q = i_c3.number_input("SL", 1, 100, 1)
    
    with i_c4:
        st.markdown("<div style='margin-top: 28.5px;'></div>", unsafe_allow_html=True)
        if st.button("➕ Thêm", type="primary", use_container_width=True):
            p = parse_amount(im_p)
            if im_n and p > 0: st.session_state.current_items.append({"name": im_n, "price": p, "qty": im_q}); st.rerun()

    total_bill = 0
    if st.session_state.current_items:
        st.write("---")
        st.write("**📝 Danh sách món:**")
        for idx, it in enumerate(st.session_state.current_items):
            col_n, col_p, col_q, col_del = st.columns([4, 3, 2, 1])
            new_name = col_n.text_input("Tên món", value=it['name'], key=f"edit_n_{idx}", label_visibility="collapsed")
            new_price_str = col_p.text_input("Giá", value=str(it['price']), key=f"edit_p_{idx}", label_visibility="collapsed")
            new_qty = col_q.number_input("SL", value=it['qty'], min_value=1, key=f"edit_q_{idx}", label_visibility="collapsed")
            new_price = parse_amount(new_price_str)
            st.session_state.current_items[idx] = {"name": new_name, "price": new_price, "qty": new_qty}
            total_bill += new_price * new_qty
            if col_del.button("❌", key=f"deli_{idx}"): 
                st.session_state.current_items.pop(idx)
                st.rerun()

    st.write("---")
    c_info1, c_info2 = st.columns(2)
    b_title = c_info1.text_input("Tiêu đề bill:", value="Đi ăn")
    b_date = c_info2.text_input("Thời gian:", value=st.session_state.get("ai_date", datetime.now().strftime("%d/%m/%Y %H:%M")))

    if total_bill == 0:
        q_amt = st.text_input("💰 Nhập tổng bill nhanh ở đây:", value="0")
        total_bill = parse_amount(q_amt)

    st.write("---")
    st.markdown(f"#### 💳 Ai thanh toán? (Tổng: {format_vn(total_bill)}đ)")
    all_members = list(st.session_state.members.keys())
    
    selected_payers = st.multiselect("Chọn người đã ứng tiền:", all_members, default=[my_nick] if my_nick in all_members else [], format_func=lambda x: f"Bản thân ({x})" if x == my_nick else x, key="multi_payer_select")

    payer_data = {}
    if len(selected_payers) > 1:
        pay_method = st.radio("Cách chia tiền trả:", ["Chia đều", "Theo tỉ lệ (%)", "Số tiền cụ thể"], horizontal=True)
        if pay_method == "Chia đều":
            each_pay = total_bill / len(selected_payers)
            for p in selected_payers: payer_data[p] = each_pay
        elif pay_method == "Theo tỉ lệ (%)":
            cols = st.columns(len(selected_payers))
            for i, p in enumerate(selected_payers):
                pct = cols[i].number_input(f"% của {p}", min_value=0, max_value=100, value=0, key=f"pct_{p}")
                payer_data[p] = (pct / 100) * total_bill
        elif pay_method == "Số tiền cụ thể":
            cols = st.columns(len(selected_payers))
            for i, p in enumerate(selected_payers):
                amt = cols[i].number_input(f"Tiền {p} ứng ra", min_value=0, value=0, step=1000, key=f"amt_pay_{p}")
                payer_data[p] = amt
    elif len(selected_payers) == 1:
        payer_data[selected_payers[0]] = total_bill

    st.write("---")
    st.markdown("#### 🍴 Ai tham gia ăn?")
    use_g = st.selectbox("Chọn nhóm (để tick nhanh):", ["-- Chọn lẻ --"] + list(st.session_state.groups.keys()))
    def_m = list(st.session_state.members.keys())
    if use_g != "-- Chọn lẻ --": def_m = st.session_state.groups[use_g]
    b_cons = st.multiselect("Danh sách người ăn:", def_m, default=def_m, format_func=lambda x: f"Bản thân ({x})" if x == my_nick else x)

    if b_cons and total_bill > 0:
        method = st.radio("Cách chia tiền ăn:", ["Chia đều", "Chia theo món lẻ", "Nhập riêng", "Chia %"], horizontal=True)
        splits = {c: 0 for c in b_cons}
        if method == "Chia theo món lẻ" and st.session_state.current_items:
            pool = 0
            for idx, it in enumerate(st.session_state.current_items):
                st.write(f"🍴 {it['name']}")
                who = st.multiselect(f"Ai ăn {it['name']}?", b_cons, key=f"w_{idx}")
                if who:
                    p_v = (it['price']*it['qty'])/len(who)
                    for w in who: splits[w] += p_v
                else: pool += it['price']*it['qty']
            if pool > 0:
                for c in b_cons: splits[c] += (pool/len(b_cons))
        elif method == "Chia đều":
            for c in b_cons: splits[c] = total_bill / len(b_cons)

        has_deadline = st.checkbox("📅 Đặt hạn chót thanh toán cho bill này?")
        b_deadline = None
        if has_deadline: b_deadline = st.date_input("Chọn ngày hạn chót:", value=datetime.now().date()).strftime("%d/%m/%Y")

        if st.button("💾 LƯU SỔ NỢ", type="primary", use_container_width=True):
            if not selected_payers: st.error("Phải có người trả tiền!")
            elif sum(payer_data.values()) != total_bill: st.error("Vui lòng nhập tiền trả khớp với tổng bill!")
            else:
                st.session_state.history.append({
                    "id": time.time(), 
                    "date": b_date,
                    "deadline": b_deadline, 
                    "name": b_title, 
                    "amount": total_bill, 
                    "payer": selected_payers[0] if len(selected_payers) == 1 else "Nhóm trả", 
                    "payer_data": payer_data,
                    "splits": splits, 
                    "status": "unpaid", 
                    "paid_by": [],
                    "items": st.session_state.current_items.copy()
                })
                st.session_state.current_items = []
                st.session_state.ai_date = datetime.now().strftime("%d/%m/%Y %H:%M")
                save_data()
                
                st.balloons()
                st.success("🎉 LƯU THÀNH CÔNG! Đang cập nhật lại hệ thống...")
                time.sleep(1.5)
                st.rerun()

# --- TAB 3: CHỐT SỔ ---
with tab3:
    today = datetime.now().date()
    urgent_alerts = []
    unpaid = [b for b in st.session_state.history if b['status'] == 'unpaid']

    for b in unpaid:
        if b.get('deadline'):
            try:
                dl_date = datetime.strptime(b['deadline'], "%d/%m/%Y").date()
                days_left = (dl_date - today).days
                if 0 <= days_left <= 7:
                    urgent_alerts.append({"name": b['name'], "days": days_left, "deadline": b['deadline'], "amount": b['amount']})
            except: pass

    if urgent_alerts:
        st.markdown("### 🔔 Nhắc nhở hạn chót")
        for alert in urgent_alerts:
            msg = f"Sắp tới hạn! Bill **{alert['name']}** ({format_vn(alert['amount'])}đ) "
            if alert['days'] == 0: st.error(f"🚨 {msg} phải trả vào **HÔM NAY**!")
            else: st.warning(f"⏰ {msg} còn **{alert['days']} ngày** nữa (Hạn: {alert['deadline']})")
        st.write("---")

    if not unpaid:
        st.success("Tất cả hóa đơn đã thanh toán xong! 🎉")
    else:
        st.subheader("⚙️ Tùy chọn chốt nợ")
        use_netting = st.toggle("🔀 Bật tính nhanh nợ chéo (Bù trừ nợ qua lại)", value=False)
        msg_out = "📣 TỔNG KẾT CHỐT SỔ SÒNG PHẲNG:\n"
        
        matrix = {m1: {m2: 0 for m2 in st.session_state.members} for m1 in st.session_state.members}
        details = {m1: {m2: [] for m2 in st.session_state.members} for m1 in st.session_state.members}
        debts_dict = {}

        for b in unpaid:
            p_data = b.get('payer_data', {b.get('payer', ''): b.get('amount', 0)})
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
                            details[debtor][creditor].append({"date": b['date'], "name": b['name'], "amount": amt, "deadline": b.get('deadline'), "b_id": b.get('id')})
        
        if not use_netting:
            if debts_dict:
                for (d, c), items in debts_dict.items():
                    msg_out += f"👉 {d} nợ {c}: {int(sum(it['amount'] for it in items)):,}đ\n"
            else: msg_out += "Hiện không có khoản nợ nào.\n"
        else:
            net_bal = {m: 0 for m in st.session_state.members}
            for d in matrix:
                for c in matrix[d]:
                    net_bal[c] += matrix[d][c]
                    net_bal[d] -= matrix[d][c]
            debtors_l = [[m, abs(v)] for m, v in net_bal.items() if v < -1]
            creditors_l = [[m, v] for m, v in net_bal.items() if v > 1]
            if not debtors_l: msg_out += "Không có khoản nợ nào cần bù trừ.\n"
            else:
                while debtors_l and creditors_l:
                    debtors_l.sort(key=lambda x: x[1], reverse=True); creditors_l.sort(key=lambda x: x[1], reverse=True)
                    d_n, d_a = debtors_l[0]; c_n, c_a = creditors_l[0]
                    s_a = min(d_a, c_a)
                    msg_out += f"✨ {d_n} chuyển thẳng cho {c_n}: {int(s_a):,}đ\n"
                    debtors_l[0][1] -= s_a; creditors_l[0][1] -= s_a
                    if debtors_l[0][1] < 1: debtors_l.pop(0)
                    if creditors_l[0][1] < 1: creditors_l.pop(0)
        
        msg_out += "\n(Mọi người vào web check bill và chuyển khoản nha💸)"
        with st.expander("📋 Lấy tin nhắn gửi nhóm (Copy nhanh)"): st.code(msg_out, language="text")
        
        st.write("---")

        # KHU VỰC HIỂN THỊ MÃ QR VÀ NÚT XÁC NHẬN TRẢ TIỀN
        if not use_netting:
            st.markdown("### 📜 Danh sách nợ chi tiết")
            for (debtor, creditor), items in debts_dict.items():
                total_owed = sum(item['amount'] for item in items)
                with st.expander(f"🔴 **{debtor}** nợ **{creditor}**: {format_vn(total_owed)}đ"):
                    for item in items:
                        st.write(f"- {item['date']} | {item['name']} | **{format_vn(item['amount'])}đ**")
                        if item.get('deadline'): 
                            dl_date = datetime.strptime(item['deadline'], "%d/%m/%Y").date()
                            if datetime.now().date() > dl_date: st.markdown(f"&nbsp;&nbsp;⚠️ <span style='color:red;'>QUÁ HẠN ({item['deadline']})</span>", unsafe_allow_html=True)
                            else: st.caption(f"&nbsp;&nbsp;⏰ Hạn: {item['deadline']}")
                    
                    st.write("---")
                    c_info = st.session_state.members.get(creditor, {"bank": "Chưa rõ", "acc": "Chưa rõ"})
                    if c_info['bank'] and c_info['acc']:
                        qr_url = f"https://img.vietqr.io/image/{c_info['bank']}-{c_info['acc']}-compact2.png?amount={int(total_owed)}&addInfo={debtor}chuyen"
                        st.image(qr_url, caption="QR Chuyển khoản", width=250)
                    
                    if st.button(f"✅ Xác nhận {debtor} đã trả xong cho {creditor}", key=f"pay_{debtor}_{creditor}"):
                        item_ids = [it['b_id'] for it in items]
                        for b in st.session_state.history:
                            if b.get('id') in item_ids and b['status'] == 'unpaid':
                                if 'paid_by' not in b: b['paid_by'] = []
                                if debtor not in b['paid_by']: b['paid_by'].append(debtor)
                                
                                t_p_data = b.get('payer_data', {b.get('payer', ''): b.get('amount', 0)})
                                t_bals = {}
                                for p, a in t_p_data.items():
                                    if p not in b['paid_by']: t_bals[p] = t_bals.get(p, 0) + a
                                for c, a in b['splits'].items():
                                    if c not in b['paid_by']: t_bals[c] = t_bals.get(c, 0) - a
                                if not any(v < -1 for v in t_bals.values()): b['status'] = 'paid'
                        save_data(); st.rerun()
        else:
            st.markdown("### 🔀 Kết quả bù trừ nợ chéo")
            all_members = list(st.session_state.members.keys())
            found_netting = False
            for i in range(len(all_members)):
                for j in range(i + 1, len(all_members)):
                    m1, m2 = all_members[i], all_members[j]
                    if matrix[m1][m2] > matrix[m2][m1]:
                        net_amt = matrix[m1][m2] - matrix[m2][m1]
                        if net_amt > 1:
                            found_netting = True
                            with st.expander(f"👉 **{m1}** cần chuyển **{m2}**: {format_vn(net_amt)}đ"):
                                st.write(f"**{m1} nợ {m2} tổng {format_vn(matrix[m1][m2])}đ từ:**")
                                for p in details[m1][m2]: st.write(f"- (+) {p['name']} ({format_vn(p['amount'])}đ)")
                                if matrix[m2][m1] > 0:
                                    st.write(f"**Được trừ {format_vn(matrix[m2][m1])}đ do nợ ngược lại từ:**")
                                    for n in details[m2][m1]: st.write(f"- (-) {n['name']} ({format_vn(n['amount'])}đ)")
                                
                                c_info = st.session_state.members.get(m2, {"bank":"", "acc":""})
                                if c_info['bank'] and c_info['acc']:
                                    st.image(f"https://img.vietqr.io/image/{c_info['bank']}-{c_info['acc']}-compact2.png?amount={int(net_amt)}&addInfo={m1}chuyen", width=250)
                                if st.button(f"✅ Xác nhận {m1} chuyển xong", key=f"net_{m1}_{m2}"):
                                    b_ids = [it['b_id'] for it in details[m1][m2]]
                                    for b in st.session_state.history:
                                        if b.get('id') in b_ids and b['status'] == 'unpaid':
                                            if 'paid_by' not in b: b['paid_by'] = []
                                            if m1 not in b['paid_by']: b['paid_by'].append(m1)
                                            t_p = b.get('payer_data', {b.get('payer', ''): b.get('amount', 0)})
                                            t_b = {}
                                            for p, a in t_p.items():
                                                if p not in b['paid_by']: t_b[p] = t_b.get(p, 0) + a
                                            for c, a in b['splits'].items():
                                                if c not in b['paid_by']: t_b[c] = t_b.get(c, 0) - a
                                            if not any(v < -1 for v in t_b.values()): b['status'] = 'paid'
                                    save_data(); st.rerun()
                                    
                    elif matrix[m2][m1] > matrix[m1][m2]:
                        net_amt = matrix[m2][m1] - matrix[m1][m2]
                        if net_amt > 1:
                            found_netting = True
                            with st.expander(f"👉 **{m2}** cần chuyển **{m1}**: {format_vn(net_amt)}đ"):
                                st.write(f"**{m2} nợ {m1} tổng {format_vn(matrix[m2][m1])}đ từ:**")
                                for p in details[m2][m1]: st.write(f"- (+) {p['name']} ({format_vn(p['amount'])}đ)")
                                if matrix[m1][m2] > 0:
                                    st.write(f"**Được trừ {format_vn(matrix[m1][m2])}đ do nợ ngược lại từ:**")
                                    for n in details[m1][m2]: st.write(f"- (-) {n['name']} ({format_vn(n['amount'])}đ)")
                                
                                c_info = st.session_state.members.get(m1, {"bank":"", "acc":""})
                                if c_info['bank'] and c_info['acc']:
                                    st.image(f"https://img.vietqr.io/image/{c_info['bank']}-{c_info['acc']}-compact2.png?amount={int(net_amt)}&addInfo={m2}chuyen", width=250)
                                if st.button(f"✅ Xác nhận {m2} chuyển xong", key=f"net_{m2}_{m1}"):
                                    b_ids = [it['b_id'] for it in details[m2][m1]]
                                    for b in st.session_state.history:
                                        if b.get('id') in b_ids and b['status'] == 'unpaid':
                                            if 'paid_by' not in b: b['paid_by'] = []
                                            if m2 not in b['paid_by']: b['paid_by'].append(m2)
                                            t_p = b.get('payer_data', {b.get('payer', ''): b.get('amount', 0)})
                                            t_b = {}
                                            for p, a in t_p.items():
                                                if p not in b['paid_by']: t_b[p] = t_b.get(p, 0) + a
                                            for c, a in b['splits'].items():
                                                if c not in b['paid_by']: t_b[c] = t_b.get(c, 0) - a
                                            if not any(v < -1 for v in t_b.values()): b['status'] = 'paid'
                                    save_data(); st.rerun()

            if not found_netting: st.info("Hiện không có cặp nào có thể bù trừ nợ cho nhau.")

# --- TAB 4: NHẬT KÝ ---
with tab4:
    st.subheader("🕒 Lịch sử hóa đơn gốc")
    
    # ĐỊNH NGHĨA POP-UP XÁC NHẬN XÓA (Tính năng mới của Streamlit)
    @st.dialog("⚠️ Xác nhận xóa hóa đơn")
    def confirm_delete_bill(real_index, bill_name):
        st.write(f"Bạn có chắc chắn muốn xóa bill **{bill_name}** không?")
        st.write("Hành động này không thể hoàn tác và sẽ làm thay đổi sổ nợ của cả nhóm!")
        c1, c2 = st.columns(2)
        if c1.button("Hủy bỏ", use_container_width=True):
            st.rerun()
        if c2.button("Xóa luôn!", type="primary", use_container_width=True):
            st.session_state.history.pop(real_index)
            save_data()
            st.toast("Đã xóa hóa đơn thành công!", icon="✅")
            st.rerun()

    if not st.session_state.history:
        st.markdown("<h3 style='text-align: center; color: #ff4b4b; padding: 50px 0;'>🙌🙌🙌 Chưa có hoá đơn, lên kèo đi chơi thôi!!! 🙌🙌🙌</h3>", unsafe_allow_html=True)
    else:
        # BỘ LỌC VÀ SẮP XẾP BILL
        filter_col1, filter_col2 = st.columns(2)
        status_filter = filter_col1.selectbox("Bộ lọc trạng thái:", ["Tất cả", "🔴 Đang nợ", "✅ Đã thanh toán xong"])
        sort_order = filter_col2.radio("Sắp xếp theo:", ["Mới nhất trước", "Cũ nhất trước"], horizontal=True)
        
        st.write("---")
        
        # Áp dụng logic lọc dữ liệu
        display_history = []
        for i, b in enumerate(st.session_state.history):
            b_status = b.get('status', 'unpaid')
            if status_filter == "🔴 Đang nợ" and b_status == 'paid': continue
            if status_filter == "✅ Đã thanh toán xong" and b_status == 'unpaid': continue
            display_history.append((i, b)) # Lưu lại index thật để xóa không bị nhầm
            
        if sort_order == "Mới nhất trước":
            display_history = list(reversed(display_history))
            
        if not display_history:
            st.info("Không có hóa đơn nào khớp với bộ lọc của bạn.")
        
        # Hiển thị các bill sau khi lọc
        for real_index, b in display_history:
            # Nếu bill đã trả xong, hiện thêm chữ (Đã xong) lên tiêu đề cho dễ nhìn
            is_done_text = " (Đã xong ✅)" if b.get('status') == 'paid' else ""
            
            with st.expander(f"[{b['date']}] {b['name']} - {format_vn(b['amount'])}đ{is_done_text}"):
                p_data_str = ", ".join([f"{k} ({format_vn(v)}đ)" for k,v in b.get('payer_data', {b.get('payer', ''): b.get('amount', 0)}).items()])
                st.write(f"**Nguồn tiền:** {p_data_str}")
                for p, amt in b['splits'].items():
                    if amt > 0:
                        status = "✅ Xong" if p in b.get('paid_by', []) or b.get('status') == 'paid' else "🔴 Nợ"
                        st.write(f"- {p} ăn: {format_vn(amt)}đ ({status})")
                
                st.write("---")
                # Nút bấm giờ sẽ gọi cái Pop-up xác nhận ở trên ra chứ không xóa ngang nữa
                if st.button(f"🗑️ Xóa bill này", key=f"del_b_{b['id']}", type="primary"):
                    confirm_delete_bill(real_index, b['name'])

# --- TAB 5: WRAPPED & ANALYTICS ---
with tab5:
    my_nick = st.session_state.get('nickname', 'Bạn')
    st.markdown(f"<h2 style='text-align: center; color: #ff4b4b;'>🎉 Share Bills Wrapped - {my_nick}</h2>", unsafe_allow_html=True)
    
    if not st.session_state.history:
        st.info("Chưa có dữ liệu. Hãy ghi bill để mở khóa báo cáo!")
    else:
        # TÍNH NĂNG THỐNG KÊ CHI TIẾT
        time_filter = st.radio("⏳ Mốc thời gian:", ["Tháng này (Tháng 4)", "Từ đầu năm (2026)"], horizontal=True)
        filtered_history = []
        for b in st.session_state.history:
            try:
                match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', str(b['date']))
                if match:
                    d_m, d_y = int(match.group(2)), int(match.group(3))
                    if ("Tháng này" in time_filter and d_m == 4 and d_y == 2026) or ("đầu năm" in time_filter and d_y == 2026):
                        filtered_history.append(b)
            except: pass

        if not filtered_history: st.warning("Không có dữ liệu trong khoảng thời gian này.")
        else:
            my_spent = 0
            others_owe_me = {}
            i_owe_others = {}
            group_stats = {}
            all_unpaid_debts = []
            my_nick_lower = my_nick.strip().lower()

            for b in filtered_history:
                splits = b.get('splits', {})
                paid_by = b.get('paid_by', [])
                p_data = b.get('payer_data', {b.get('payer', ''): b.get('amount', 0)})
                
                my_name_in_bill = None
                for name in set(list(splits.keys()) + list(p_data.keys())):
                    if name.strip().lower() == my_nick_lower:
                        my_name_in_bill = name; break

                if my_name_in_bill in splits: my_spent += splits[my_name_in_bill]
                
                if b.get('status') == 'unpaid':
                    bals = {}
                    for p, a in p_data.items():
                        if p not in paid_by: bals[p] = bals.get(p, 0) + a
                    for c, a in splits.items():
                        if c not in paid_by: bals[c] = bals.get(c, 0) - a
                        
                    pos_bals = {k: v for k, v in bals.items() if v > 1000}
                    neg_bals = {k: v for k, v in bals.items() if v < -1000}
                    tot_pos = sum(pos_bals.values())
                    
                    if my_name_in_bill in bals and tot_pos > 0:
                        my_bal = bals[my_name_in_bill]
                        if my_bal > 1000:
                            for k, v in neg_bals.items(): others_owe_me[k] = others_owe_me.get(k, 0) + abs(v) * (my_bal / tot_pos)
                        elif my_bal < -1000:
                            for k, v in pos_bals.items(): i_owe_others[k] = i_owe_others.get(k, 0) + abs(my_bal) * (v / tot_pos)

                    if tot_pos > 0:
                        for d_name, d_bal in neg_bals.items():
                            for c_name, c_bal in pos_bals.items():
                                owed_amt = abs(d_bal) * (c_bal / tot_pos)
                                if owed_amt > 1000: all_unpaid_debts.append({"debtor": d_name, "creditor": c_name, "amount": int(owed_amt), "item": b.get('name', 'Bill')})

                gn = "Nhóm chung"
                for name, members in st.session_state.groups.items():
                    if set(splits.keys()) == set(members): gn = name; break
                if gn not in group_stats: group_stats[gn] = {"count": 0, "money": 0}
                group_stats[gn]["count"] += 1
                group_stats[gn]["money"] += b.get('amount', 0)

            st.markdown(f"### 📊 Dashboard của {my_nick}")
            c1, c2, c3 = st.columns(3)
            c1.metric("Tiền bạn đã chi", f"{format_vn(my_spent)}đ")
            
            tot_o_me = sum(others_owe_me.values())
            tot_i_o = sum(i_owe_others.values())
            
            m_debtor = max(others_owe_me, key=others_owe_me.get) if others_owe_me else "Không ai"
            if m_debtor != "Không ai": c2.metric("Nợ bạn nhiều nhất", m_debtor, f"{format_vn(others_owe_me.get(m_debtor, 0))}đ / Tổng: {format_vn(tot_o_me)}đ", delta_color="normal")
            else: c2.metric("Nợ bạn nhiều nhất", "Không ai", "0đ / Tổng: 0đ", delta_color="off")
            
            m_creditor = max(i_owe_others, key=i_owe_others.get) if i_owe_others else "Không ai"
            if m_creditor != "Không ai": c3.metric("Bạn nợ nhiều nhất", m_creditor, f"-{format_vn(i_owe_others.get(m_creditor, 0))}đ / Tổng: -{format_vn(tot_i_o)}đ", delta_color="inverse")
            else: c3.metric("Bạn nợ nhiều nhất", "Không ai", "0đ / Tổng: 0đ", delta_color="off")

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
            else: st.info("Sổ nợ trống, không có gì để vẽ biểu đồ cả! 🎉")
