import streamlit as st
import json
import os
import re
import time
from datetime import datetime
from google import genai
import PIL.Image

# --- 1. CÀI ĐẶT TRANG CƠ BẢN ---
st.set_page_config(page_title="Sòng Phẳng Super Ultimate", page_icon="💸", layout="wide")

# Lấy Key từ Secrets
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=API_KEY)
except Exception as e:
    client = None

# --- 2. HỆ THỐNG ĐĂNG NHẬP / ĐĂNG KÝ ---
USERS_FILE = 'users.json'

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f: return json.load(f)
    return {}

def save_users(users_data):
    with open(USERS_FILE, 'w', encoding='utf-8') as f: json.dump(users_data, f)

# Khởi tạo biến users ở NGOÀI CÙNG để không bao giờ bị lỗi NameError
users = load_users()

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ''
    st.session_state.nickname = ''

# GIAO DIỆN ĐĂNG NHẬP (Chỉ hiện khi chưa login)
if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center;'>🔐 Đăng nhập Sòng Phẳng</h1>", unsafe_allow_html=True)
    tab_login, tab_reg = st.tabs(["Đăng nhập", "Đăng ký"])
    
    with tab_login:
        l_user = st.text_input("Tài khoản:")
        l_pass = st.text_input("Mật khẩu:", type="password")
        if st.button("🚀 Đăng nhập", type="primary", use_container_width=True):
            if l_user in users:
                user_data = users[l_user]
                stored_pass = user_data["pass"] if isinstance(user_data, dict) else user_data
                if l_pass == stored_pass:
                    st.session_state.logged_in = True
                    st.session_state.username = l_user
                    st.session_state.nickname = user_data.get("nickname", l_user) if isinstance(user_data, dict) else l_user
                    st.rerun()
                else:
                    st.error("Sai mật khẩu!")
            else:
                st.error("Tài khoản không tồn tại!")
                
    with tab_reg:
        r_user = st.text_input("Tên đăng nhập (ID):", key="reg_id")
        r_pass = st.text_input("Mật khẩu:", type="password", key="reg_pass")
        r_nick = st.text_input("Bạn muốn được gọi là gì? (Ví dụ: Trúc Lâm)", key="reg_nick")
        
        if st.button("📝 Đăng ký tài khoản", use_container_width=True):
            if r_user in users: 
                st.error("ID này đã tồn tại!")
            elif r_user and r_pass and r_nick:
                users[r_user] = {"pass": r_pass, "nickname": r_nick}
                save_users(users)
                st.success("Đăng ký thành công! Mời bạn qua tab Đăng nhập.")
            else: 
                st.warning("Vui lòng điền đủ 3 thông tin!")
                
    st.stop() # <--- CỰC KỲ QUAN TRỌNG: Chặn không cho web chạy tiếp nếu chưa login

# --- 3. CHUẨN BỊ DỮ LIỆU & GIAO DIỆN CHÍNH (Chạy sau khi đã login) ---
DATA_FILE = f'data_{st.session_state.username}.json'

# Sidebar - Hiển thị Nickname
st.sidebar.markdown(f"### ✨ Xin chào, **{st.session_state.get('nickname', 'Bạn')}**!")
if st.sidebar.button("🚪 Đăng xuất"):
    st.session_state.logged_in = False
    st.session_state.username = ''
    st.session_state.nickname = ''
    st.rerun()

# ... (Từ đây trở xuống giữ nguyên cụm load_data(), save_data() và 4 Tab như cũ) ...

API_KEY = st.secrets["GEMINI_API_KEY"]

try:
    client = genai.Client(api_key=API_KEY)
except:
    client = None
    
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            st.session_state.members = data.get('members', {})
            st.session_state.groups = data.get('groups', {})
            st.session_state.history = data.get('history', [])
    else:
        st.session_state.members, st.session_state.groups, st.session_state.history = {}, {}, []

def save_data():
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump({'members': st.session_state.members, 'groups': st.session_state.groups, 'history': st.session_state.history}, f, ensure_ascii=False, indent=4)

if 'members' not in st.session_state: load_data()

# --- 2. HÀM BỔ TRỢ ---
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

