# Product Requirements Document — CircleFi

**NEOMA MSc Fintech & DeFi — Final Group Project**
**Team:** Aadhithya Raj, Samarth Srivastava, Nidhi Mamtora, Naman Nailwal
**Date:** November 2026

---

## 1. Objective / Goal

Students and young, underbanked adults often lack access to affordable credit and have
no easy, trustworthy way to save with peers. **CircleFi** digitizes the Rotating Savings
and Credit Association (ROSCA) — known as a "tanda," "chit fund," or "susu" in different
cultures — into a simple fintech app. A group of people agree to contribute a fixed
amount every cycle (e.g. weekly or monthly) into a shared pot, and one member receives
the full pot each cycle on a rotating basis until everyone has been paid out once.

The goal of CircleFi is to make this informal, trust-based savings model **transparent,
auditable, and fair** by recording every contribution and payout on an append-only,
cryptographically hash-chained ledger — giving the trust guarantees associated with
blockchain (immutability, verifiability) without requiring members to own crypto
wallets or pay gas fees for an MVP aimed at first-time users.

## 2. Target Users & Stakeholders

- **Primary users:** University students and young professionals (18–30) with limited
  credit history, who want to save consistently and occasionally need access to a lump
  sum earlier than they could save alone (e.g. for a deposit, tuition, or emergency).
- **Secondary users:** Diaspora and community groups who already run informal ROSCAs
  (common in Latin America, West Africa, and South/Southeast Asia) and want a digital,
  transparent record instead of a notebook or group chat.
- **Stakeholders:** The circle "organizer" (sets up the circle and cycle rules),
  participating members, and — in a future version — a partner credit union or
  microfinance institution that could use on-time contribution history as alternative
  credit data.

## 3. Key Features

1. **Create a Savings Circle** — organizer defines circle name, contribution amount,
   number of members, and cycle length.
2. **Join & Contribute** — members join an existing circle and make their contribution
   for the current cycle; each contribution is written to the hash-chain ledger.
3. **Automated Rotating Payout** — once all members have contributed for a cycle, the
   app identifies whose turn it is (round-robin) and marks the payout, advancing the
   circle to the next cycle.
4. **Tamper-Evident Ledger & Verification** — a full transaction log where every entry
   stores the SHA-256 hash of its own data plus the previous entry's hash (a simplified
   blockchain). A one-click "Verify Chain Integrity" check recomputes all hashes to
   prove the ledger hasn't been altered.
5. **Trust Score Dashboard** — every member gets a trust score based on on-time
   contribution rate, visualized alongside circle progress (pot growth, contribution
   history, payout schedule) with charts.

*(Deliberately kept to 5 features, per the course's PRD guidance: keep it to 3–5.)*

## 4. Technical Architecture

- **Frontend / App layer:** Streamlit (Python) — single-page app with sidebar
  navigation across the five features above.
- **Data layer:** SQLite (via Python's built-in `sqlite3`), stored as a local file
  (`circlefi.db`) so data persists across app restarts and can be inspected directly.
- **Integrity layer:** A custom hash-chain module (`ledger.py`-style logic embedded in
  `app.py`) using `hashlib.sha256`, conceptually identical to a blockchain's linked-block
  structure: `hash_n = SHA256(data_n + hash_{n-1})`.
- **Architecture choice — centralized MVP with blockchain-style guarantees:** The
  ledger is centralized (single SQLite file) rather than deployed on a public chain.
  This is a deliberate MVP decision: it avoids wallet onboarding friction and gas fees
  for non-crypto-native users (our target market), while still providing tamper-evidence
  via hash-chaining. **Roadmap:** migrate the ledger to an Ethereum L2 (e.g. Base or
  Polygon) using a smart contract once the user base and trust requirements justify the
  added cost and complexity — at that point CircleFi becomes a true decentralized app.
- **Tech stack:** Python 3, Streamlit, SQLite, hashlib, pandas (for charts), matplotlib/
  Streamlit native charting.

## 5. Non-Functional Requirements

- **Usability:** No crypto wallet, gas fees, or technical knowledge required to join a
  circle; all actions are simple forms and buttons.
- **Security:** Contribution and payout records are hash-chained so any retroactive edit
  to the database is detectable via the "Verify Chain Integrity" check. No real money or
  payment credentials are handled in this MVP (simulated balances only).
- **Reliability:** Data persists locally via SQLite; the app recovers its full state on
  restart.
- **Portability:** Runs identically on any machine with Python + Streamlit installed
  (`streamlit run app.py`); no external services required for the demo.
- **Transparency:** Every member can view the full ledger and verify it themselves —
  no action is hidden from participants.

## 6. Milestones / Timeline

| Milestone | Target |
|---|---|
| Idea validation & PRD draft | Week 1 |
| Core data model + hash-chain ledger | Week 2 |
| Streamlit UI: create/join/contribute flows | Week 3 |
| Payout rotation logic + trust score + dashboard | Week 4 |
| Internal testing & bug fixes | Week 5 |
| Final polish, slides, PRD finalization | Week 6 |
| Submission & live demo | 15 December 2026 |

## 7. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Members miss a contribution, stalling the whole circle | Trust score penalty + organizer can mark a member "at risk" and circle can continue once caught up |
| Centralized ledger is a single point of failure/trust (vs. "real" blockchain) | Clearly scoped as MVP; hash-chaining still makes tampering detectable; roadmap item to move to a public chain |
| Users could dispute a contribution/payout | Full ledger is visible to all members at all times, with independently verifiable hashes |
| Demo day technical failure | SQLite file is portable and pre-seeded with sample data so the demo can run offline with no network dependency |

## 8. Success Metrics

- A circle can be created, fully funded, and cycled through at least one full payout
  rotation without errors during the live demo.
- Ledger integrity check correctly **passes** on an unmodified database and correctly
  **fails** (detects tampering) when a record is manually edited — demonstrating the
  core value proposition.
- Trust scores and dashboard charts update correctly as contributions are made.
- Qualitative: reviewers (instructor/classmates) can explain, after the demo, what
  problem CircleFi solves and for whom, without needing further explanation.
