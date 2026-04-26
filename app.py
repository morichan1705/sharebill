import streamlit as st
import json
import os
import re
import time
from datetime import datetime
from google import genai
import PIL.Image

# --- 1. CẤU HÌNH & LƯU TRỮ ---
st.set_page_config(page_title="Share Bills Ultimate V6", page_icon="💸", layout="wide")
# --- TÙY CHỈNH CSS NÂNG CAO ---
st.markdown("""
    <style>
    /* 1. Bo tròn và tạo hiệu ứng nổi cho tất cả các nút bấm */
    div.stButton > button {
        border-radius: 25px;
        transition: all 0.3s ease;
        border: none;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    /* Hiệu ứng khi di chuột vào nút */
    div.stButton > button:hover {
        transform: translateY(-3px);
        box-shadow: 0 5px 15px rgba(255, 75, 75, 0.4);
    }
    
    /* 2. Làm đẹp thanh Tab Menu trên cùng */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px 10px 0 0;
        padding: 10px 15px;
    }
    
    /* 3. Ẩn chữ "Made with Streamlit" ở dưới cùng cho chuyên nghiệp */
    footer {visibility: hidden;}
    
    /* 4. Làm đẹp các ô Expander (Thẻ thả xuống) */
    [data-testid="stExpander"] {
        border: 1px solid #ffeaeb;
        border-radius: 15px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.02);
    }
    </style>
""", unsafe_allow_html=True)
# --- HỆ THỐNG ĐĂNG NHẬP (USER AUTHENTICATION) ---
USERS_FILE = 'users.json'

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f: return json.load(f)
    return {}

def save_users(users_data):
    with open(USERS_FILE, 'w', encoding='utf-8') as f: json.dump(users_data, f)

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ''

# GIAO DIỆN ĐĂNG NHẬP
if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center;'>🔐 Đăng nhập Share Bills</h1>", unsafe_allow_html=True)
    tab_login, tab_reg = st.tabs(["Đăng nhập", "Đăng ký"])
    users = load_users()
    
    with tab_login:
        l_user = st.text_input("Tên bạn là gì:")
        l_pass = st.text_input("Mật khẩu:", type="password")
        if st.button("🚀 Đăng nhập", type="primary", use_container_width=True):
            if l_user in users and users[l_user] == l_pass:
                st.session_state.logged_in = True
                st.session_state.username = l_user
                st.rerun()
            else:
                st.error("Sai òi!")
    
    with tab_reg:
        r_user = st.text_input("Tạo tài khoản mới:")
        r_pass = st.text_input("Tạo mật khẩu:", type="password")
        if st.button("📝 Đăng ký", use_container_width=True):
            if r_user in users: st.error("Bạn đã có tài khoản rồi!")
            elif r_user and r_pass:
                users[r_user] = r_pass; save_users(users)
                st.success("Đăng ký thành công! Hãy quay lại tab Đăng nhập nhé.")
    
    st.stop() # Lệnh này chặn toàn bộ code bên dưới nếu chưa đăng nhập thành công
# --- CẤU HÌNH DỮ LIỆU CÁ NHÂN ---
# Mỗi user sẽ có một file data riêng (VD: data_lam.json)
DATA_FILE = f'data_{st.session_state.username}.json'

# Thêm nút Đăng xuất ở thanh menu bên trái (Sidebar)
st.sidebar.title(f"👋 Xin chào, {st.session_state.username}")
if st.sidebar.button("🚪 Đăng xuất"):
    st.session_state.logged_in = False
    st.session_state.username = ''
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
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.subheader("👤 Thành Viên")
        n_name = st.text_input("Tên mới:")
        n_bank = st.selectbox("Ngân hàng:", ["", "MB", "VCB", "TPB", "BIDV", "TCB", "VPB", "CTG"])
        n_acc = st.text_input("Số tài khoản:")
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