# --- TAB 1: DANH BẠ & NHÓM ---
with tab1:
    my_nick = st.session_state.get('nickname', 'Bản thân')
    st.markdown(f"### 👤 Thông tin cá nhân ({my_nick})")
    
    # Đảm bảo có entry cho bản thân trong members
    if my_nick not in st.session_state.members:
        st.session_state.members[my_nick] = {"bank": "", "acc": ""}

   with st.expander("Sửa thông tin nhận tiền của bạn (Để người khác quét QR)"):
        # Chia làm 2 cột cho UI gọn gàng, đẹp mắt
        c1, c2 = st.columns(2)
        
        # 1. Danh sách các ngân hàng phổ biến
        bank_list = ["", "MB", "VCB", "TPB", "BIDV", "TCB", "VPB", "CTG", "ACB", "SHB", "STB", "VIB"]
        
        # 2. Lấy dữ liệu cũ một cách an toàn bằng hàm .get()
        saved_bank = st.session_state.members[nickname].get('bank', '')
        saved_acc = st.session_state.members[nickname].get('acc', '')
        
        # 3. Tìm vị trí của ngân hàng cũ. Nếu chưa có hoặc nhập sai thì để mặc định là 0 (ô trống)
        default_idx = bank_list.index(saved_bank) if saved_bank in bank_list else 0
        
        # 4. Gắn vào Selectbox và Text_input
        my_bank = c1.selectbox("Ngân hàng:", bank_list, index=default_idx)
        my_acc = c2.text_input("Số tài khoản:", value=saved_acc)
        
        if st.button("Cập nhật thông tin bản thân"):
            st.session_state.members[nickname] = {"bank": my_bank, "acc": my_acc}
            save_data()
            st.toast("Đã cập nhật số tài khoản thành công!", icon="✅")
            st.rerun()
    
    st.write("---")
    st.markdown("### 👥 Quản lý Bạn bè & Nhóm")
    # (Các phần Thêm bạn, Thêm nhóm bên dưới giữ nguyên nhưng lọc bỏ nickname khỏi danh sách "Thêm bạn")
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.subheader("👤 Thành Viên")
        n_name = st.text_input("Tên mới:")
        n_bank = st.selectbox("Ngân hàng:", ["", "MB", "VCB", "TPB", "BIDV", "TCB", "VPB", "CTG"])
        # Thêm thuộc tính key=f"acc_{name}" (hoặc biến tên tương ứng trong vòng lặp của bạn)
        n_acc = st.text_input("Số tài khoản:", value=info['acc'], key=f"acc_input_{name}")
        if st.button("➕ Lưu người mới"):
            if n_name: st.session_state.members[n_name] = {"bank": n_bank, "acc": n_acc}; save_data(); st.rerun()
        
        if st.session_state.members:
            with st.expander("📝 Sửa/Xóa thành viên"):
                m_edit = st.selectbox("Chọn người:", list(st.session_state.members.keys()))
                eb = st.text_input("Ngân hàng mới:", value=st.session_state.members[m_edit]['bank'])
                ea = st.text_input("STK mới:", value=st.session_state.members[m_edit]['acc'])
                if st.button("💾 Lưu sửa"):
                    st.session_state.members[m_edit] = {"bank": eb, "acc": ea}; save_data(); st.rerun()
                if st.button("🗑️ Xóa người"):
                    del st.session_state.members[m_edit]; save_data(); st.rerun()

    with col_m2:
        st.subheader("👨‍👩‍👧‍👦 Quản Lý Nhóm")
        g_n = st.text_input("Tên nhóm mới:")
        g_m = st.multiselect("Thành viên nhóm:", list(st.session_state.members.keys()))
        if st.button("➕ Tạo Nhóm"):
            if g_n and g_m: st.session_state.groups[g_n] = g_m; save_data(); st.rerun()
        
        if st.session_state.groups:
            with st.expander("📝 Chỉnh sửa/Xóa nhóm"):
                g_edit = st.selectbox("Chọn nhóm:", list(st.session_state.groups.keys()))
                new_gm = st.multiselect("Sửa thành viên:", list(st.session_state.members.keys()), default=st.session_state.groups[g_edit])
                if st.button("💾 Cập nhật nhóm"):
                    st.session_state.groups[g_edit] = new_gm; save_data(); st.rerun()
                if st.button("🗑️ Xóa nhóm này"):
                    del st.session_state.groups[g_edit]; save_data(); st.rerun()

