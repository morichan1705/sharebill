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
    st.subheader("🤖 Để AI nhập hộ bạn nhé")
    c_ai1, c_ai2 = st.columns(2)
    with c_ai1:
        up_f = st.file_uploader("📸 Quét ảnh bill", type=["jpg", "png", "jpeg"])
        if up_f and st.button("✨ Ai đang căng mắt phân tích ảnh đây"):
            try:
                img = PIL.Image.open(up_f); img.thumbnail((800, 800))
                res = client.models.generate_content(model='gemini-2.5-flash', contents=["Đọc bill, trả về: TÊN|GIÁ|SL", img])
                for line in res.text.strip().split('\n'):
                    p = line.split('|')
                    if len(p) == 3: st.session_state.current_items.append({"name": p[0], "price": parse_amount(p[1]), "qty": int(p[2])})
                st.rerun()
            except Exception as e: st.error(e)
    with c_ai2:
        txt_ai = st.text_area("💬 Dán tin nhắn ở đây nè:")
        if txt_ai and st.button("✨ Ai đang đọc tin nhắn của bạn đây"):
            try:
                res = client.models.generate_content(model='gemini-2.5-flash', contents=f"Phân tích bill: TÊN|GIÁ|SL: {txt_ai}")
                for line in res.text.strip().split('\n'):
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
    b_title = st.text_input("Tiêu đề bill:", value="Đi ăn")
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
        
        if st.button("💾 LƯU SỔ NỢ", type="primary"):
            now = datetime.now().strftime("%d/%m/%Y %H:%M")
            st.session_state.history.append({"id": time.time(), "date": now, "name": b_title, "amount": total_bill, "payer": b_payer, "splits": splits, "status": "unpaid", "paid_by": [], "items": st.session_state.current_items.copy()})
            st.session_state.current_items = []; save_data(); st.rerun()