# --- TAB 5: WRAPPED & BẢNG XẾP HẠNG NHÓM ---
with tab5:
    # Mỗi lần mở Tab 5 là bóng bay ngập trời
    st.balloons() 
    st.markdown("<h2 style='text-align: center; color: #ff4b4b;'>🎉 Sòng Phẳng Wrapped</h2>", unsafe_allow_html=True)
    # ... (code cũ giữ nguyên)
    if not st.session_state.history:
        st.info("Chưa có dữ liệu đi chơi. Hãy lập kèo đi ăn ngay để mở khóa thống kê!")
    else:
        # --- BỘ LỌC THỜI GIAN ---
        time_filter = st.radio("⏳ Chọn mốc thời gian xem báo cáo:", 
                               ["Tháng này (Tháng 4)", "Từ đầu năm (2026)"], horizontal=True)
        st.write("---")
        
        # Tách danh sách bill theo mốc thời gian đã chọn
        filtered_history = []
        for b in st.session_state.history:
            try:
                # Dùng Regex lấy ngày tháng (VD: 25/04/2026)
                match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', str(b['date']))
                if match:
                    d_month = int(match.group(2))
                    d_year = int(match.group(3))
                    
                    if "Tháng này" in time_filter:
                        if d_month == 4 and d_year == 2026:
                            filtered_history.append(b)
                    elif "đầu năm" in time_filter:
                        if d_year == 2026:
                            filtered_history.append(b)
            except: 
                pass
                
        if not filtered_history:
            st.warning(f"Chưa có kèo nào được ghi nhận trong mốc: **{time_filter.split(' (')[0]}**")
        else:
            # --- 1. TÍNH TOÁN DỮ LIỆU CÁ NHÂN ---
            total_spent = sum(b['amount'] for b in filtered_history)
            payer_stats = {}
            debt_stats = {}
            tra_sua_count = 0
            
            # --- 2. TÍNH TOÁN DỮ LIỆU THEO NHÓM (DÀNH CHO LEADERBOARD) ---
            group_stats = {} 
            
            for b in filtered_history:
                # Tính cá nhân
                p = b['payer']
                payer_stats[p] = payer_stats.get(p, 0) + b['amount']
                
                if b['status'] == 'unpaid':
                    for debtor, amt in b['splits'].items():
                        if debtor != p and amt > 0 and debtor not in b.get('paid_by', []):
                            debt_stats[debtor] = debt_stats.get(debtor, 0) + amt
                
                # Đếm trà sữa
                for it in b.get('items', []):
                    if any(keyword in it['name'].lower() for keyword in ["trà sữa", "ts", "cafe", "nước", "phúc long", "koi"]):
                        tra_sua_count += it['qty']
                        
                # Tính cho Leaderboard Nhóm
                # Tìm tên nhóm hoặc tạo tên tạm từ các thành viên
                matched_group_name = None
                for gn, members in st.session_state.groups.items():
                    if set(b['splits'].keys()) == set(members):
                        matched_group_name = gn; break
                
                # Nếu không có tên nhóm lưu sẵn, hiển thị những người tham gia
                group_key = matched_group_name if matched_group_name else "Team: " + ", ".join(sorted(b['splits'].keys()))
                
                if group_key not in group_stats:
                    group_stats[group_key] = {"count": 0, "total_money": 0, "payers": {}}
                
                # Cập nhật số liệu cho nhóm đó
                group_stats[group_key]["count"] += 1
                group_stats[group_key]["total_money"] += b['amount']
                
                # Ai là người trả nhiều nhất trong nhóm này
                group_stats[group_key]["payers"][p] = group_stats[group_key]["payers"].get(p, 0) + b['amount']

            # Tìm danh hiệu cá nhân
            dai_gia = max(payer_stats, key=payer_stats.get) if payer_stats else "Chưa có"
            chua_no = max(debt_stats, key=debt_stats.get) if debt_stats else "Trắng nợ"
            
            # --- 3. GIAO DIỆN WRAPPED CÁ NHÂN ---
            st.subheader(f"🏆 Bảng Phong Thần - {time_filter.split(' (')[0]}")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"<div style='text-align: center; background-color: #f0f2f6; padding: 20px; border-radius: 10px;'>"
                            f"<h3>👑 Đại Gia Quẹt Thẻ</h3><h2 style='color:#ff4b4b;'>{dai_gia}</h2>"
                            f"<p>Tổng ứng: {format_vn(payer_stats.get(dai_gia, 0))}đ</p></div>", unsafe_allow_html=True)
            with col2:
                st.markdown(f"<div style='text-align: center; background-color: #f0f2f6; padding: 20px; border-radius: 10px;'>"
                            f"<h3>🐢 Chúa Tể Nợ Nần</h3><h2 style='color:#ff4b4b;'>{chua_no}</h2>"
                            f"<p>Đang nợ: {format_vn(debt_stats.get(chua_no, 0))}đ</p></div>", unsafe_allow_html=True)
            with col3:
                st.markdown(f"<div style='text-align: center; background-color: #f0f2f6; padding: 20px; border-radius: 10px;'>"
                            f"<h3>💸 Tổng Đốt Tiền</h3><h2 style='color:#ff4b4b;'>{format_vn(total_spent)}đ</h2>"
                            f"<p>Qua {len(filtered_history)} kèo</p></div>", unsafe_allow_html=True)

            st.write("---")
            if tra_sua_count > 0:
                st.success(f"🧋 **Báo động đường huyết:** Trong {time_filter.split(' (')[0].lower()}, nhóm đã tiêu thụ **{tra_sua_count} ly đồ uống**!")
            
            # --- 4. LEADERBOARD CÁC NHÓM ĐI CHƠI NHIỀU NHẤT ---
            st.write("---")
            st.subheader("🔥 Bảng Xếp Hạng Hội Quẩy (Leaderboard)")
            st.markdown("Hội nào đang có tần suất họp mặt và 'đốt tiền' ác liệt nhất?")
            
            # Sắp xếp các nhóm theo số lần đi chơi giảm dần (nếu bằng nhau thì xét tổng tiền)
            sorted_groups = sorted(group_stats.items(), key=lambda item: (item[1]['count'], item[1]['total_money']), reverse=True)
            
            for index, (g_name, stats) in enumerate(sorted_groups):
                # Xác định icon Top 3
                if index == 0: medal = "🥇"
                elif index == 1: medal = "🥈"
                elif index == 2: medal = "🥉"
                else: medal = f"**{index+1}.**"
                
                # Tìm 'Cá mập' gánh team (người trả nhiều tiền nhất trong nhóm này)
                shark = max(stats["payers"], key=stats["payers"].get) if stats["payers"] else "Không rõ"
                
                # Hiển thị từng nhóm trong thẻ Expander
                with st.expander(f"{medal} Nhóm: {g_name} - Đi {stats['count']} kèo (Tổng: {format_vn(stats['total_money'])}đ)"):
                    st.write(f"💸 **Tổng tiền nhóm đã chi:** {format_vn(stats['total_money'])}đ")
                    st.write(f"👑 **Cá mập gánh team:** {shark} (đã quẹt {format_vn(stats['payers'][shark])}đ)")
                    
                    # Thanh tiến trình thể hiện tỉ lệ đóng góp (vui vẻ)
                    st.write("**Tỉ lệ ứng tiền trong nhóm:**")
                    for p_name, p_amt in sorted(stats["payers"].items(), key=lambda x: x[1], reverse=True):
                        st.progress(min(p_amt / stats['total_money'], 1.0), text=f"{p_name}: {format_vn(p_amt)}đ")

            st.write("---")
            st.subheader("📊 Tỉ trọng người thanh toán chung (Biểu đồ)")
            if payer_stats:
                st.bar_chart(payer_stats)
