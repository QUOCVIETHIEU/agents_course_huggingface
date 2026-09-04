# Deploy Agents Course Learn App to Vercel

App học offline/local từ repo clone [huggingface/agents-course](https://github.com/huggingface/agents-course).

## Trước khi deploy

1. **Không push lên repo Hugging Face gốc.** Tạo repo GitHub riêng của bạn (fork hoặc repo mới) rồi push bản dịch + UI.
2. Tiến độ mặc định dùng `localStorage` trên từng trình duyệt. Đồng bộ cloud là **tùy chọn** (xem `FIREBASE_SETUP.md`).

## Deploy nhanh (CLI)

```bash
cd agents-course
npx vercel login
npx vercel          # preview
npx vercel --prod   # production
```

## Deploy qua GitHub

1. Push project lên repo của bạn
2. Vào [vercel.com/new](https://vercel.com/new) → Import repo
3. Framework Preset: **Other**
4. Build Command: `pip install -r requirements.txt && python build_preview_vi.py`
5. Output Directory: `preview-vi`
6. (Tuỳ chọn) Thêm biến môi trường `FIREBASE_*` theo `FIREBASE_SETUP.md` rồi Deploy

Sau khi lên, mọi người mở URL Vercel là học được (EN/VN). Không bắt buộc đăng nhập.

## Lưu ý

- Không đăng nhập → tiến độ chỉ trên thiết bị.
- Đăng nhập Google → tiến độ theo tài khoản (merge local + cloud).
- Repo `origin` hiện trỏ Hugging Face — tạo repo GitHub của bạn rồi `git remote add mine <url>` trước khi push.
