import streamlit as st
from PIL import Image, ImageDraw
import math, os, time
from datetime import datetime, timedelta

st.set_page_config(page_title="Rikoten Image Processor", layout="wide", initial_sidebar_state="expanded")

DARK_MODE_CSS = """
<style>
html, body {
    background-color: #0e1117;
    color: #e5e7eb;
}
[data-testid="stAppViewContainer"], [data-testid="stSidebar"], [data-testid="stHeader"] {
    background-color: #0e1117;
    color: #e5e7eb;
}
[data-testid="stSidebar"] * {
    color: #e5e7eb !important;
}
.stButton>button, .stDownloadButton>button {
    background-color: #1f2933;
    color: #e5e7eb;
    border: 1px solid #3e4c59;
}
.stButton>button:hover, .stDownloadButton>button:hover {
    background-color: #323f4b;
    border-color: #52606d;
}
.stRadio>div>label, .stFileUploader label {
    color: #e5e7eb;
}
</style>
"""

st.markdown(DARK_MODE_CSS, unsafe_allow_html=True)

# -----------------------------
# 設定
# -----------------------------
UPLOAD_DIR = "uploads"
PROCESSED_DIR = "uploads/processed"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

ADMIN_PASS = st.secrets.ADMIN_PASS  # 企画側パスコード(Streamlit Secretsで設定)
EXPIRE_SECONDS = 120  # ファイルの有効期限(秒)


# -----------------------------
# 古いファイル削除
# -----------------------------
def cleanup_old_files():
    now = time.time()
    for folder in [UPLOAD_DIR, PROCESSED_DIR]:
        for f in os.listdir(folder):
            path = os.path.join(folder, f)
            if os.path.isfile(path) and now - os.path.getmtime(path) > EXPIRE_SECONDS:
                os.remove(path)


# -----------------------------
# 加工スクリプト関数
# -----------------------------
def process_image(src_path, outfile):
    canvas_size = 1200
    ring_radius = 330
    angles = [0, 90, 180, 270]
    center_square_ratio = 0.05  # 中央白枠の大きさ（キャンバスに対する割合）
    margin = 20  # リング中心からの余白

    im = Image.open(src_path).convert("RGBA")
    original_width, original_height = im.size

    # 元画像サイズを維持してリサイズ（隣の画像と重ならないよう調整）
    max_extent = ring_radius - margin
    scale = min(1.0, max_extent / original_width, max_extent / original_height)
    if scale < 1.0:
        resized_width = max(1, int(original_width * scale))
        resized_height = max(1, int(original_height * scale))
        im = im.resize((resized_width, resized_height), Image.Resampling.LANCZOS)

    # キャンバス作成
    canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 255))
    cx, cy = canvas_size // 2, canvas_size // 2

    def paste_center(base, img, x, y):
        x0 = int(x - img.width // 2)
        y0 = int(y - img.height // 2)
        base.alpha_composite(img, (x0, y0))

    # 回転コピーを配置
    for ang in angles:
        rim = im.rotate(-ang, resample=Image.Resampling.BICUBIC, expand=True)
        rad = math.radians(ang)
        x = cx + ring_radius * math.sin(rad)
        y = cy - ring_radius * math.cos(rad)
        paste_center(canvas, rim, x, y)

    # 中央の白枠
    draw = ImageDraw.Draw(canvas)
    center_square = int(canvas_size * center_square_ratio)
    half = center_square // 2
    draw.rectangle([cx - half, cy - half, cx + half, cy + half], outline=(255, 255, 255, 255), width=6)

    canvas_to_save = canvas
    if outfile.lower().endswith((".jpg", ".jpeg")):
        canvas_to_save = canvas.convert("RGB")
    canvas_to_save.save(outfile)


# -----------------------------
# ページ切り替え
# -----------------------------
st.sidebar.title("メニュー")
page = st.sidebar.radio("ページを選択", ["ゲスト用（アップロード）", "企画側用（表示）"])


# -----------------------------
# お客さんページ
# -----------------------------
if page == "ゲスト用（アップロード）":
    st.title("画像アップロードページ")
    uploaded_file = st.file_uploader("画像をアップロードしてください。著作権等の問題があるものはお控えください。  \nアップロードされたファイルは約1時間後に自動で削除されます。", type=["jpg", "png", "jpeg"])

    if uploaded_file:
        # 保存先パス
        base_name = datetime.now().strftime("%Y%m%d_%H%M%S_") + uploaded_file.name
        src_path = os.path.join(UPLOAD_DIR, base_name)
        with open(src_path, "wb") as f:
            f.write(uploaded_file.read())

        # 加工実行
        out_path = os.path.join(PROCESSED_DIR, f"processed_{base_name}")
        process_image(src_path, out_path)

        st.success("アップロード＆処理が完了しました！")
        st.image(out_path, caption="加工後の画像", use_container_width=True)

    cleanup_old_files()


# -----------------------------
# 企画側ページ
# -----------------------------
elif page == "企画側用（表示）":
    st.title("企画側ページ")

    password = st.text_input("パスコードを入力してください", type="password")
    if password == ADMIN_PASS:
        st.success("認証成功！")

        # 再読み込みボタンを追加
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("🔄 ファイルを再読み込み"):
                st.rerun()

        cleanup_old_files()
        files = sorted(os.listdir(PROCESSED_DIR), reverse=True)

        if not files:
            st.info("現在アップロードされた画像はありません。")
        else:
            st.write(f"**現在の画像数: {len(files)}件**")
            for f in files:
                path = os.path.join(PROCESSED_DIR, f)
                upload_time = datetime.fromtimestamp(os.path.getmtime(path))
                expire_time = upload_time + timedelta(seconds=EXPIRE_SECONDS)
                st.image(Image.open(path), caption=f"{f}（削除予定: {expire_time:%H:%M:%S}）", use_container_width=True)
    elif password:
        st.error("パスコードが間違っています。")
