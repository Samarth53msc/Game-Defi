# How CircleFi Actually Works

A technical walkthrough for explaining the mechanics confidently during the live demo
and answering follow-up questions. Pairs with `DEMO_SCRIPT.md` (which covers the
run-of-show and click sequence) — this document covers the *why* and *how* underneath
each click.

## 1. The big picture

```
Browser (Streamlit UI)  <-->  app.py (Python)  <-->  circlefi.db (SQLite file)
                                     |
                                     v
                          hash-chain logic (hashlib.sha256)
```

There is no server beyond the single Python process Streamlit runs. All "backend"
logic — creating circles, recording contributions, computing payouts, verifying the
ledger — happens in plain Python functions inside `app.py`, reading and writing one
SQLite file (`circlefi.db`) that sits next to the code.

## 2. The data model (3 tables)

- **`circles`** — one row per savings circle: its name, the contribution amount per
  member per cycle, and `current_cycle` (which round is currently open).
- **`members`** — one row per person in a circle, with a `join_order` (0, 1, 2, 3…)
  that determines payout rotation order.
- **`ledger`** — the append-only transaction log. Every contribution and every payout
  is one row here. This is the table that matters most for the demo.

Each `ledger` row stores: `circle_id`, `cycle`, `entry_type` (`contribution` or
`payout`), `member_id`, `amount`, `timestamp`, and two hash columns: `prev_hash` and
`hash`.

## 3. The hash chain, concretely

This is the core idea, and the thing to explain slowly and clearly:

```python
def compute_hash(circle_id, cycle, entry_type, member_id, amount, timestamp, prev_hash):
    payload = f"{circle_id}|{cycle}|{entry_type}|{member_id}|{amount}|{timestamp}|{prev_hash}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
```

Every new ledger entry:
1. Looks up the **hash of the previous entry** (`prev_hash`) — or a string of 64 zeros
   if it's the very first entry in that circle (the "genesis" row).
2. Builds a single string combining every field of the new entry *plus* that previous
   hash.
3. Runs that whole string through SHA-256 to get a new, unique 64-character hash.
4. Stores both `prev_hash` and the new `hash` on the row.

The key property: **the new hash depends on the previous hash.** So entry #10's hash
depends on entry #9's hash, which depends on entry #8's, all the way back to entry #1.
This is exactly the "chain" in blockchain — each block/record is cryptographically
glued to the one before it.

**What verification does** (`verify_chain()` in the code): it walks the whole ledger in
order, and for every row, it:
- Recomputes the hash from that row's own stored fields and `prev_hash`.
- Checks the recomputed hash matches the `hash` that was actually stored.
- Checks that row's `prev_hash` matches the previous row's `hash`.

If someone edits any field of any past row — say, changing a `$100` contribution to
`$1000` — that row's stored `hash` no longer matches what you'd recompute from its
(now-changed) data. Verification immediately flags that exact row. And because every
later row's `prev_hash` was built from the *original* (now-wrong) hash, in a real
attack the tamperer would have to recompute every single hash after the edit too, just
to make the chain look consistent again — which is the "work" a blockchain's integrity
guarantee is actually buying you.

**This is exactly what the "Simulate tampering" button demonstrates**: it directly
`UPDATE`s a row's `amount` in the database without touching its hash — the shortcut an
attacker with raw database access might take — and the next verification catches it
immediately, because the stored hash and the recomputed hash no longer match.

## 4. Payout rotation logic

```python
payee_index = (cycle - 1) % num_members
payee_id = members[payee_index][0]   # members ordered by join_order
```

Cycle 1 pays the member at `join_order = 0`, cycle 2 pays `join_order = 1`, and so on,
wrapping back around with `% num_members` once everyone's had a turn. This fires
automatically the moment the last member contributes for that cycle — no organizer
action needed (`add_contribution()` checks `len(contributed) == len(members)` and calls
`trigger_payout()` if so).

## 5. Trust score

```python
score = 100 * (contributions made in completed cycles) / (number of completed cycles)
```

A member with zero missed contributions sits at 100%. A new circle with no completed
cycles yet defaults everyone to 100% (nothing to judge yet). This is deliberately
simple — a real product might weight recent cycles more heavily, but the PRD's own
guidance is to keep the MVP's logic explainable, not sophisticated.

## 6. Why centralized + hash-chained, not a public blockchain

Worth having ready, since it's the most likely pushback question:

- A public chain (Ethereum, etc.) means every member needs a wallet and either pays gas
  fees or you (the app) subsidizes them — both are real adoption friction for
  non-crypto-native users, which is exactly our target market.
- The hash chain gives the *specific property we actually need* — tamper-evidence and
  independent verifiability — without that onboarding cost.
- It is explicitly **not** claiming to be decentralized. The PRD and deck both say this
  directly: centralized MVP, blockchain-style guarantees, with a stated roadmap item to
  migrate the ledger to an L2 if/when the user base justifies it.

## 7. Should you deploy it to a public URL?

**Short answer: Streamlit Community Cloud, not Vercel.** See the chat reply for the
reasoning — Vercel's serverless model doesn't support what Streamlit needs (a
persistent process holding a live WebSocket connection and local SQLite state), so it
would require rearchitecting the app rather than just deploying it. Streamlit Community
Cloud is built specifically to run apps like this one, for free, straight from a GitHub
repo.
