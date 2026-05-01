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

# ════════════════════════════════════════════
#  1. CÀI ĐẶT TRANG & GIAO DIỆN CUTE ✨
# ════════════════════════════════════════════
st.set_page_config(page_title="Share Bills ✨", page_icon="💸", layout="wide")

st.markdown("""
<style>
/* ── Google Font ── */
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&display=swap');

/* ── Root & Body ── */
html, body, [class*="css"] {
    font-family: 'Nunito', sans-serif !important;
}

/* ── Ẩn footer Streamlit ── */
footer { visibility: hidden; }
div[data-testid="InputInstructions"] { display: none !important; }

/* ── Metric card – pastel glow ── */
div[data-testid="stMetric"] {
    border-radius: 20px;
    padding: 1rem 1.25rem;
    box-shadow: 0 4px 18px rgba(255, 120, 130, 0.10);
    border: 1.5px solid rgba(255,120,130,0.15);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
div[data-testid="stMetric"]:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 28px rgba(255,120,130,0.18);
}

/* ── PRIMARY button ── */
button[kind="primary"] {
    border: none !important;
    color: white !important;
    border-radius: 50px !important;
    font-weight: 700 !important;
    font-family: 'Nunito', sans-serif !important;
    letter-spacing: 0.3px;
    box-shadow: 0 4px 14px rgba(255,75,75,0.30) !important;
    transition: transform 0.15s ease, box-shadow 0.15s ease !important;
}
button[kind="primary"]:hover {
    transform: translateY(-2px) scale(1.03) !important;
    box-shadow: 0 8px 22px rgba(255,75,75,0.40) !important;
}
button[kind="primary"]:active { transform: scale(0.97) !important; }

/* ── SECONDARY button ── */
button[kind="secondary"] {
    border-radius: 50px !important;
    font-weight: 600 !important;
    font-family: 'Nunito', sans-serif !important;
    transition: transform 0.15s ease !important;
}
button[kind="secondary"]:hover { transform: translateY(-1px) !important; }

/* ── Tab bar ── */
div[data-baseweb="tab-list"] {
    border-radius: 50px;
    padding: 4px 6px;
    gap: 4px;
    backdrop-filter: blur(8px);
    box-shadow: 0 2px 12px rgba(0,0,0,0.07);
}
div[data-baseweb="tab"] {
    border-radius: 40px !important;
    font-weight: 600 !important;
    font-family: 'Nunito', sans-serif !important;
    transition: background 0.2s ease !important;
}
div[aria-selected="true"][data-baseweb="tab"] {
    color: white !important;
}

/* ── Expander ── */
div[data-testid="stExpander"] {
    border-radius: 16px !important;
    border: 1.5px solid rgba(255,107,129,0.18) !important;
    backdrop-filter: blur(6px);
    margin-bottom: 0.6rem !important;
    overflow: hidden;
    transition: box-shadow 0.2s ease;
}
div[data-testid="stExpander"]:hover {
    box-shadow: 0 6px 20px rgba(255,107,129,0.14);
}
div[data-testid="stExpander"] details summary {
    padding: 0.55rem 0.75rem !important;
    font-weight: 700 !important;
}

/* ── Input fields ── */
div[data-baseweb="input"] > div,
div[data-baseweb="select"] > div:first-child {
    border-radius: 14px !important;
    border-color: rgba(255,107,129,0.3) !important;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
div[data-baseweb="input"] > div:focus-within {
    border-color: #ff6b81 !important;
    box-shadow: 0 0 0 3px rgba(255,107,129,0.15) !important;
}

/* ── Container / Card ── */
div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 20px !important;
    border: 1.5px solid rgba(255,107,129,0.15) !important;
    padding: 0.5rem;
    box-shadow: 0 4px 16px rgba(255,107,129,0.08);
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    border-right: 1.5px solid rgba(255,107,129,0.15) !important;
}

/* ── Toast override ── */
div[data-testid="stToast"] {
    border-radius: 16px !important;
    font-family: 'Nunito', sans-serif !important;
    font-weight: 600 !important;
}

/* ── Divider ── */
hr {
    border: none !important;
    height: 2px !important;
    margin: 1rem 0 !important;
}

/* ── Animations ── */
@keyframes wiggle {
    0%, 100% { transform: rotate(-4deg); }
    50% { transform: rotate(4deg); }
}
@keyframes popIn {
    0% { opacity:0; transform: scale(0.85) translateY(8px); }
    100% { opacity:1; transform: scale(1) translateY(0); }
}
@keyframes pulse-soft {
    0%, 100% { box-shadow: 0 0 0 0 rgba(255,107,129,0.25); }
    50% { box-shadow: 0 0 0 8px rgba(255,107,129,0); }
}

.wiggle-icon { display: inline-block; animation: wiggle 2s ease-in-out infinite; }
.pop-in { animation: popIn 0.35s ease forwards; }

/* ── Warning / Info / Success ── */
div[data-testid="stAlert"] {
    border-radius: 16px !important;
    font-family: 'Nunito', sans-serif !important;
    font-weight: 600 !important;
    border-left-width: 4px !important;
}

/* ── Mobile tweaks ── */
@media (max-width: 768px) {
    .mobile-margin-fix { display: none !important; }
    .block-container { padding-left: 0.75rem !important; padding-right: 0.75rem !important; }
}

/* ── Balloon override – already cute but just in case ── */
div[data-testid="stBalloons"] canvas { opacity: 0.9 !important; }
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════
#  KHỞI TẠO CLIENT
# ════════════════════════════════════════════
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=API_KEY)
except Exception:
    client = None


@st.cache_resource
def init_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])


supabase = init_supabase()

# ════════════════════════════════════════════
#  2. HỆ THỐNG ĐĂNG NHẬP
# ════════════════════════════════════════════
if "logged_in" not in st.session_state:
    st.session_state.update(logged_in=False, username="", nickname="")


def get_user_from_db(username):
    res = supabase.table("users").select("*").eq("username", username).execute()
    return res.data[0] if res.data else None


if not st.session_state.logged_in:
    # ── Login header ──
    st.markdown("""
    <div style='text-align:center; padding: 2rem 0 1rem;'>
        <div style='font-size:3.5rem; animation: wiggle 2s ease-in-out infinite; display:inline-block;'>💸</div>
        <h1 style='font-family: Nunito, sans-serif; font-weight:800; color:#ff4b4b; margin:0.3rem 0;'>Share Bills</h1>
        <p style='color:#999; font-size:1rem;'>Chia tiền vui vẻ, không lo cãi nhau 🥰</p>
    </div>
    """, unsafe_allow_html=True)

    tab_login, tab_reg = st.tabs(["🔑 Đăng nhập", "🌸 Đăng ký mới"])

    with tab_login:
        with st.container():
            l_user = st.text_input("👤 Tài khoản:", key="log_user", placeholder="Nhập ID của bạn...")
            l_pass = st.text_input("🔒 Mật khẩu:", type="password", key="log_pass", placeholder="••••••••")
            if st.button("🚀 Đăng nhập nào!", type="primary", use_container_width=True):
                user_data = get_user_from_db(l_user)
                if user_data and l_pass == user_data["password"]:
                    st.session_state.update(logged_in=True, username=l_user, nickname=user_data["nickname"])
                    st.rerun()
                else:
                    st.error("😅 Sai tài khoản hoặc mật khẩu rồi!")

    with tab_reg:
        r_user = st.text_input("🆔 Tên đăng nhập (ID):", key="reg_user", placeholder="vd: mori2024")
        r_pass = st.text_input("🔒 Mật khẩu:", type="password", key="reg_pass", placeholder="Đặt mật khẩu bí mật...")
        r_nick = st.text_input("✨ Bạn muốn được gọi là gì?", key="reg_nick", placeholder="vd: Mori, Bé Heo, ...")
        if st.button("🎉 Tạo tài khoản!", use_container_width=True):
            if get_user_from_db(r_user):
                st.error("😬 ID này đã có người dùng rồi!")
            elif r_user and r_pass and r_nick:
                supabase.table("users").insert({
                    "username": r_user, "password": r_pass, "nickname": r_nick,
                    "app_data": {"members": {}, "groups": {}, "history": []}
                }).execute()
                st.success("🎊 Đăng ký thành công! Qua tab Đăng nhập nha~")
            else:
                st.warning("🙈 Điền đủ thông tin giúp mình nha!")
    st.stop()

# ════════════════════════════════════════════
#  3. DỮ LIỆU & HELPERS
# ════════════════════════════════════════════
BANK_LIST = ["", "MB", "VCB", "TPB", "BIDV", "TCB", "VPB", "CTG", "ACB", "SHB", "STB", "VIB"]
my_id = st.session_state.username


# ── Sidebar ──
st.sidebar.markdown(f"""
<div style='text-align:center; padding:0.5rem 0 1rem;'>
    <div style='font-size:2.5rem;'>🌸</div>
    <div style='font-weight:800; font-size:1.1rem; color:#ff4b4b;'>
        Xin chào, {st.session_state.get('nickname', 'Bạn')}!
    </div>
    <div style='font-size:0.8rem; color:#aaa; margin-top:2px;'>Chúc bạn chia bill vui vẻ~</div>
</div>
""", unsafe_allow_html=True)

if st.sidebar.button("🚪 Đăng xuất", use_container_width=True):
    st.session_state.update(logged_in=False, username="", nickname="")
    st.rerun()


def load_data():
    user_data = get_user_from_db(st.session_state.username)
    if user_data and user_data.get("app_data"):
        data = user_data["app_data"]
        raw_members = data.get("members", {})

        # AUTO MIGRATION: nâng cấp dữ liệu cũ
        is_old_format = any(
            "name" not in v for k, v in raw_members.items() if isinstance(v, dict)
        )
        if is_old_format:
            new_members, name_to_id = {}, {}
            for old_name, info in raw_members.items():
                new_id = my_id if old_name == st.session_state.nickname else f"user_{int(time.time()*1000)}_{len(new_members)}"
                new_members[new_id] = {"name": old_name, "bank": info.get("bank", ""), "acc": info.get("acc", "")}
                name_to_id[old_name] = new_id

            st.session_state.members = new_members
            st.session_state.groups = {
                g: [name_to_id.get(m, m) for m in ml]
                for g, ml in data.get("groups", {}).items()
            }
            new_history = []
            for b in data.get("history", []):
                b["payer_data"] = {name_to_id.get(k, k): v for k, v in b.get("payer_data", {}).items()}
                b["splits"] = {name_to_id.get(k, k): v for k, v in b.get("splits", {}).items()}
                b["paid_by"] = [name_to_id.get(k, k) for k in b.get("paid_by", [])]
                new_history.append(b)
            st.session_state.history = new_history
            save_data()
        else:
            st.session_state.members = raw_members
            st.session_state.groups = data.get("groups", {})
            st.session_state.history = data.get("history", [])
    else:
        st.session_state.update(members={}, groups={}, history=[])


def save_data():
    supabase.table("users").update({
        "app_data": {
            "members": st.session_state.members,
            "groups": st.session_state.groups,
            "history": st.session_state.history,
        }
    }).eq("username", st.session_state.username).execute()


if "members" not in st.session_state:
    load_data()

# Đảm bảo bản thân luôn có trong danh bạ
if my_id not in st.session_state.members:
    st.session_state.members[my_id] = {"name": st.session_state.nickname, "bank": "", "acc": ""}
    save_data()


# ── Utility functions ──
def get_name(u_id: str) -> str:
    base = st.session_state.members.get(u_id, {}).get("name", "Khách")
    return f"⭐ Bản thân ({base})" if u_id == my_id else base


def get_pure_name(u_id: str) -> str:
    return st.session_state.members.get(u_id, {}).get("name", "Khách")


def parse_amount(text) -> int:
    if not text:
        return 0
    clean = str(text).lower().replace(",", "").replace(".", "").replace(" ", "")
    has_k = "k" in clean
    clean = re.sub(r"k\b", "*1000", clean)
    try:
        if all(c in "0123456789+-*/.() " for c in clean):
            val = eval(clean)
            if 0 < val < 1000 and not has_k:
                val *= 1000
            return int(round(val))
    except Exception:
        pass
    return 0


def format_vn(num: float) -> str:
    return "{:,}".format(int(num))


def _bank_idx(bank: str) -> int:
    return BANK_LIST.index(bank) if bank in BANK_LIST else 0


# ════════════════════════════════════════════
#  HEADER
# ════════════════════════════════════════════
st.markdown("""
<div style='display:flex; align-items:center; gap:12px; margin-bottom:0.25rem;'>
    <span style='font-size:2.2rem; animation: wiggle 2s ease-in-out infinite; display:inline-block;'>💸</span>
    <div>
        <h2 style='margin:0; font-family:Nunito,sans-serif; font-weight:800; color:#ff4b4b; line-height:1.1;'>Share Bills Ultimate</h2>
        <div style='font-size:0.8rem; color:#aaa;'>Chia tiền chill, không stress ✌️</div>
    </div>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["👥 Danh Bạ & Nhóm", "🧾 Ghi Hóa Đơn", "🔥 Chốt Sổ Nợ", "🕒 Nhật Ký Bill", "🎁 Wrapped"]
)

