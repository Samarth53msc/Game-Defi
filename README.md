# CircleFi

A blockchain-inspired rotating savings circle (ROSCA) app, built for the NEOMA MSc
Fintech & DeFi final group project. See `PRD.md` for the full product requirements
document.

## Run it

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open the local URL Streamlit prints (usually http://localhost:8501).

## Demo tips

1. Go to **Overview** and click **"Seed sample demo circle"** to instantly load a
   circle with 4 members and 2 completed payout cycles — no manual setup needed.
2. Go to **Join & Contribute**, pick the demo circle, and make the next contribution(s)
   to trigger a live payout.
3. Go to **Ledger & Verification**, click **"Verify chain integrity"** (should pass),
   then use **"Simulate tampering"** followed by **Verify** again to show the hash
   chain catching a tampered record — this is the core value proposition to highlight
   in the live demo.
4. Go to **Trust & Dashboard** to show trust scores and pot growth charts.

## Files

- `app.py` — the Streamlit app (UI + hash-chain ledger + ROSCA logic).
- `PRD.md` — product requirements document (2–4 pages, per assignment guidelines).
- `circlefi.db` — SQLite database created automatically on first run (safe to delete
  to reset all data).
