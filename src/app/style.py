"""CSS cho app. Bố cục bắt chước 2 trang, giữ tông cam đất:

- Cổng Dịch vụ công quốc gia: đầu trang chữ có chân màu đỏ đất, thanh menu ngang, nút vàng nghệ,
  tiêu đề mục chữ hoa gạch chân.
- Kho tri thức UEH (hotro.ueh.edu.vn): banner lớn, câu chào ở giữa, ô tìm kiếm bo tròn có ảnh bên
  cạnh, danh sách "chủ đề hữu ích" dạng mở/đóng, chân trang nhiều cột.

Có 3 ảnh (hoa sen, chim Lạc, hoa văn trống đồng), quản lý trong src/app/images.py. Streamlit không cho sửa HTML
của widget, nên phải chỉnh giao diện bằng CSS nhắm vào class "st-key-<key>" (st.container(key=...)) và
data-testid của tab, nút, ô nhập.
"""
from __future__ import annotations

from src.app.images import url

PALETTE = dict(
    brand="#B8462B",       # đỏ đất nung: chữ tiêu đề, chữ nhấn
    nav="#8E3B23",         # thanh menu, chân trang
    orange="#D6845F",      # cam đất
    accent="#C9653F",      # tab đang chọn, gạch chân
    gold="#FBC254",        # nút vàng nghệ
    gold_dark="#E9A92C",
    cream="#FFF6EC",
    paper="#FFFDF8",
    ink="#3B2A22",
    muted="#7B6A60",
    line="#EADBCB",
    gray="#F3F2F0",
)


def css() -> str:
    p = PALETTE
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Nunito:ital,wght@0,400;0,600;0,700;0,800;1,400&family=Noto+Serif:ital,wght@0,500;0,700;1,400&display=swap');

:root {{
  --brand:{p['brand']}; --nav:{p['nav']}; --orange:{p['orange']}; --accent:{p['accent']}; --gold:{p['gold']};
  --gold-dark:{p['gold_dark']}; --cream:{p['cream']}; --paper:{p['paper']}; --ink:{p['ink']}; --muted:{p['muted']};
  --line:{p['line']}; --gray:{p['gray']};
}}
.stApp, .stApp p, .stApp li, .stApp label, .stApp button, .stApp input, .stApp textarea {{ font-family:'Nunito', system-ui, sans-serif; }}
[data-testid="stIconMaterial"] {{ font-family:'Material Symbols Rounded' !important; }}
.stApp {{ background:var(--paper); color:var(--ink); }}
#MainMenu, footer, header[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"] {{ display:none !important; }}
.block-container {{ padding-top:0 !important; padding-bottom:0 !important; max-width:1180px; }}

/* ---------- đầu trang (kiểu cổng Chính phủ) ---------- */
.site-header {{ display:flex; align-items:center; gap:18px; padding:16px 0 14px; }}
.site-header .title {{ font-family:'Noto Serif', serif; font-weight:700; color:var(--brand); font-size:30px;
  letter-spacing:.5px; line-height:1.15; text-transform:uppercase; }}
