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
DATA_FILE = 'data.json'

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
tab1, tab2, tab3, tab4 = st.tabs(["👥 Danh Bạ & Nhóm", "🧾 Ghi Hóa Đơn", "🔥 Chốt Sổ Nợ", "🕒 Nhật Ký Bill"])

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
    with c_ai1:
        up_f = st.file_uploader("📸 Quét ảnh bill", type=["jpg", "png", "jpeg"])
        if up_f and st.button("✨ Phân tích ảnh"):
            try:
                img = PIL.Image.open(up_f); img.thumbnail((800, 800))
                res = client.models.generate_content(model='gemini-2.5-flash', contents=["Đọc bill, trả về: TÊN|GIÁ|SL", img])
                for line in res.text.strip().split('\n'):
                    p = line.split('|')
                    if len(p) == 3: st.session_state.current_items.append({"name": p[0], "price": parse_amount(p[1]), "qty": int(p[2])})
                st.rerun()
            except Exception as e: st.error(e)
    with c_ai2:
        txt_ai = st.text_area("💬 Dán tin nhắn:")
        if txt_ai and st.button("✨ Phân tích chữ"):
            try:
                res = client.models.generate_content(model='gemini-2.5-flash', contents=f"Phân tích bill: TÊN|GIÁ|SL: {txt_ai}")
                for line in res.text.strip().split('\n'):
                    p = line.split('|')
                    if len(p) == 3: st.session_state.current_items.append({"name": p[0], "price": parse_amount(p[1]), "qty": int(p[2])})
                st.rerun()
            except Exception as e: st.error(e)

    st.divider()
    st.subheader("📝 Nhập món lẻ")
    i_c1, i_c2, i_c3, i_c4 = st.columns([4, 3, 2, 2])
    im_n = i_c1.text_input("Tên món:")
    im_p = i_c2.text_input("Giá (VD: 50k, 200...):")
    im_q = i_c3.number_input("SL", 1, 100, 1)
    if i_c4.button("➕ Thêm"):
        p = parse_amount(im_p)
        if im_n and p > 0: st.session_state.current_items.append({"name": im_n, "price": p, "qty": im_q}); st.rerun()

    total_bill = 0
    for idx, it in enumerate(st.session_state.current_items):
        total_bill += it['price'] * it['qty']
        st.write(f"🔹 {it['name']} ({format_vn(it['price'])}đ x {it['qty']})")

    st.write("---")
    b_title = st.text_input("Tiêu đề bill:", value="Đi ăn")
    b_payer = st.selectbox("Ai trả tiền?", list(st.session_state.members.keys()))
    use_g = st.selectbox("Chọn nhóm (để tick nhanh):", ["-- Chọn lẻ --"] + list(st.session_state.groups.keys()))
    def_m = list(st.session_state.members.keys())
    if use_g != "-- Chọn lẻ --": def_m = st.session_state.groups[use_g]
    b_cons = st.multiselect("Ai tham gia?", list(st.session_state.members.keys()), default=def_m)

    if total_bill == 0:
        q_amt = st.text_input("💰 Nhập tổng bill nhanh:", value="0")
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
            st.session_state.history.append({"id": time.time(), "date": now, "name": b_title, "amount": total_bill, "payer": b_payer, "splits": splits, "status": "unpaid", "paid_by": []})
            st.session_state.current_items = []; save_data(); st.rerun()

# --- TAB 3: CHỐT SỔ (Tối ưu hóa nợ đa bên) ---
with tab3:
    unpaid = [b for b in st.session_state.history if b['status'] == 'unpaid']
    if not unpaid:
        st.success("Hết nợ! 🎉")
    else:
        st.subheader("⚙️ Tùy chọn chốt nợ")
        use_netting = st.toggle("🔀 Tối ưu hóa nợ đa bên (Rút gọn số lần chuyển khoản tối đa)", value=False)
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
                    with st.expander(f"🔴 **{debtor}** đang nợ tổng cộng: {format_vn(abs(bal))}đ"):
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