# --- TAB 3: CHỐT SỔ (Tối ưu hóa nợ đa bên) ---
with tab3:
    unpaid = [b for b in st.session_state.history if b['status'] == 'unpaid']
    if not unpaid:
        st.success("Hết nợ! 🎉")
    else:
        st.subheader("⚙️ Tùy chọn chốt nợ")
        use_netting = st.toggle("🔀 Tối ưu hóa nợ cho mọi người (Để bạn không phải chuyển khoản nhiều nhé)", value=False)
        st.write("---")

        # 1. Tính toán Balance (Tổng tài sản ròng của mỗi người)
        # Ai có Balance dương là người cần thu tiền, âm là người cần trả tiền
        balances = {m: 0 for m in st.session_state.members}
        details_for_everyone = {m: [] for m in st.session_state.members}

        for b in unpaid:
            creditor = b['payer']
            paid_by = b.get('paid_by', [])
            balances[creditor] += (b['amount'] - b['splits'].get(creditor, 0))
            
            for debtor, amt in b['splits'].items():
                if debtor != creditor and amt > 0 and debtor not in paid_by:
                    balances[debtor] -= amt
                    details_for_everyone[debtor].append({"date": b['date'], "name": b['name'], "amount": amt, "type": "owe", "to": creditor})
                    details_for_everyone[creditor].append({"date": b['date'], "name": b['name'], "amount": amt, "type": "collect", "from": debtor})

        if not use_netting:
            # CHẾ ĐỘ 1: LIỆT KÊ TRỰC TIẾP (Theo từng chủ nợ)
            for debtor, bal in balances.items():
                if bal < -1:
                    with st.expander(f"🔴 **{debtor}** đang nợ tổng cộng, chờ xíu: {format_vn(abs(bal))}đ"):
                        my_debts = [d for d in details_for_everyone[debtor] if d['type'] == 'owe']
                        # Nhóm theo chủ nợ
                        by_creditor = {}
                        for d in my_debts:
                            if d['to'] not in by_creditor: by_creditor[d['to']] = 0
                            by_creditor[d['to']] += d['amount']
                        
                        for cred, total in by_creditor.items():
                            st.write(f"👉 **Nợ {cred}: {format_vn(total)}đ**")
                            c_info = st.session_state.members[cred]
                            if c_info['bank'] and c_info['acc']:
                                qr = f"https://img.vietqr.io/image/{c_info['bank']}-{c_info['acc']}-compact2.png?amount={int(total)}&addInfo={debtor}chuyen"
                                st.image(qr, width=200)
                            if st.button(f"Xác nhận đã trả xong cho {cred}", key=f"pay_{debtor}_{cred}"):
                                for b in st.session_state.history:
                                    if b['status'] == 'unpaid' and b['payer'] == cred and debtor in b['splits']:
                                        if 'paid_by' not in b: b['paid_by'] = []
                                        if debtor not in b['paid_by']: b['paid_by'].append(debtor)
                                        if all(d in b['paid_by'] or d == b['payer'] or b['splits'][d] <= 0 for d in b['splits']):
                                            b['status'] = 'paid'
                                save_data(); st.rerun()
        else:
            # CHẾ ĐỘ 2: TỐI ƯU HÓA (NETTING ĐA BÊN)
            st.markdown("### 🔀 Kết quả rút gọn nợ toàn nhóm")
            st.caption("Lâm nợ Thắng, Hân nợ Lâm -> Tính toán Hân trả thẳng cho Thắng để bớt khâu trung gian.")
            
            # Tách thành 2 nhóm: Người phải trả (âm) và Người được nhận (dương)
            debtors = [[m, abs(bal)] for m, bal in balances.items() if bal < -1]
            creditors = [[m, bal] for m, bal in balances.items() if bal > 1]

            # Thuật toán Greedy tối ưu hóa số lần chuyển
            transactions = []
            while debtors and creditors:
                debtors.sort(key=lambda x: x[1], reverse=True)
                creditors.sort(key=lambda x: x[1], reverse=True)
                
                d_name, d_amt = debtors[0]
                c_name, c_amt = creditors[0]
                
                settle_amt = min(d_amt, c_amt)
                transactions.append({"from": d_name, "to": c_name, "amount": settle_amt})
                
                debtors[0][1] -= settle_amt
                creditors[0][1] -= settle_amt
                
                if debtors[0][1] < 1: debtors.pop(0)
                if creditors[0][1] < 1: creditors.pop(0)

            for tx in transactions:
                with st.expander(f"✨ **{tx['from']}** ➡️ **{tx['to']}**: {format_vn(tx['amount'])}đ"):
                    st.write(f"Số tiền này bao gồm các khoản bù trừ từ nhiều hóa đơn khác nhau.")
                    c_info = st.session_state.members[tx['to']]
                    if c_info['bank'] and c_info['acc']:
                        qr = f"https://img.vietqr.io/image/{c_info['bank']}-{c_info['acc']}-compact2.png?amount={int(tx['amount'])}&addInfo={tx['from']}chuyen"
                        st.image(qr, width=200)
                    
                    if st.button(f"Xác nhận đã trả xong", key=f"net_{tx['from']}_{tx['to']}"):
                        # Lưu ý: Với Netting đa bên, việc xác nhận một giao dịch sẽ dọn sạch
                        # một phần nợ của người đó trong các bill liên quan.
                        # Để đơn giản và an toàn, ta sẽ xử lý dứt điểm nợ của 'from' 
                        # đối với bất kỳ ai, và 'to' được nhận tiền từ bất kỳ ai.
                        # (Đây là logic 'Chốt sổ dứt điểm' cho giao dịch tối ưu)
                        remaining = tx['amount']
                        for b in st.session_state.history:
                            if b['status'] == 'unpaid' and remaining > 0:
                                if tx['from'] in b['splits'] and tx['from'] not in b.get('paid_by', []):
                                    b.setdefault('paid_by', []).append(tx['from'])
                                    # Kiểm tra đóng bill
                                    if all(d in b['paid_by'] or d == b['payer'] or b['splits'][d] <= 0 for d in b['splits']):
                                        b['status'] = 'paid'
                        save_data(); st.rerun()

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