# --- TAB 2: GHI HÓA ĐƠN ---
with tab2:
    if 'current_items' not in st.session_state: st.session_state.current_items = []
   
    st.subheader("🤖 Nhập liệu nhanh AI")
    c_ai1, c_ai2 = st.columns(2)
    
    # Lấy thời gian thực để bơm vào Prompt cho AI suy luận
    current_time_str = datetime.now().strftime('%d/%m/%Y %H:%M')
    
    with c_ai1:
        up_f = st.file_uploader("📸 Nhập ảnh của bạn ở đây", type=["jpg", "png", "jpeg"])
        if up_f and st.button("✨ Phân tích ảnh"):
            try:
                img = PIL.Image.open(up_f); img.thumbnail((800, 800))
                prompt_img = f"Hôm nay là {current_time_str}. Đọc bill, tìm ngày giờ hóa đơn. Trả về đúng định dạng:\nDòng 1: NGÀY: dd/mm/yyyy hh:mm\nCác dòng sau: TÊN|GIÁ|SL"
                res = client.models.generate_content(model='gemini-2.5-flash', contents=[prompt_img, img])
                
                for line in res.text.strip().split('\n'):
                    line = line.strip()
                    if line.upper().startswith("NGÀY:"):
                        st.session_state.ai_date = line[5:].strip()
                    else:
                        p = line.split('|')
                        if len(p) == 3: st.session_state.current_items.append({"name": p[0], "price": parse_amount(p[1]), "qty": int(p[2])})
                st.rerun()
            except Exception as e: st.error(e)
            
    with c_ai2:
        txt_ai = st.text_area("💬 Dán tin nhắn của bạn ở đây:")
        if txt_ai and st.button("✨ Phân tích chữ"):
            try:
                prompt_txt = f"Hôm nay là {current_time_str}. Đọc tin nhắn, tự suy luận ngày giờ đi ăn (nếu nói 'hôm qua', 'tối nay'). Trả về đúng định dạng:\nDòng 1: NGÀY: dd/mm/yyyy hh:mm\nCác dòng sau: TÊN|GIÁ|SL\n\nTin nhắn: {txt_ai}"
                res = client.models.generate_content(model='gemini-2.5-flash', contents=prompt_txt)
                
                for line in res.text.strip().split('\n'):
                    line = line.strip()
                    if line.upper().startswith("NGÀY:"):
                        st.session_state.ai_date = line[5:].strip()
                    else:
                        p = line.split('|')
                        if len(p) == 3: st.session_state.current_items.append({"name": p[0], "price": parse_amount(p[1]), "qty": int(p[2])})
                st.rerun()
            except Exception as e: st.error(e)

    st.divider()
    st.subheader("📝 Nhập món lẻ (tuỳ chọn nhá)")
    i_c1, i_c2, i_c3, i_c4 = st.columns([4, 3, 2, 2])
    im_n = i_c1.text_input("Tên món:")
    im_p = i_c2.text_input("Giá (VD: 50k, 200...):")
    im_q = i_c3.number_input("SL", 1, 100, 1)
    if i_c4.button("➕ Thêm"):
        p = parse_amount(im_p)
        if im_n and p > 0: st.session_state.current_items.append({"name": im_n, "price": p, "qty": im_q}); st.rerun()

    # --- THAY ĐOẠN CODE HIỂN THỊ MÓN ĂN CŨ BẰNG ĐOẠN NÀY ---
    total_bill = 0
    if st.session_state.current_items:
        st.write("---")
        st.write("**📝 Danh sách món (Sửa trực tiếp hoặc Xóa):**")
        for idx, it in enumerate(st.session_state.current_items):
            col_n, col_p, col_q, col_del = st.columns([4, 3, 2, 1])
            
            # Các ô nhập liệu lấy giá trị mặc định từ AI, người dùng có thể gõ đè lên để sửa
            new_name = col_n.text_input("Tên món", value=it['name'], key=f"edit_n_{idx}", label_visibility="collapsed")
            new_price_str = col_p.text_input("Giá", value=str(it['price']), key=f"edit_p_{idx}", label_visibility="collapsed")
            new_qty = col_q.number_input("SL", value=it['qty'], min_value=1, key=f"edit_q_{idx}", label_visibility="collapsed")
            
            # Tự động tính toán lại và lưu vào bộ nhớ khi bạn sửa
            new_price = parse_amount(new_price_str)
            st.session_state.current_items[idx] = {"name": new_name, "price": new_price, "qty": new_qty}
            
            total_bill += new_price * new_qty
            
            if col_del.button("❌", key=f"deli_{idx}"): 
                st.session_state.current_items.pop(idx)
                st.rerun()
    # --------------------------------------------------------
    st.write("---")
    # Tách làm 2 ô ngang nhau cho đẹp
    c_info1, c_info2 = st.columns(2)
    b_title = c_info1.text_input("Tiêu đề bill:", value="Đi ăn")
    # Hiển thị ngày giờ AI quét được, hoặc ngày giờ hiện tại nếu AI không tìm thấy
    b_date = c_info2.text_input("Thời gian (AI tự điền):", value=st.session_state.get("ai_date", datetime.now().strftime("%d/%m/%Y %H:%M")))
    b_payer = st.selectbox("Ai trả tiền?", list(st.session_state.members.keys()))
    use_g = st.selectbox("Chọn nhóm (để tick nhanh):", ["-- Chọn lẻ --"] + list(st.session_state.groups.keys()))
    def_m = list(st.session_state.members.keys())
    if use_g != "-- Chọn lẻ --": def_m = st.session_state.groups[use_g]
    b_cons = st.multiselect("Ai tham gia?", list(st.session_state.members.keys()), default=def_m)

    if total_bill == 0:
        q_amt = st.text_input("💰 Nhập tổng bill nhanh ở đây:", value="0")
        total_bill = parse_amount(q_amt)

    if b_cons and total_bill > 0:
        method = st.radio("Cách chia:", ["Chia đều", "Chia theo món lẻ", "Nhập riêng", "Chia %"], horizontal=True)
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

        st.markdown("### 👀 Xem trước (Preview)")
        for c, amt in splits.items():
            if amt > 0: st.write(f"- {c}: **{format_vn(amt)}đ**")

        # --- THÊM TÙY CHỌN DEADLINE (MẶC ĐỊNH LÀ KHÔNG CÓ) ---
    has_deadline = st.checkbox("📅 Đặt hạn chót thanh toán cho bill này?")
    b_deadline = None
    if has_deadline:
        b_deadline = st.date_input("Chọn ngày hạn chót:", value=datetime.now().date()).strftime("%d/%m/%Y")

    if b_cons and total_bill > 0:
        # ... (giữ nguyên logic method và preview) ...
        
        if st.button("💾 LƯU SỔ NỢ", type="primary"):
            st.session_state.history.append({
                "id": time.time(), 
                "date": b_date, # Dùng ngày AI bắt được (hoặc người dùng đã sửa tay)
                "deadline": b_deadline, 
                "name": b_title, 
                "amount": total_bill, 
                "payer": b_payer, 
                "splits": splits, 
                "status": "unpaid", 
                "paid_by": [],
                "items": st.session_state.current_items.copy() # Lưu items cho Wrapped Tab 5
            })
            # Reset lại dữ liệu sau khi lưu
            st.session_state.current_items = []
            st.session_state.ai_date = datetime.now().strftime("%d/%m/%Y %H:%M")
            save_data()
            st.toast("✅ Đã lưu vào sổ nợ thành công!", icon="💸")
            st.rerun()

