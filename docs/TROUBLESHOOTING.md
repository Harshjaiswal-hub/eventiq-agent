# EventIQ Agent — Troubleshooting & Diagnostics Playbook

## 1. Port Conflict (`OSError: [Errno 98 / 10048] Address already in use`)

### Symptom:
Server fails to start with:
`[!] Port 3000 is currently in use.`

### Resolution:
1. Check what process is occupying port 3000:
   - **Windows:**
     ```powershell
     netstat -ano | findstr :3000
     taskkill /PID <PID> /F
     ```
   - **Linux/macOS:**
     ```bash
     lsof -i :3000
     kill -9 <PID>
     ```
2. Or start EventIQ on an alternate port:
   ```bash
   PORT=8080 python server.py
   ```

---

## 2. Database Locked (`sqlite3.OperationalError: database is locked`)

### Symptom:
Writes fail under high concurrency with database locked error.

### Root Cause & Resolution:
EventIQ is configured with **Write-Ahead Logging (`WAL`)** and `busy_timeout = 5000` ms, which accommodates concurrent readers and writers. If a lock persists:
1. Ensure no rogue process has an exclusive lock on `eventiq.db`.
2. Delete leftover WAL shared memory files (`eventiq.db-shm`, `eventiq.db-wal`) only when the server is stopped:
   ```bash
   rm -f eventiq.db-shm eventiq.db-wal
   ```
3. Restart the server.

---

## 3. Rate Limit Lockouts (`429 Too Many Requests`)

### Symptom:
User receives:
`Too many failed login attempts. Account locked for 900 seconds.`

### Resolution:
- Login rate limits are tracked in-memory (5 failed attempts per 15 minutes).
- To clear immediately in development, restart the server process.
- In production, wait for the window to expire or inspect `security_logs` to ensure no brute force attack is underway.

---

## 4. CSRF Validation Failures (`403 Forbidden: CSRF validation failed`)

### Symptom:
State-changing API calls (`/api/recommendations/decision`, `/api/agent/audit`) return 403 CSRF error.

### Resolution:
- Ensure the client passes the `X-CSRF-Token` header matching the token received from `/api/auth/login` or `/api/auth/me`.
- If using API scripts, authenticate using `Authorization: Bearer <session_token>` header instead of cookies; Bearer tokens automatically bypass CSRF validation.

---

## 5. Session Expiry & Cookies

### Symptom:
User is unexpectedly logged out or `/api/auth/me` returns 401.

### Resolution:
- Sessions expire after **8 hours**.
- If `SECURE_COOKIES=True` is enabled in `.env` while accessing over plain `http://`, the browser rejects the cookie. Set `SECURE_COOKIES=False` in local HTTP environments.