# ════════════════════════════════════════════
#  TAB 1 – DANH BẠ & NHÓM
# ════════════════════════════════════════════
with tab1:
    # ── Thông tin cá nhân ──
    st.markdown("### 👤 Thông tin của bạn")
    with st.expander("⚙️ Chỉnh sửa thông tin cá nhân"):
        c0, c1, c2 = st.columns(3)
        edit_my_name = c0.text_input("Tên hiển thị:", value=st.session_state.members[my_id].get("name", st.session_state.nickname))
        edit_my_bank = c1.selectbox("Ngân hàng:", BANK_LIST, index=_bank_idx(st.session_state.members[my_id].get("bank", "")))
        edit_my_acc = c2.text_input("Số tài khoản:", value=st.session_state.members[my_id].get("acc", ""))
        if st.button("💾 Cập nhật thông tin", type="primary"):
            st.session_state.members[my_id] = {"name": edit_my_name, "bank": edit_my_bank, "acc": edit_my_acc}
            st.session_state.nickname = edit_my_name
            save_data()
            st.toast("✅ Đã lưu rồi nha~", icon="🌸")
            st.rerun()

    st.divider()

    # ── Bạn bè ──
    st.markdown("### 👥 Bạn bè của bạn")
    c_add, c_list = st.columns([1, 1.5], gap="large")

    with c_add:
        st.markdown("#### ➕ Kết bạn mới")
        with st.container(border=True):
            new_f_name = st.text_input("Tên người bạn:", placeholder="vd: Bé Mèo 🐱")
            new_f_bank = st.selectbox("Ngân hàng (tuỳ):", BANK_LIST, key="new_f_bank")
            new_f_acc = st.text_input("Số tài khoản (tuỳ):", key="new_f_acc")
            if st.button("➕ Thêm bạn này!", type="primary", use_container_width=True):
                if not new_f_name.strip():
                    st.warning("🙈 Nhập tên bạn đi nè!")
                else:
                    new_id = f"user_{int(time.time()*1000)}"
                    st.session_state.members[new_id] = {
                        "name": new_f_name.strip(), "bank": new_f_bank, "acc": new_f_acc.strip()
                    }
                    save_data()
                    st.toast(f"🎉 Đã thêm {new_f_name}!", icon="✨")
                    st.rerun()

    with c_list:
        st.markdown("#### 📜 Danh sách bạn bè")
        friend_ids = [u for u in st.session_state.members if u != my_id]
        if not friend_ids:
            st.info("🥺 Chưa có bạn nào, thêm ngay đi~")
        else:
            if "friend_page" not in st.session_state:
                st.session_state.friend_page = 1
            per_page = 5
            total_pages = max(1, math.ceil(len(friend_ids) / per_page))
            st.session_state.friend_page = min(st.session_state.friend_page, total_pages)
            start = (st.session_state.friend_page - 1) * per_page

            for f_id in friend_ids[start: start + per_page]:
                f_data = st.session_state.members[f_id]
                with st.expander(f"👤 {f_data['name']}"):
                    fc0, fc1, fc2 = st.columns([1.5, 1, 1.5])
                    edit_f_name = fc0.text_input("Đổi tên:", value=f_data["name"], key=f"en_{f_id}")
                    edit_f_bank = fc1.selectbox("Bank:", BANK_LIST, index=_bank_idx(f_data.get("bank", "")), key=f"eb_{f_id}")
                    edit_f_acc = fc2.text_input("STK:", value=f_data.get("acc", ""), key=f"ea_{f_id}")
                    bc1, bc2 = st.columns(2)
                    if bc1.button("💾 Lưu", key=f"sb_{f_id}", use_container_width=True):
                        st.session_state.members[f_id] = {"name": edit_f_name, "bank": edit_f_bank, "acc": edit_f_acc}
                        save_data(); st.rerun()
                    if bc2.button("🗑️ Xoá", key=f"db_{f_id}", type="primary", use_container_width=True):
                        st.session_state.members.pop(f_id)
                        for g in st.session_state.groups.values():
                            if f_id in g: g.remove(f_id)
                        save_data(); st.rerun()

            if total_pages > 1:
                cp1, cp2, cp3 = st.columns([1.5, 7, 1.5])
                if cp1.button("⬅️", disabled=(st.session_state.friend_page == 1), use_container_width=True):
                    st.session_state.friend_page -= 1; st.rerun()
                cp2.markdown(f"<div style='text-align:center;padding-top:5px;font-weight:700;'>Trang {st.session_state.friend_page} / {total_pages}</div>", unsafe_allow_html=True)
                if cp3.button("➡️", disabled=(st.session_state.friend_page == total_pages), use_container_width=True):
                    st.session_state.friend_page += 1; st.rerun()

    st.divider()

    # ── Nhóm ──
    st.markdown("### 🧑‍🤝‍🧑 Nhóm đi chơi")
    all_mem_ids = list(st.session_state.members.keys())
    cg_add, cg_list = st.columns([1, 1.5], gap="large")

    with cg_add:
        st.markdown("#### ➕ Lập nhóm mới")
        with st.container(border=True):
            new_g_name = st.text_input("Tên nhóm:", placeholder="vd: Team Trà Sữa 🧋")
            new_g_members = st.multiselect("Thành viên:", all_mem_ids, default=[my_id], format_func=get_name)
            if st.button("🎊 Lập nhóm nào!", type="primary", use_container_width=True):
                if new_g_name and len(new_g_members) >= 2 and new_g_name not in st.session_state.groups:
                    st.session_state.groups[new_g_name.strip()] = new_g_members
                    save_data(); st.rerun()

    with cg_list:
        st.markdown("#### 📌 Danh sách nhóm")
        if not st.session_state.groups:
            st.info("🥺 Chưa có nhóm nào, tạo nhóm đi chơi thôi~")
        else:
            group_names = list(st.session_state.groups.keys())
            if "group_page" not in st.session_state: st.session_state.group_page = 1
            per_pg = 5
            tot_pg = max(1, math.ceil(len(group_names) / per_pg))
            st.session_state.group_page = min(st.session_state.group_page, tot_pg)
            s_g = (st.session_state.group_page - 1) * per_pg

            for g_name in group_names[s_g: s_g + per_pg]:
                g_mems = st.session_state.groups[g_name]
                with st.expander(f"📌 {g_name} · {len(g_mems)} người"):
                    edit_gm = st.multiselect(
                        "Thành viên:", all_mem_ids,
                        default=[m for m in g_mems if m in all_mem_ids],
                        format_func=get_name, key=f"eg_{g_name}"
                    )
                    gc1, gc2 = st.columns(2)
                    if gc1.button("💾 Lưu", key=f"sg_{g_name}", use_container_width=True) and len(edit_gm) >= 2:
                        st.session_state.groups[g_name] = edit_gm; save_data(); st.rerun()
                    if gc2.button("🗑️ Xoá nhóm", key=f"dg_{g_name}", type="primary", use_container_width=True):
                        st.session_state.groups.pop(g_name); save_data(); st.rerun()

            if tot_pg > 1:
                gp1, gp2, gp3 = st.columns([1.5, 7, 1.5])
                if gp1.button("⬅️", key="g_prev", disabled=(st.session_state.group_page == 1), use_container_width=True):
                    st.session_state.group_page -= 1; st.rerun()
                gp2.markdown(f"<div style='text-align:center;padding-top:5px;font-weight:700;'>Trang {st.session_state.group_page} / {tot_pg}</div>", unsafe_allow_html=True)
                if gp3.button("➡️", key="g_next", disabled=(st.session_state.group_page == tot_pg), use_container_width=True):
                    st.session_state.group_page += 1; st.rerun()