.site-header .title .big {{ font-size:40px; }}
.site-header .tagline {{ font-style:italic; color:#C0603F; font-size:16px; margin-top:4px; }}
.site-header .badges {{ margin-left:auto; display:flex; flex-direction:column; gap:8px; align-items:flex-end; }}
.badge-out {{ border:1.5px solid var(--brand); color:var(--brand); border-radius:4px; padding:6px 14px; font-weight:700;
  font-size:14px; background:#fff; white-space:nowrap; }}
.badge-soft {{ color:var(--muted); font-size:12.5px; }}

/* ---------- thanh menu (thanh đậm như UEH, màu cam đất) ---------- */
[data-testid="stTabs"] [role="tablist"] {{ gap:0; background:var(--nav); border:none;
  box-shadow:0 0 0 100vmax var(--nav); clip-path:inset(0 -100vmax); }}
[data-testid="stTabs"] [role="tablist"]::after, [data-testid="stTabs"] .react-aria-SelectionIndicator {{ display:none !important; }}
[data-testid="stTab"] {{ height:54px; padding:0 22px; background:transparent; border-radius:0; margin:0;
  display:flex; align-items:center; border-bottom:4px solid transparent; }}
[data-testid="stTab"] p {{ font-size:17.5px; font-weight:700; color:#FBE6D6; }}
[data-testid="stTab"][aria-selected="true"] {{ background:var(--accent); border-bottom-color:var(--gold); }}
[data-testid="stTab"][aria-selected="true"] p, [data-testid="stTab"]:hover p {{ color:#fff; }}
[data-testid="stTabs"] [role="tabpanel"] {{ padding-top:0; }}

/* ---------- banner (kiểu banner UEH: nền chuyển màu + khối hình học, không dùng ảnh) ---------- */
.banner {{ width:100vw; margin-left:calc(50% - 50vw); color:#fff; overflow:hidden;
  background:linear-gradient(100deg, #7E2F1C 0%, #A8432A 45%, #C9653F 75%, #D6845F 100%); }}
.banner .inner {{ position:relative; max-width:1180px; height:300px; margin:0 auto; padding:0 1rem; }}
.banner .text {{ position:absolute; left:1rem; top:44px; max-width:70%; }}
.banner .kicker {{ display:inline-block; background:var(--gold); color:var(--ink); font-weight:800; font-size:13px;
  letter-spacing:.8px; padding:4px 12px; border-radius:3px; text-transform:uppercase; }}
.banner h1 {{ font-family:'Noto Serif', serif; font-size:38px; line-height:1.2; margin:14px 0 8px; color:#fff;
  text-shadow:0 2px 6px rgba(60,20,10,.4); padding:0; }}
.banner .sub {{ font-size:17px; color:#FFE9D9; }}
.banner .stats {{ display:flex; gap:10px; margin-top:18px; flex-wrap:wrap; }}
.banner .stats span {{ background:rgba(255,255,255,.14); border:1px solid rgba(255,255,255,.35); border-radius:999px;
  padding:5px 14px; font-weight:700; font-size:14px; backdrop-filter:blur(2px); }}
.banner .tri {{ position:absolute; right:-40px; bottom:-60px; width:240px; height:160px; background:var(--gold);
  transform:rotate(-24deg); opacity:.95; }}
.banner .tri2 {{ position:absolute; right:120px; top:-70px; width:200px; height:120px; background:var(--orange);
  transform:rotate(28deg); opacity:.85; }}

/* ---------- dải chim Lạc (ảnh hoạ tiết thật, tô màu bằng mask) ---------- */
/* Mỗi con chim là 1 thẻ <i> riêng, xếp hàng ngang: dòng nào không đủ chỗ thì rơi xuống và bị ẩn,
   nên mọi con hiện ra đều nguyên vẹn (không bị cắt đầu / đuôi ở mép). */
.frieze {{ display:flex; flex-wrap:wrap; justify-content:space-between; height:46px; overflow:hidden; gap:0 18px; }}
.frieze i {{ flex:0 0 160px; height:46px; background:var(--accent);
  -webkit-mask:url("{url('chim_lac')}") center / contain no-repeat; mask:url("{url('chim_lac')}") center / contain no-repeat; }}

/* ---------- khu tìm kiếm (kiểu UEH: logo tròn, câu chào, ô bo tròn, ảnh hai bên) ---------- */
.st-key-hero {{ position:relative; padding:26px 0 22px; gap:10px;
  background:
    linear-gradient(rgba(255,246,236,.90), rgba(255,246,236,.90)),
    url("{url('hoa_van_trong_dong')}") center 40%/540px no-repeat, var(--cream);
  box-shadow:0 0 0 100vmax var(--cream); clip-path:inset(0 -100vmax); }}
.hero-title {{ text-align:center; margin-top:10px !important; font-size:32px; font-weight:600; color:var(--ink); margin:2px 0 0; }}
.hero-title b {{ color:var(--brand); font-weight:800; }}
.hero-sub {{ text-align:center; color:var(--muted); font-size:15px; margin:2px 0 6px; }}
.side-photo {{ width:100%; aspect-ratio: 3/4; border-radius:120px 120px 14px 14px; background-size:cover;
  background-position:center; box-shadow:0 0 0 5px #fff, 0 8px 20px rgba(120,50,20,.18); margin-top:18px; }}
.side-cap {{ text-align:center; font-size:12px; color:var(--muted); margin-top:10px; font-style:italic; }}
.st-key-hero [data-testid="stForm"] {{ border:none; padding:0; background:transparent; }}
.st-key-hero [data-testid="stTextInputRootElement"] {{ height:56px; border:1.5px solid #E2C2A8; border-radius:999px; background:#fff;
  padding-left:14px; box-shadow:0 4px 14px rgba(120,50,20,.08); }}
.st-key-hero [data-testid="stTextInputRootElement"]:focus-within {{ border-color:var(--accent); }}
.st-key-hero [data-testid="stTextInputField"] {{ font-size:18px; color:var(--ink); }}
.st-key-hero [data-testid="stFormSubmitButton"] button {{ height:56px; width:100%; background:var(--accent); color:#fff;
  border:none; border-radius:999px; font-weight:800; font-size:17px; }}
.st-key-hero [data-testid="stFormSubmitButton"] button:hover {{ background:var(--brand); color:#fff; }}
.st-key-quick button {{ background:var(--gold); color:var(--ink); border:none; min-height:46px; border-radius:999px;
  font-weight:700; box-shadow:0 2px 0 rgba(120,60,20,.15); }}
.st-key-quick button:hover {{ background:var(--gold-dark); color:var(--ink); }}
.st-key-quick button p {{ font-size:15.5px; }}

/* ---------- tiêu đề mục (kiểu cổng Chính phủ) ---------- */
.sec-title {{ text-align:center; color:var(--accent); font-size:23px; font-weight:700; letter-spacing:.5px;
  text-transform:uppercase; padding-bottom:10px; border-bottom:4px solid var(--accent); margin:26px 0 16px; }}
.sec-title.left {{ text-align:left; }}

/* ---------- chủ đề hữu ích (accordion kiểu UEH, tông cam) ---------- */
.st-key-topics [data-testid="stExpander"] details {{ border:none; border-radius:0; background:transparent; margin-bottom:6px; }}
.st-key-topics [data-testid="stExpander"] summary {{ background:#FCEBDD; border:1px solid #F1D2BC; border-radius:6px;
  padding:12px 16px; }}
.st-key-topics [data-testid="stExpander"] details[open] summary {{ border-radius:6px 6px 0 0; background:#F6D7C2; }}
.st-key-topics [data-testid="stExpander"] summary p {{ font-size:17px; font-weight:700; color:var(--ink); }}
.st-key-topics [data-testid="stExpander"] summary [data-testid="stIconMaterial"] {{ color:var(--accent); }}
.st-key-topics [data-testid="stExpanderDetails"] {{ background:#F3DFD1; border:1px solid #F1D2BC; border-top:none;
  border-radius:0 0 6px 6px; padding:6px 10px 10px; }}
.st-key-topics [data-testid="stExpanderDetails"] button {{ background:transparent; border:none; justify-content:flex-start;
  text-align:left; min-height:34px; padding:2px 10px; color:#4A3328; }}
.st-key-topics [data-testid="stExpanderDetails"] button:hover {{ color:var(--brand); text-decoration:underline; background:rgba(255,255,255,.35); }}
.st-key-topics [data-testid="stExpanderDetails"] button, .st-key-similar button {{ justify-content:flex-start !important; }}
.st-key-topics [data-testid="stExpanderDetails"] button > div, .st-key-similar button > div,
.st-key-topics [data-testid="stExpanderDetails"] button > div > span, .st-key-similar button > div > span {{
  justify-content:flex-start !important; text-align:left; width:100%; }}
.st-key-topics [data-testid="stExpanderDetails"] button p, .st-key-similar button p {{ text-align:left; font-size:15.5px; }}
.topic-meta {{ font-size:13px; color:var(--muted); padding:2px 10px 4px; }}
.how-card {{ background:#fff; border:1px solid var(--line); border-radius:10px; overflow:hidden; }}
.how-card .bd {{ padding:14px 18px 16px; font-size:15.5px; line-height:1.6; }}
.how-card .bd b {{ color:var(--brand); }}

/* ---------- thẻ câu trả lời ---------- */
.answer-card {{ background:var(--cream); border:1px solid var(--line); border-left:6px solid var(--brand);
  border-radius:6px; padding:18px 22px; }}
.answer-card .label {{ display:flex; align-items:center; gap:10px; color:var(--brand); font-weight:800;
  letter-spacing:.6px; font-size:13px; text-transform:uppercase; margin-bottom:6px; }}
.answer-card .cite {{ font-weight:700; color:var(--ink); }}
.answer-card blockquote {{ font-family:'Noto Serif', serif; font-size:17.5px; line-height:1.65; margin:8px 0 10px;
  padding:4px 0 4px 16px; border-left:3px solid var(--gold); color:#2E211B; }}
.answer-card .part-q {{ font-weight:700; color:#8A3B22; margin-top:12px; }}
.answer-card .src-link a {{ color:var(--brand); font-weight:700; text-decoration:none; }}
.answer-card .src-link a:hover {{ text-decoration:underline; }}
.refuse-card {{ background:#FFF4E0; border:1px solid #F1D6A6; border-left:6px solid var(--gold-dark); border-radius:6px; padding:18px 22px; }}
.refuse-card .label {{ color:#9A5B10; font-weight:800; letter-spacing:.6px; font-size:13px; text-transform:uppercase; }}
.refuse-card p {{ margin:6px 0; font-size:16.5px; }}
.chip {{ display:inline-block; padding:2px 10px; border-radius:999px; font-size:12.5px; font-weight:700; margin-right:6px; }}
.chip.ok {{ background:#E7F0DF; color:#43662F; }}
.chip.part {{ background:#F8E3D7; color:#9A3F22; }}
.chip.muted {{ background:var(--gray); color:var(--muted); }}
.note {{ background:#F4F7EF; border:1px solid #D8E3CB; border-radius:6px; padding:10px 14px; margin-top:10px; font-size:14.5px; }}
.note b {{ color:#4C6B36; }}

/* ---------- đoạn trích ---------- */
.excerpt {{ font-family:'Noto Serif', serif; font-size:15.5px; line-height:1.7; color:#33261F; }}
.excerpt mark {{ background:#FCE3A1; color:inherit; padding:0 2px; border-radius:2px; }}
.excerpt .quote-line {{ background:#FBEBDD; box-shadow:-8px 0 0 #FBEBDD, 8px 0 0 #FBEBDD; border-radius:2px; }}
.src-head {{ font-size:14px; color:var(--muted); margin-bottom:6px; }}
.src-head b {{ color:var(--ink); }}
.scorebar {{ height:6px; background:#F0E4D8; border-radius:4px; overflow:hidden; margin:4px 0 10px; }}
.scorebar span {{ display:block; height:100%; background:linear-gradient(90deg, var(--gold), var(--brand)); }}
[data-testid="stExpander"] details {{ border:1px solid var(--line); border-radius:6px; background:#fff; }}
[data-testid="stExpander"] summary p {{ font-weight:700; }}

/* ---------- cột phải ---------- */
.st-key-similar button {{ text-align:left; justify-content:flex-start; background:#fff; border:1px solid var(--line);
  border-radius:10px; min-height:46px; color:var(--ink); }}
.st-key-similar button:hover {{ border-color:var(--brand); color:var(--brand); }}
.st-key-clarify button {{ background:#fff; border:1px dashed #D9A35E; border-radius:999px; color:#8A5414; }}
.st-key-feedback button {{ border-radius:999px; border:1.5px solid var(--line); background:#fff; font-weight:700; }}
.st-key-feedback button:hover {{ border-color:var(--brand); color:var(--brand); }}

/* ---------- thống kê, giới thiệu ---------- */
[data-testid="stMetric"] {{ background:var(--cream); border:1px solid var(--line); border-radius:8px; padding:14px 16px; }}
[data-testid="stMetricValue"] {{ color:var(--brand); font-weight:800; }}
.pipeline {{ display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin:8px 0 4px; }}
.pipeline .step {{ background:#fff; border:1.5px solid var(--line); border-radius:6px; padding:8px 12px; font-weight:700; font-size:14.5px; }}
.pipeline .step small {{ display:block; font-weight:400; color:var(--muted); font-size:12px; }}
.pipeline .arrow {{ color:var(--brand); font-weight:800; }}

/* ---------- chân trang (nhiều cột kiểu UEH) ---------- */
.site-footer {{ margin-top:44px; background:#6E2A18; color:#F8E7D6; box-shadow:0 0 0 100vmax #6E2A18;
  clip-path:inset(0 -100vmax); padding:0 0 22px; font-size:14px; }}
.site-footer .frieze {{ margin:12px 0 14px; }}
.site-footer .frieze i {{ background:#F2B98F; }}
.site-footer .cols {{ display:flex; gap:28px; flex-wrap:wrap; align-items:flex-start; }}
.site-footer .cols > div {{ flex:1 1 220px; line-height:1.6; }}
.site-footer h4 {{ color:#FFD887; font-size:15px; margin:0 0 6px; padding:0; }}
.site-footer a {{ color:#FBE3CF; text-decoration:none; }}
.site-footer a:hover {{ color:#FFD887; text-decoration:underline; }}
.site-footer .copy {{ border-top:1px solid rgba(255,255,255,.15); margin-top:14px; padding-top:10px; font-size:12.5px; color:#E6C6B2; }}

@media (max-width: 760px) {{
  .site-header .title {{ font-size:22px; }} .site-header .title .big {{ font-size:28px; }}
  .site-header .badges {{ display:none; }}
  [data-testid="stTab"] {{ padding:0 12px; }} [data-testid="stTab"] p {{ font-size:15px; }}
  .banner .inner {{ height:auto; padding:28px 1rem 40px; }} .banner .text {{ position:static; max-width:100%; }}
  .banner .tri, .banner .tri2 {{ display:none; }}
  .banner h1 {{ font-size:28px; }} .hero-title {{ font-size:24px; }}
}}
</style>
"""
