# Firebase: optional cloud progress sync

Progress is **local by default** (`localStorage`). Firebase is only used when a learner clicks **Save online / Lưu online** and signs in with Google.

## 1. Create a Firebase project

1. Open [Firebase Console](https://console.firebase.google.com/) → Create project
2. Add a **Web** app and copy the config values
3. **Authentication** → Sign-in method → enable **Google**
4. **Authentication** → Settings → Authorized domains: add `localhost` and your Vercel domain
5. **Firestore Database** → Create database (production mode)
6. Paste rules from `firestore.rules` (users can only read/write their own progress)

## 2. Configure the build

Local:

```bash
cp .env.example .env
# fill FIREBASE_* values
python3 build_preview_vi.py
```

Vercel → Project → Settings → Environment Variables:

| Name | Example |
|------|---------|
| `FIREBASE_API_KEY` | `AIza...` |
| `FIREBASE_AUTH_DOMAIN` | `your-app.firebaseapp.com` |
| `FIREBASE_PROJECT_ID` | `your-app` |
| `FIREBASE_STORAGE_BUCKET` | `your-app.appspot.com` |
| `FIREBASE_MESSAGING_SENDER_ID` | `123...` |
| `FIREBASE_APP_ID` | `1:123:web:...` |

Rebuild/redeploy after setting these. Without them, the app still works with **local-only** progress (no Sign-in button).

## 3. How sync works

- Not signed in → progress only on this browser
- Sign in with Google → merge local + cloud (newer lesson timestamps win), then keep both in sync
- Sign out → local copy stays; cloud keeps the last synced state
- Reset while signed in → clears local and cloud for that account

Data path: `users/{uid}/progress/course`