# ════════════════════════════════════════════
#  TAB 2 – GHI HÓA ĐƠN
# ════════════════════════════════════════════
with tab2:
    if "current_items" not in st.session_state: st.session_state.current_items = []

    st.markdown("### 🤖 AI đọc bill siêu tốc")
    c_ai1, c_ai2 = st.columns(2)
    current_time_str = datetime.now(timezone(timedelta(hours=7))).strftime("%d/%m/%Y %H:%M")

    with c_ai1:
        up_files = st.file_uploader("📸 Tải ảnh bill lên đây", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
        if up_files and st.button("✨ Phân tích ảnh ngay!", type="primary"):
            with st.spinner("🤖 AI đang cắm mặt đọc bill... xíu nha~"):
                try:
                    images = [PIL.Image.open(f).copy() for f in up_files]
                    for img in images: img.thumbnail((800, 800))
                    prompt = f"Hôm nay là {current_time_str}. Đọc bill, gộp chung món. Trả về:\nNGÀY: dd/mm/yyyy hh:mm\nTÊN|GIÁ|SL"
                    res = client.models.generate_content(model="gemini-2.5-flash", contents=[prompt] + images)
                    for line in res.text.strip().split("\n"):
                        if line.upper().startswith("NGÀY:"):
                            st.session_state.ai_date = line[5:].strip()
                        else:
                            p = line.split("|")
                            if len(p) == 3:
                                st.session_state.current_items.append({"name": p[0], "price": parse_amount(p[1]), "qty": int(p[2])})
                    st.rerun()
                except Exception as e: st.error(f"😵 Lỗi: {e}")

    with c_ai2:
        txt_ai = st.text_area("💬 Paste tin nhắn bill vào đây:", placeholder="vd: Trà sữa 2 ly 120k, Gà rán 1 phần 85k...")
        if txt_ai and st.button("✨ Phân tích chữ!", type="primary"):
            with st.spinner("🤖 AI đang đọc tin nhắn..."):
                try:
                    res = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=f"Hôm nay là {current_time_str}. Đọc tin nhắn:\n{txt_ai}\nTrả về:\nNGÀY: dd/mm/yyyy hh:mm\nTÊN|GIÁ|SL"
                    )
                    for line in res.text.strip().split("\n"):
                        if line.upper().startswith("NGÀY:"):
                            st.session_state.ai_date = line[5:].strip()
                        else:
                            p = line.split("|")
                            if len(p) == 3:
                                st.session_state.current_items.append({"name": p[0], "price": parse_amount(p[1]), "qty": int(p[2])})
                    st.rerun()
                except Exception as e: st.error(f"😵 Lỗi: {e}")

    st.divider()
    st.markdown("### 📝 Thêm món lẻ")
    ic1, ic2, ic3, ic4 = st.columns([4, 3, 2, 2])
    im_n = ic1.text_input("Tên món:", placeholder="vd: Bún bò 🍜")
    im_p = ic2.text_input("Giá:", placeholder="vd: 45k, 120000")
    im_q = ic3.number_input("SL", 1, 100, 1)
    with ic4:
        st.markdown("<div style='margin-top:28.5px;'></div>", unsafe_allow_html=True)
        if st.button("➕ Thêm", type="primary", use_container_width=True) and im_n and parse_amount(im_p) > 0:
            st.session_state.current_items.append({"name": im_n, "price": parse_amount(im_p), "qty": im_q})
            st.rerun()

    total_bill = 0
    if st.session_state.current_items:
        st.divider()
        st.markdown("**🛒 Danh sách món:**")
        for idx, it in enumerate(st.session_state.current_items):
            c_n, c_p, c_q, c_d = st.columns([4, 3, 2, 1])
            new_name = c_n.text_input("Tên", it["name"], key=f"en_{idx}", label_visibility="collapsed")
            new_price = parse_amount(c_p.text_input("Giá", str(it["price"]), key=f"ep_{idx}", label_visibility="collapsed"))
            new_qty = c_q.number_input("SL", value=it["qty"], min_value=1, key=f"eq_{idx}", label_visibility="collapsed")
            st.session_state.current_items[idx] = {"name": new_name, "price": new_price, "qty": new_qty}
            total_bill += new_price * new_qty
            if c_d.button("❌", key=f"d_{idx}"): st.session_state.current_items.pop(idx); st.rerun()

    st.divider()
    c_info1, c_info2 = st.columns(2)
    b_title = c_info1.text_input("📌 Tiêu đề bill:", value="Đi ăn", placeholder="vd: Bữa tối sinh nhật 🎂")
    b_date = c_info2.text_input("📅 Thời gian:", value=st.session_state.get("ai_date", datetime.now().strftime("%d/%m/%Y %H:%M")))
    if total_bill == 0:
        total_bill = parse_amount(st.text_input("💰 Tổng bill (nhập nhanh nếu không chia món):", "0"))

    st.divider()
    all_mem_ids_t2 = list(st.session_state.members.keys())

    # ── Người trả tiền ──
    st.markdown(f"#### 💳 Ai đã ứng tiền? (Tổng: **{format_vn(total_bill)}đ** 💵)")
    selected_payers = st.multiselect("Người ứng tiền:", all_mem_ids_t2, default=[my_id], format_func=get_name, key="payers_ms")

    payer_data = {}
    if len(selected_payers) > 1:
        pay_method = st.radio("Cách chia tiền ứng:", ["Chia đều ✂️", "Theo tỉ lệ (%) 📊", "Số tiền cụ thể 💰"], horizontal=True)
        if "Chia đều" in pay_method:
            for p in selected_payers: payer_data[p] = total_bill / len(selected_payers)
        elif "tỉ lệ" in pay_method:
            cols = st.columns(len(selected_payers))
            for i, p in enumerate(selected_payers):
                pct = cols[i].number_input(f"% {get_pure_name(p)}", 0, 100, 0, key=f"pct_{p}")
                payer_data[p] = (pct / 100) * total_bill
        else:
            cols = st.columns(len(selected_payers))
            for i, p in enumerate(selected_payers):
                payer_data[p] = cols[i].number_input(f"{get_pure_name(p)} ứng", 0, step=1000, key=f"amt_{p}")
    elif len(selected_payers) == 1:
        payer_data[selected_payers[0]] = total_bill

    st.divider()

    # ── Người ăn ──
    st.markdown("#### 🍴 Ai tham gia ăn?")
    use_g = st.selectbox("Chọn nhóm nhanh:", ["-- Chọn lẻ --"] + list(st.session_state.groups.keys()))
    def_m = st.session_state.groups.get(use_g, all_mem_ids_t2) if use_g != "-- Chọn lẻ --" else all_mem_ids_t2
    b_cons = st.multiselect("Danh sách ăn:", def_m, default=def_m, format_func=get_name)

    if b_cons and total_bill > 0:
        method = st.radio("Cách chia tiền ăn:", ["Chia đều ✂️", "Chia theo món lẻ 🍽️"], horizontal=True)
        splits = {c: 0 for c in b_cons}
        if "món lẻ" in method and st.session_state.current_items:
            pool = 0
            for idx, it in enumerate(st.session_state.current_items):
                st.write(f"🍴 **{it['name']}** — {format_vn(it['price'] * it['qty'])}đ")
                who = st.multiselect("Ai ăn?", b_cons, default=b_cons, format_func=get_pure_name, key=f"w_{idx}")
                if who:
                    for w in who: splits[w] += (it["price"] * it["qty"]) / len(who)
                else:
                    pool += it["price"] * it["qty"]
            if pool > 0:
                for c in b_cons: splits[c] += pool / len(b_cons)
        else:
            for c in b_cons: splits[c] = total_bill / len(b_cons)

        has_deadline = st.checkbox("📅 Đặt hạn chót thanh toán?")
        b_deadline = st.date_input("Hạn chót:", value=datetime.now().date()).strftime("%d/%m/%Y") if has_deadline else None

        if st.button("💾 LƯU SỔ NỢ 📒", type="primary", use_container_width=True):
            if not selected_payers:
                st.error("😅 Chưa chọn người trả tiền!")
            elif abs(sum(payer_data.values()) - total_bill) > 1:
                st.error(f"😵 Tổng ứng ({format_vn(sum(payer_data.values()))}đ) lệch với tổng bill ({format_vn(total_bill)}đ)!")
            else:
                st.session_state.history.append({
                    "id": time.time(), "date": b_date, "deadline": b_deadline,
                    "name": b_title, "amount": total_bill,
                    "payer_data": payer_data, "splits": splits,
                    "status": "unpaid", "paid_by": [],
                    "items": st.session_state.current_items.copy()
                })
                st.session_state.current_items = []
                st.session_state.ai_date = datetime.now().strftime("%d/%m/%Y %H:%M")
                save_data()
                st.balloons()
                st.success("🎉 Đã lưu rồi nha! Nhớ đòi nợ đúng hạn nhé~")
                time.sleep(1.5)
                st.rerun()