# --- TAB 3: CHỐT SỔ (Bù trừ nợ chéo & Có Deadline) ---
with tab3:
    # 1. TRUNG TÂM NHẮC NỢ
    today = datetime.now().date()
    urgent_alerts = []

    for b in st.session_state.history:
        if b['status'] == 'unpaid' and b.get('deadline'):
            try:
                dl_date = datetime.strptime(b['deadline'], "%d/%m/%Y").date()
                days_left = (dl_date - today).days
                
                if 0 <= days_left <= 7:
                    urgent_alerts.append({
                        "name": b['name'],
                        "days": days_left,
                        "deadline": b['deadline'],
                        "payer": b['payer'],
                        "amount": b['amount']
                    })
            except Exception as e:
                pass # Bỏ qua nếu lỗi định dạng ngày

    if urgent_alerts:
        st.markdown("### 🔔 Nhắc nhở hạn chót")
        for alert in urgent_alerts:
            msg = f"Sắp tới hạn! Bill **{alert['name']}** ({format_vn(alert['amount'])}đ) "
            if alert['days'] == 0:
                st.error(f"🚨 {msg} phải trả vào **HÔM NAY**!")
            else:
                st.warning(f"⏰ {msg} còn **{alert['days']} ngày** nữa (Hạn: {alert['deadline']})")
        st.write("---")

    # 2. XỬ LÝ DANH SÁCH NỢ (Đoạn code cũ của bạn bắt đầu từ đây)
    unpaid = [b for b in st.session_state.history if b['status'] == 'unpaid']
    if not unpaid:
        st.success("Tất cả hóa đơn đã thanh toán xong! 🎉")
    else:
        st.subheader("⚙️ Tùy chọn chốt nợ")
        use_netting = st.toggle("🔀 Bật tính nhanh nợ chéo (Bù trừ nợ qua lại)", value=False)
        
        # Tự động tạo tin nhắn tổng kết để Copy
        msg = "📣 TỔNG KẾT CHỐT SỔ SÒNG PHẲNG:\n"
        
        if not use_netting:
            temp_dict = {}
            for b in unpaid:
                c = b['payer']
                p_b = b.get('paid_by', [])
                for d, a in b['splits'].items():
                    if d != c and a > 0 and d not in p_b:
                        temp_dict[(d, c)] = temp_dict.get((d, c), 0) + a
            if temp_dict:
                for (d, c), amt in temp_dict.items():
                    msg += f"👉 {d} nợ {c}: {int(amt):,}đ\n"
            else:
                msg += "Hiện không có khoản nợ nào.\n"
        else:
            bal = {m: 0 for m in st.session_state.members}
            for b in unpaid:
                c = b['payer']
                p_b = b.get('paid_by', [])
                bal[c] += (b['amount'] - b['splits'].get(c, 0))
                for d, a in b['splits'].items():
                    if d != c and a > 0 and d not in p_b:
                        bal[d] -= a
            debtors = [[m, abs(v)] for m, v in bal.items() if v < -1]
            creditors = [[m, v] for m, v in bal.items() if v > 1]
            
            if not debtors:
                msg += "Không có khoản nợ nào cần bù trừ.\n"
            else:
                while debtors and creditors:
                    debtors.sort(key=lambda x: x[1], reverse=True)
                    creditors.sort(key=lambda x: x[1], reverse=True)
                    d_n, d_a = debtors[0]
                    c_n, c_a = creditors[0]
                    s_a = min(d_a, c_a)
                    msg += f"✨ {d_n} chuyển thẳng cho {c_n}: {int(s_a):,}đ\n"
                    debtors[0][1] -= s_a
                    creditors[0][1] -= s_a
                    if debtors[0][1] < 1: debtors.pop(0)
                    if creditors[0][1] < 1: creditors.pop(0)
                
        msg += "\n(Mọi người vào web check bill chi tiết và lấy mã VietQR nha 💸)"
        
        with st.expander("📋 Lấy tin nhắn gửi nhóm (Copy nhanh)"):
            st.code(msg, language="text")

        st.write("---")

        if not use_netting:
            # CHẾ ĐỘ 1: LIỆT KÊ CHI TIẾT THEO TỪNG KHOẢN
            st.markdown("### 📜 Danh sách nợ chi tiết")
            debts_dict = {}
            for b in unpaid:
                creditor = b['payer']
                paid_by_list = b.get('paid_by', [])
                for debtor, amt in b['splits'].items():
                    if debtor != creditor and amt > 0 and debtor not in paid_by_list:
                        pair = (debtor, creditor)
                        if pair not in debts_dict: debts_dict[pair] = []
                        # Lấy thêm trường deadline từ bill gốc
                        debts_dict[pair].append({"date": b['date'], "name": b['name'], "amount": amt, "deadline": b.get('deadline')})

            for (debtor, creditor), items in debts_dict.items():
                total_owed = sum(item['amount'] for item in items)
                with st.expander(f"🔴 **{debtor}** nợ **{creditor}**: {format_vn(total_owed)}đ"):
                    for item in items:
                        st.write(f"- Ngày {item['date']} | {item['name']} | **{format_vn(item['amount'])}đ**")
                        
                        # ---> PHẦN HIỂN THỊ CẢNH BÁO DEADLINE NẰM Ở ĐÂY <---
                        if item.get('deadline'): 
                            today = datetime.now().date()
                            dl_date = datetime.strptime(item['deadline'], "%d/%m/%Y").date()
                            
                            if today > dl_date:
                                st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;⚠️ <span style='color:red; font-weight:bold;'>QUÁ HẠN (Hạn chót: {item['deadline']})</span>", unsafe_allow_html=True)
                            else:
                                st.caption(f"&nbsp;&nbsp;&nbsp;&nbsp;⏰ Hạn chót: {item['deadline']}")
                    
                    st.write("---")
                    c_info = st.session_state.members[creditor]
                    if c_info['bank'] and c_info['acc']:
                        qr_url = f"https://img.vietqr.io/image/{c_info['bank']}-{c_info['acc']}-compact2.png?amount={int(total_owed)}&addInfo={debtor}chuyentien"
                        st.image(qr_url, caption="QR Chuyển khoản", width=250)
                    
                    if st.button(f"✅ Xác nhận {debtor} đã trả xong cho {creditor}", key=f"pay_{debtor}_{creditor}"):
                        for b in st.session_state.history:
                            if b['status'] == 'unpaid' and b['payer'] == creditor and debtor in b['splits']:
                                if 'paid_by' not in b: b['paid_by'] = []
                                if debtor not in b['paid_by']: b['paid_by'].append(debtor)
                                
                                all_paid = True
                                for d, a in b['splits'].items():
                                    if d != creditor and a > 0 and d not in b['paid_by']: all_paid = False
                                if all_paid: b['status'] = 'paid'
                        save_data(); st.rerun()

        else:
            
            # CHẾ ĐỘ 2: TÍNH NHANH NỢ CHÉO (BÙ TRỪ)
            st.markdown("### 🔀 Kết quả bù trừ nợ chéo")
            matrix = {m1: {m2: 0 for m2 in st.session_state.members} for m1 in st.session_state.members}
            details = {m1: {m2: [] for m2 in st.session_state.members} for m1 in st.session_state.members}

            for b in unpaid:
                creditor = b['payer']
                paid_by = b.get('paid_by', [])
                for debtor, amt in b['splits'].items():
                    if debtor != creditor and amt > 0 and debtor not in paid_by:
                        matrix[debtor][creditor] += amt
                        # Lấy thêm trường deadline
                        details[debtor][creditor].append({"date": b['date'], "name": b['name'], "amount": amt, "deadline": b.get('deadline')})

            all_members = list(st.session_state.members.keys())
            found_netting = False
            for i in range(len(all_members)):
                for j in range(i + 1, len(all_members)):
                    m1, m2 = all_members[i], all_members[j]
                    if matrix[m1][m2] > matrix[m2][m1]:
                        net_amt = matrix[m1][m2] - matrix[m2][m1]
                        if net_amt > 1:
                            found_netting = True
                            with st.expander(f"👉 **{m1}** cần chuyển **{m2}**: {format_vn(net_amt)}đ (Đã bù trừ)"):
                                st.write(f"**{m1} nợ {m2} tổng {format_vn(matrix[m1][m2])}đ từ:**")
                                for p in details[m1][m2]: 
                                    st.write(f"- (+) {p['name']} ({format_vn(p['amount'])}đ)")
                                    # ---> DEADLINE CHO MỤC CẦN TRẢ <---
                                    if p.get('deadline'):
                                        today = datetime.now().date()
                                        dl_date = datetime.strptime(p['deadline'], "%d/%m/%Y").date()
                                        if today > dl_date:
                                            st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;⚠️ <span style='color:red; font-weight:bold;'>QUÁ HẠN (Hạn chót: {p['deadline']})</span>", unsafe_allow_html=True)
                                        else:
                                            st.caption(f"&nbsp;&nbsp;&nbsp;&nbsp;⏰ Hạn chót: {p['deadline']}")

                                if matrix[m2][m1] > 0:
                                    st.write(f"**Được trừ {format_vn(matrix[m2][m1])}đ do {m2} nợ lại {m1} từ:**")
                                    for n in details[m2][m1]: 
                                        st.write(f"- (-) {n['name']} ({format_vn(n['amount'])}đ)")
                                
                                st.write("---")
                                c_info = st.session_state.members[m2]
                                if c_info['bank'] and c_info['acc']:
                                    qr = f"https://img.vietqr.io/image/{c_info['bank']}-{c_info['acc']}-compact2.png?amount={int(net_amt)}&addInfo={m1}chuyen"
                                    st.image(qr, width=250)
                                
                                if st.button(f"✅ Xác nhận {m1} đã chuyển khoản (Bù trừ)", key=f"net_{m1}_{m2}"):
                                    for b in st.session_state.history:
                                        if b['status'] == 'unpaid':
                                            if b['payer'] == m2 and m1 in b['splits']:
                                                if 'paid_by' not in b: b['paid_by'] = []
                                                if m1 not in b['paid_by']: b['paid_by'].append(m1)
                                            if b['payer'] == m1 and m2 in b['splits']:
                                                if 'paid_by' not in b: b['paid_by'] = []
                                                if m2 not in b['paid_by']: b['paid_by'].append(m2)
                                            
                                            all_p = True
                                            for d, a in b['splits'].items():
                                                if d != b['payer'] and a > 0 and d not in b.get('paid_by', []): all_p = False
                                            if all_p: b['status'] = 'paid'
                                    save_data(); st.rerun()
                    
                    elif matrix[m2][m1] > matrix[m1][m2]:
                        net_amt = matrix[m2][m1] - matrix[m1][m2]
                        if net_amt > 1:
                            found_netting = True
                            with st.expander(f"👉 **{m2}** cần chuyển **{m1}**: {format_vn(net_amt)}đ (Đã bù trừ)"):
                                st.write(f"**{m2} nợ {m1} tổng {format_vn(matrix[m2][m1])}đ từ:**")
                                for p in details[m2][m1]: 
                                    st.write(f"- (+) {p['name']} ({format_vn(p['amount'])}đ)")
                                    # ---> DEADLINE CHO MỤC CẦN TRẢ <---
                                    if p.get('deadline'):
                                        today = datetime.now().date()
                                        dl_date = datetime.strptime(p['deadline'], "%d/%m/%Y").date()
                                        if today > dl_date:
                                            st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;⚠️ <span style='color:red; font-weight:bold;'>QUÁ HẠN (Hạn chót: {p['deadline']})</span>", unsafe_allow_html=True)
                                        else:
                                            st.caption(f"&nbsp;&nbsp;&nbsp;&nbsp;⏰ Hạn chót: {p['deadline']}")

                                if matrix[m1][m2] > 0:
                                    st.write(f"**Được trừ {format_vn(matrix[m1][m2])}đ do {m1} nợ lại {m2} từ:**")
                                    for n in details[m1][m2]: st.write(f"- (-) {n['name']} ({format_vn(n['amount'])}đ)")
                                
                                st.write("---")
                                c_info = st.session_state.members[m1]
                                if c_info['bank'] and c_info['acc']:
                                    qr = f"https://img.vietqr.io/image/{c_info['bank']}-{c_info['acc']}-compact2.png?amount={int(net_amt)}&addInfo={m2}chuyen"
                                    st.image(qr, width=250)
                                
                                if st.button(f"✅ Xác nhận {m2} đã chuyển khoản (Bù trừ)", key=f"net_{m2}_{m1}"):
                                    for b in st.session_state.history:
                                        if b['status'] == 'unpaid':
                                            if b['payer'] == m1 and m2 in b['splits']:
                                                if 'paid_by' not in b: b['paid_by'] = []
                                                if m2 not in b['paid_by']: b['paid_by'].append(m2)
                                            if b['payer'] == m2 and m1 in b['splits']:
                                                if 'paid_by' not in b: b['paid_by'] = []
                                                if m1 not in b['paid_by']: b['paid_by'].append(m1)
                                            
                                            all_p = True
                                            for d, a in b['splits'].items():
                                                if d != b['payer'] and a > 0 and d not in b.get('paid_by', []): all_p = False
                                            if all_p: b['status'] = 'paid'
                                    save_data(); st.rerun()

            if not found_netting:
                st.info("Hiện không có cặp nào có thể bù trừ nợ cho nhau.")