# --- TAB 5: WRAPPED & THỐNG KÊ (Theo mốc thời gian) ---
with tab5:
    st.markdown("<h2 style='text-align: center; color: #ff4b4b;'>🎉 Sòng Phẳng Wrapped</h2>", unsafe_allow_html=True)
    
    if not st.session_state.history:
        st.info("Chưa có dữ liệu đi chơi. Hãy lập kèo đi ăn ngay để mở khóa thống kê!")
    else:
        # --- BỘ LỌC THỜI GIAN ---
        # Lấy mốc thời gian hiện tại là Tháng 4/2026
        time_filter = st.radio("⏳ Chọn mốc thời gian xem báo cáo:", 
                               ["Tháng này(Tháng 4)", "Từ đầu năm (2026)"], horizontal=True)
        st.write("---")
        
        # Tách danh sách bill theo mốc thời gian đã chọn
        filtered_history = []
        for b in st.session_state.history:
            try:
                # Chuyển đổi chuỗi ngày tháng (VD: "26/04/2026 19:30") thành object ngày
                date_str = b['date'].split(" ")[0]
                date_obj = datetime.strptime(date_str, "%d/%m/%Y")
                
                if time_filter == "Tháng này (Tháng 4)":
                    if date_obj.month == 4 and date_obj.year == 2026:
                        filtered_history.append(b)
                elif time_filter == "Từ đầu năm (2026)":
                    if date_obj.year == 2026:
                        filtered_history.append(b)
            except: 
                pass # Bỏ qua nếu ngày tháng bị nhập sai định dạng
                
        # Nếu khoảng thời gian được chọn không có dữ liệu
        if not filtered_history:
            st.warning(f"Chưa có kèo nào được ghi nhận trong mốc: **{time_filter.split(' (')[0]}**")
        else:
            # --- 1. TÍNH TOÁN DỮ LIỆU TỔNG QUAN (Chỉ tính trên filtered_history) ---
            total_spent = sum(b['amount'] for b in filtered_history)
            payer_stats = {}
            debt_stats = {}
            tra_sua_count = 0
            group_dates = {} 
            
            for b in filtered_history:
                p = b['payer']
                payer_stats[p] = payer_stats.get(p, 0) + b['amount']
                
                if b['status'] == 'unpaid':
                    for debtor, amt in b['splits'].items():
                        if debtor != p and amt > 0 and debtor not in b.get('paid_by', []):
                            debt_stats[debtor] = debt_stats.get(debtor, 0) + amt
                
                for it in b.get('items', []):
                    if any(keyword in it['name'].lower() for keyword in ["trà sữa", "ts", "cafe", "nước", "phúc long", "koi"]):
                        tra_sua_count += it['qty']
                        
                matched_group_name = None
                for gn, members in st.session_state.groups.items():
                    if set(b['splits'].keys()) == set(members):
                        matched_group_name = gn; break
                
                group_key = matched_group_name if matched_group_name else "Kèo: " + ", ".join(sorted(b['splits'].keys()))
                if group_key not in group_dates: group_dates[group_key] = []
                
                try:
                    date_str = b['date'].split(" ")[0]
                    group_dates[group_key].append(datetime.strptime(date_str, "%d/%m/%Y").date())
                except: pass
                
            # --- 2. TÌM DANH HIỆU ---
            dai_gia = max(payer_stats, key=payer_stats.get) if payer_stats else "Chưa có"
            chua_no = max(debt_stats, key=debt_stats.get) if debt_stats else "Trắng nợ"
            
            # --- 3. TÍNH STREAK ---
            group_streaks = {}
            for g_name, dates_list in group_dates.items():
                dates_list = sorted(list(set(dates_list)))
                streak = 0
                if dates_list:
                    streak = 1
                    for i in range(1, len(dates_list)):
                        if (dates_list[i] - dates_list[i-1]).days <= 7: streak += 1
                        else: streak = 1 
                group_streaks[g_name] = streak
                
            champion_group = max(group_streaks, key=group_streaks.get) if group_streaks else "Chưa có"
            champion_streak = group_streaks.get(champion_group, 0)

            # --- 4. GIAO DIỆN WRAPPED ---
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
            
            # --- 5. THỐNG KÊ VUI ---
            if tra_sua_count > 0:
                st.success(f"🧋 **Báo động đường huyết:** Trong {time_filter.split(' (')[0].lower()}, nhóm đã tiêu thụ **{tra_sua_count} ly đồ uống**!")
                
            # --- 6. CHUỖI VÀ BẢNG XẾP HẠNG ---
            st.subheader("🔥 Cuộc Đua Chuỗi Đi Chơi (Streak)")
            if champion_streak > 0:
                st.markdown(f"🥇 **Hội Quẩy Nhiệt Nhất:** Nhóm `{champion_group}` đang dẫn đầu với **{champion_streak} kèo liên tiếp**! 🔥")
            
            with st.expander("Bảng xếp hạng Streak các nhóm"):
                for g, s in sorted(group_streaks.items(), key=lambda item: item[1], reverse=True):
                    icon = "🔥" if s >= 3 else "🌱"
                    st.write(f"{icon} **{g}**: {s} kèo liên tiếp")
                    
            st.write("---")
            st.subheader("📊 Tỉ trọng người thanh toán (Biểu đồ)")
            if payer_stats:
                st.bar_chart(payer_stats)