# ════════════════════════════════════════════
#  TAB 3 – CHỐT SỔ
# ════════════════════════════════════════════
with tab3:
    unpaid = [b for b in st.session_state.history if b["status"] == "unpaid"]

    # Cảnh báo deadline
    today = datetime.now().date()
    for b in unpaid:
        if b.get("deadline"):
            try:
                days_left = (datetime.strptime(b["deadline"], "%d/%m/%Y").date() - today).days
                if 0 <= days_left <= 7:
                    st.warning(f"⏰ Sắp hết hạn! Bill **{b['name']}** còn **{days_left} ngày** nữa đó~")
            except Exception:
                pass

    if not unpaid:
        st.markdown("""
        <div style='text-align:center; padding:3rem 0;'>
            <div style='font-size:4rem;'>🎉</div>
            <h3 style='color:#ff4b4b; font-family:Nunito,sans-serif;'>Sạch nợ hết rồi!</h3>
            <p style='color:#aaa;'>Tất cả hóa đơn đã được thanh toán xong~</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        use_netting = st.toggle("🔀 Bật bù trừ nợ chéo thông minh", value=True)

        # ── Tính toán nợ ──
        mem_keys = list(st.session_state.members.keys())
        matrix = {m1: {m2: 0.0 for m2 in mem_keys} for m1 in mem_keys}
        details = {m1: {m2: [] for m2 in mem_keys} for m1 in mem_keys}
        debts_dict: dict = {}

        for b in unpaid:
            p_data = b.get("payer_data", {})
            splits = b.get("splits", {})
            paid_by = b.get("paid_by", [])

            bals: dict = {}
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
                            debts_dict.setdefault(pair, []).append({
                                "date": b["date"], "name": b["name"],
                                "amount": amt, "deadline": b.get("deadline"), "b_id": b.get("id")
                            })
                            if debtor in matrix and creditor in matrix[debtor]:
                                matrix[debtor][creditor] += amt
                            if debtor in details and creditor in details[debtor]:
                                details[debtor][creditor].append({"name": b["name"], "amount": amt, "b_id": b.get("id")})

        # ── Tin nhắn tóm tắt ──
        msg_raw = "📣 TỔNG KẾT CHỐT SỔ NỢ (Chưa bù trừ):\n"
        for (d_r, c_r), items_r in debts_dict.items():
            msg_raw += f"🔸 {get_pure_name(d_r)} nợ {get_pure_name(c_r)}: {format_vn(sum(i['amount'] for i in items_r))}đ\n"
        if not debts_dict: msg_raw += "Không có khoản nợ nào.\n"

        net_bal = {m: 0.0 for m in mem_keys}
        for d in mem_keys:
            for c in mem_keys:
                net_bal[c] += matrix[d][c]
                net_bal[d] -= matrix[d][c]

        debtors_l = [[m, abs(v)] for m, v in net_bal.items() if v < -1]
        creditors_l = [[m, v] for m, v in net_bal.items() if v > 1]

        msg_netting = "📣 TỔNG KẾT CHỐT SỔ NỢ (Đã bù trừ):\n"
        _dl, _cl = [x[:] for x in debtors_l], [x[:] for x in creditors_l]
        found_netting = False
        while _dl and _cl:
            _dl.sort(key=lambda x: x[1], reverse=True); _cl.sort(key=lambda x: x[1], reverse=True)
            d_n, d_a = _dl[0]; c_n, c_a = _cl[0]
            s_a = min(d_a, c_a)
            msg_netting += f"✨ {get_pure_name(d_n)} → {get_pure_name(c_n)}: {format_vn(s_a)}đ\n"
            _dl[0][1] -= s_a; _cl[0][1] -= s_a
            if _dl[0][1] < 1: _dl.pop(0)
            if _cl[0][1] < 1: _cl.pop(0)
            found_netting = True
        if not found_netting: msg_netting += "Không có khoản nợ nào cần chốt.\n"

        with st.expander("📋 Copy tin nhắn đòi nợ liền~ 👇"):
            st.code(msg_netting if use_netting else msg_raw, language="text")

        st.divider()

        # ── Danh sách nợ ──
        def _mark_paid(debtor_id, item_list):
            """Đánh dấu đã thanh toán và cập nhật trạng thái bill."""
            ids = {it["b_id"] for it in item_list}
            for b in st.session_state.history:
                if b.get("id") in ids and b["status"] == "unpaid":
                    b.setdefault("paid_by", []).append(debtor_id)
                    remaining = {}
                    for p, a in b.get("payer_data", {}).items():
                        if p not in b["paid_by"]: remaining[p] = remaining.get(p, 0) + a
                    for c, a in b["splits"].items():
                        if c not in b["paid_by"]: remaining[c] = remaining.get(c, 0) - a
                    if not any(v < -1 for v in remaining.values()): b["status"] = "paid"
            save_data(); st.rerun()

        if not use_netting:
            st.subheader("📜 Chi tiết nợ (chưa bù trừ)")
            for (debtor, creditor), items in debts_dict.items():
                total_owed = sum(i["amount"] for i in items)
                with st.expander(f"🔴 **{get_pure_name(debtor)}** nợ **{get_pure_name(creditor)}**: {format_vn(total_owed)}đ"):
                    for item in items: st.write(f"- {item['date']} · {item['name']} · **{format_vn(item['amount'])}đ**")
                    c_info_m = st.session_state.members.get(creditor, {})
                    if c_info_m.get("bank") and c_info_m.get("acc"):
                        st.image(f"https://img.vietqr.io/image/{c_info_m['bank']}-{c_info_m['acc']}-compact2.png?amount={int(total_owed)}", width=250)
                    if st.button("✅ Xác nhận đã chuyển khoản!", key=f"p_{debtor}_{creditor}", type="primary"):
                        _mark_paid(debtor, items)
        else:
            st.subheader("📜 Nợ chéo (đã bù trừ)")
            any_shown = False
            for i, m1 in enumerate(mem_keys):
                for j, m2 in enumerate(mem_keys):
                    if j <= i: continue
                    if m1 not in matrix or m2 not in matrix[m1]: continue
                    net_m1_m2 = matrix[m1][m2] - matrix[m2][m1] if m2 in matrix.get(m1, {}) else matrix[m1][m2]
                    if matrix[m2].get(m1, 0) > matrix[m1][m2]:
                        net_m1_m2 = -(matrix[m2][m1] - matrix[m1][m2])

                    raw12 = matrix[m1].get(m2, 0)
                    raw21 = matrix[m2].get(m1, 0) if m2 in matrix else 0

                    if raw12 > raw21:
                        net_amt = raw12 - raw21
                        if net_amt > 1:
                            any_shown = True
                            with st.expander(f"👉 **{get_pure_name(m1)}** → **{get_pure_name(m2)}**: {format_vn(net_amt)}đ"):
                                ci = st.session_state.members.get(m2, {})
                                if ci.get("bank") and ci.get("acc"):
                                    st.image(f"https://img.vietqr.io/image/{ci['bank']}-{ci['acc']}-compact2.png?amount={int(net_amt)}", width=250)
                                if st.button("✅ Xác nhận đã chuyển!", key=f"n_{m1}_{m2}", type="primary"):
                                    _mark_paid(m1, details[m1][m2])
                    elif raw21 > raw12:
                        net_amt = raw21 - raw12
                        if net_amt > 1:
                            any_shown = True
                            with st.expander(f"👉 **{get_pure_name(m2)}** → **{get_pure_name(m1)}**: {format_vn(net_amt)}đ"):
                                ci = st.session_state.members.get(m1, {})
                                if ci.get("bank") and ci.get("acc"):
                                    st.image(f"https://img.vietqr.io/image/{ci['bank']}-{ci['acc']}-compact2.png?amount={int(net_amt)}", width=250)
                                if st.button("✅ Xác nhận đã chuyển!", key=f"n_{m2}_{m1}", type="primary"):
                                    _mark_paid(m2, details[m2][m1])

            if not any_shown:
                st.info("🎊 Không có khoản nợ nào cần chốt!")

# ════════════════════════════════════════════
#  TAB 4 – NHẬT KÝ
# ════════════════════════════════════════════
with tab4:
    st.subheader("🕒 Lịch sử hóa đơn")

    @st.dialog("⚠️ Xác nhận xoá hóa đơn")
    def confirm_delete_bill(real_index: int, bill_name: str):
        st.write(f"Bạn có chắc muốn xoá bill **{bill_name}** không? Không lấy lại được đâu nha 🥺")
        c1, c2 = st.columns(2)
        if c1.button("Thôi, giữ lại 😅", use_container_width=True): st.rerun()
        if c2.button("Xoá đi! 🗑️", type="primary", use_container_width=True):
            st.session_state.history.pop(real_index)
            save_data(); st.toast("Đã xoá!", icon="✅"); st.rerun()

    if not st.session_state.history:
        st.markdown("""
        <div style='text-align:center; padding:3rem 0;'>
            <div style='font-size:4rem;'>🙌</div>
            <h3 style='color:#ff4b4b; font-family:Nunito,sans-serif;'>Chưa có hóa đơn nào!</h3>
            <p style='color:#aaa;'>Lên kèo đi chơi rồi ghi bill nào~ ✨</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        fc1, fc2 = st.columns(2)
        status_filter = fc1.selectbox("🔍 Bộ lọc:", ["Tất cả 📋", "🔴 Đang nợ", "✅ Đã xong"])
        sort_order = fc2.radio("Sắp xếp:", ["Mới nhất 🆕", "Cũ nhất 📅"], horizontal=True)
        st.divider()

        display_history = [
            (i, b) for i, b in enumerate(st.session_state.history)
            if not ("Đang nợ" in status_filter and b.get("status") == "paid")
            and not ("Đã xong" in status_filter and b.get("status") == "unpaid")
        ]
        if "Cũ" not in sort_order: display_history = list(reversed(display_history))

        for real_idx, b in display_history:
            status_badge = "✅ Xong" if b.get("status") == "paid" else "🔴 Nợ"
            with st.expander(f"[{b['date']}] {b['name']} — {format_vn(b['amount'])}đ  {status_badge}"):
                p_str = ", ".join(f"{get_pure_name(k)} ({format_vn(v)}đ)" for k, v in b.get("payer_data", {}).items())
                st.write(f"**💳 Nguồn tiền:** {p_str}")
                for p_id, amt in b["splits"].items():
                    if amt > 0:
                        done = "✅" if p_id in b.get("paid_by", []) or b.get("status") == "paid" else "🔴"
                        st.write(f"- {get_pure_name(p_id)}: {format_vn(amt)}đ {done}")
                st.divider()
                if st.button("🗑️ Xoá bill này", key=f"del_b_{b['id']}", type="primary"):
                    confirm_delete_bill(real_idx, b["name"])

# ════════════════════════════════════════════
#  TAB 5 – WRAPPED & ANALYTICS
# ════════════════════════════════════════════
with tab5:
    _my_name = get_pure_name(my_id)
    st.markdown(f"""
    <div style='text-align:center; padding:1rem 0 0.5rem;'>
        <div style='font-size:3rem;'>🎁</div>
        <h2 style='font-family:Nunito,sans-serif; font-weight:800; color:#ff4b4b; margin:0;'>
            Share Bills Wrapped
        </h2>
        <p style='color:#aaa; font-size:0.9rem;'>Báo cáo chi tiêu của <b>{_my_name}</b> 📊</p>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.history:
        st.info("🥺 Chưa có dữ liệu. Ghi bill đi để mở khoá báo cáo nha~")
    else:
        now = datetime.now()
        time_filter = st.radio(
            "⏳ Mốc thời gian:",
            [f"Tháng này (T{now.month})", f"Từ đầu năm {now.year}"],
            horizontal=True
        )

        filtered_history = []
        for b in st.session_state.history:
            try:
                m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", str(b["date"]))
                if m:
                    d_m, d_y = int(m.group(2)), int(m.group(3))
                    if ("Tháng này" in time_filter and d_m == now.month and d_y == now.year) or \
                       ("đầu năm" in time_filter and d_y == now.year):
                        filtered_history.append(b)
            except Exception:
                pass

        if not filtered_history:
            st.warning("😔 Không có dữ liệu trong khoảng này.")
        else:
            my_spent = 0.0
            others_owe_me: dict = {}
            i_owe_others: dict = {}
            group_stats: dict = {}
            all_unpaid_debts = []

            for b in filtered_history:
                splits = b.get("splits", {})
                paid_by = b.get("paid_by", [])
                p_data = b.get("payer_data", {})

                if my_id in splits:
                    my_spent += splits[my_id]

                if b.get("status") == "unpaid":
                    bals: dict = {}
                    for p, a in p_data.items():
                        if p not in paid_by: bals[p] = bals.get(p, 0) + a
                    for c, a in splits.items():
                        if c not in paid_by: bals[c] = bals.get(c, 0) - a

                    pos_b = {k: v for k, v in bals.items() if v > 1000}
                    neg_b = {k: v for k, v in bals.items() if v < -1000}
                    tot_pos = sum(pos_b.values())

                    if my_id in bals and tot_pos > 0:
                        my_bal = bals[my_id]
                        if my_bal > 1000:
                            for k, v in neg_b.items():
                                others_owe_me[k] = others_owe_me.get(k, 0) + abs(v) * (my_bal / tot_pos)
                        elif my_bal < -1000:
                            for k, v in pos_b.items():
                                i_owe_others[k] = i_owe_others.get(k, 0) + abs(my_bal) * (v / tot_pos)

                    if tot_pos > 0:
                        for d_id, d_bal in neg_b.items():
                            for c_id, c_bal in pos_b.items():
                                oa = abs(d_bal) * (c_bal / tot_pos)
                                if oa > 1000:
                                    all_unpaid_debts.append({
                                        "debtor": get_pure_name(d_id), "creditor": get_pure_name(c_id),
                                        "amount": int(oa), "item": b.get("name", "Bill")
                                    })

                gn = "Nhóm chung"
                for g_name, g_mems in st.session_state.groups.items():
                    if set(splits.keys()) == set(g_mems): gn = g_name; break
                group_stats.setdefault(gn, {"count": 0, "money": 0})
                group_stats[gn]["count"] += 1
                group_stats[gn]["money"] += b.get("amount", 0)

            # ── Metrics ──
            st.markdown(f"### 📊 Dashboard của {_my_name}")
            c1, c2, c3 = st.columns(3)
            c1.metric("💸 Tiền bạn đã chi", f"{format_vn(my_spent)}đ")

            tot_o_me = sum(others_owe_me.values())
            top_debtor = max(others_owe_me, key=others_owe_me.get) if others_owe_me else None
            if top_debtor:
                c2.metric("😅 Nợ bạn nhiều nhất", get_pure_name(top_debtor),
                          f"{format_vn(others_owe_me[top_debtor])}đ / Tổng: {format_vn(tot_o_me)}đ")
            else:
                c2.metric("😅 Nợ bạn nhiều nhất", "Không ai~", "0đ", delta_color="off")

            tot_i_o = sum(i_owe_others.values())
            top_creditor = max(i_owe_others, key=i_owe_others.get) if i_owe_others else None
            if top_creditor:
                c3.metric("😬 Bạn nợ nhiều nhất", get_pure_name(top_creditor),
                          f"-{format_vn(i_owe_others[top_creditor])}đ / Tổng: -{format_vn(tot_i_o)}đ", delta_color="inverse")
            else:
                c3.metric("😬 Bạn nợ nhiều nhất", "Không ai~", "0đ", delta_color="off")

            st.divider()

            # ── Leaderboard ──
            st.subheader("🔥 Bảng xếp hạng nhóm")
            medals = ["🥇", "🥈", "🥉"]
            for i, (name, s) in enumerate(sorted(group_stats.items(), key=lambda x: x[1]["count"], reverse=True)):
                medal = medals[i] if i < 3 else "🔹"
                st.write(f"{medal} **{name}**: {s['count']} kèo · Tổng: {format_vn(s['money'])}đ")

            st.divider()

            # ── Biểu đồ ──
            st.subheader("📊 Top 10 khoản nợ lớn nhất")
            if all_unpaid_debts:
                top_10 = sorted(all_unpaid_debts, key=lambda x: x["amount"], reverse=True)[:10]
                df_chart = pd.DataFrame({
                    "Khoản nợ": [f"{d['debtor']} ➜ {d['creditor']}\n({d['item']})" for d in top_10],
                    "Số tiền (VNĐ)": [d["amount"] for d in top_10]
                }).set_index("Khoản nợ")
                st.bar_chart(df_chart, color="#ff6b81")
                with st.expander("🔍 Xem bảng số liệu chi tiết"):
                    st.table(df_chart.style.format("{:,}₫"))
            else:
                st.markdown("""
                <div style='text-align:center; padding:2rem;'>
                    <div style='font-size:3rem;'>🎊</div>
                    <p style='color:#aaa; font-weight:600;'>Sổ nợ sạch bong, không có gì để vẽ~</p>
                </div>
                """, unsafe_allow_html=True)