# --- TAB 4: NHẬT KÝ ---
with tab4:
    st.subheader("🕒 Lịch sử hóa đơn gốc")
    for b in reversed(st.session_state.history):
        with st.expander(f"[{b['date']}] {b['name']} - {format_vn(b['amount'])}đ"):
            st.write(f"**Người trả:** {b['payer']}")
            for p, amt in b['splits'].items():
                if amt > 0:
                    status = "✅ Xong" if p in b.get('paid_by', []) or b['status'] == 'paid' else "🔴 Nợ"
                    if p == b['payer']: status = "👑 Chủ chi"
                    st.write(f"- {p}: {format_vn(amt)}đ ({status})")

# --- TAB 5: WRAPPED & ANALYTICS (Dashboard Cá nhân & Nhóm) ---
with tab5:
    st.balloons()
    my_nick = st.session_state.get('nickname', 'Bạn')
    st.markdown(f"<h2 style='text-align: center; color: #ff4b4b;'>🎉 Sòng Phẳng Wrapped - {my_nick}</h2>", unsafe_allow_html=True)
    
    if not st.session_state.history:
        st.info("Chưa có dữ liệu. Hãy ghi bill để mở khóa báo cáo!")
    else:
        # 1. BỘ LỌC THỜI GIAN
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

        if not filtered_history:
            st.warning("Không có dữ liệu trong khoảng thời gian này.")
        else:
            # 2. TÍNH TOÁN LOGIC
            my_spent = 0
            others_owe_me = {}
            i_owe_others = {}
            group_stats = {}
            all_unpaid_debts = []

            for b in filtered_history:
                p = b['payer']
                splits = b['splits']
                paid_by = b.get('paid_by', [])
                
                # Chi tiêu của tôi
                if my_nick in splits: my_spent += splits[my_nick]
                
                # Nợ nần liên quan đến tôi
                if b['status'] == 'unpaid':
                    if p == my_nick:
                        for d, a in splits.items():
                            if d != my_nick and d not in paid_by: others_owe_me[d] = others_owe_me.get(d, 0) + a
                    elif my_nick in splits and my_nick not in paid_by:
                        i_owe_others[p] = i_owe_others.get(p, 0) + splits[my_nick]
                
                # Xếp hạng nợ tổng quát (Cho bảng dưới cùng)
                if b['status'] == 'unpaid':
                    for d, a in splits.items():
                        if d != p and d not in paid_by:
                            all_unpaid_debts.append({"debtor": d, "creditor": p, "amount": a, "item": b['name']})

                # Thống kê nhóm (Leaderboard)
                gn = "Nhóm chung"
                for name, members in st.session_state.groups.items():
                    if set(splits.keys()) == set(members): gn = name; break
                
                if gn not in group_stats: group_stats[gn] = {"count": 0, "money": 0}
                group_stats[gn]["count"] += 1
                group_stats[gn]["money"] += b['amount']

            # 3. HIỂN THỊ DASHBOARD CÁ NHÂN
            st.markdown(f"### 📊 Dashboard của {my_nick}")
            c1, c2, c3 = st.columns(3)
            c1.metric("Tiền bạn đã ăn", f"{format_vn(my_spent)}đ")
            
            m_debtor = max(others_owe_me, key=others_owe_me.get) if others_owe_me else "Không ai"
            c2.metric("Nợ bạn nhiều nhất", m_debtor, f"{format_vn(others_owe_me.get(m_debtor, 0))}đ")
            
            m_creditor = max(i_owe_others, key=i_owe_others.get) if i_owe_others else "Không ai"
            c3.metric("Bạn nợ nhiều nhất", m_creditor, f"-{format_vn(i_owe_others.get(m_creditor, 0))}đ")

            # 4. BẢNG XẾP HẠNG HỘI QUẨY (Leaderboard Nhóm)
            st.write("---")
            st.subheader("🔥 Bảng Xếp Hạng Nhóm (Leaderboard)")
            sorted_groups = sorted(group_stats.items(), key=lambda x: x[1]['count'], reverse=True)
            for i, (name, s) in enumerate(sorted_groups):
                medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else "🔹"
                st.write(f"{medal} **{name}**: {s['count']} kèo - Tổng chi: {format_vn(s['money'])}đ")

            # 5. BẢNG XẾP HẠNG CÁC KHOẢN NỢ (Dưới cùng)
            st.write("---")
            st.subheader("📉 Xếp hạng các khoản nợ")
            if all_unpaid_debts:
                sorted_all = sorted(all_unpaid_debts, key=lambda x: x['amount'], reverse=True)
                df_debts = []
                for i, d in enumerate(sorted_all[:10]):
                    df_debts.append({
                        "Hạng": f"#{i+1}",
                        "Người nợ": d['debtor'],
                        "Người đòi": d['creditor'],
                        "Số tiền": f"{format_vn(d['amount'])}đ",
                        "Nội dung": d['item']
                    })
                st.table(df_debts)
            else:
                st.info("Hiện không có khoản nợ nào để xếp hạng.")
