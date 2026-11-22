# CircleFi — Presentation & Demo Script

A suggested run of show for presenting to the class and professor. Total ~12–15 minutes
(adjust to your actual time slot) + Q&A. Assumes the 4-person team split already on the
Team slide — swap speakers/order as your group prefers.

## Before you walk in

- [ ] Close every other app/notification that could pop up during screen share.
- [ ] Open a terminal, `cd` into the project folder, but **don't** run Streamlit yet.
- [ ] Open the slide deck in one browser tab, keep it ready.
- [ ] Delete `circlefi.db` if it exists, so you start from zero (`rm circlefi.db`). This
      guarantees the "seed demo circle" button is there waiting, instead of showing old
      test data.
- [ ] Have a backup: a few screenshots of the app (Overview, Ledger after tampering
      detection, Dashboard) in case live demo or wifi fails. Nobody will mind — most
      pitches keep a backup slide "just in case."

## Run of show

| # | Slide / Screen | Who talks | What to say / do |
|---|---|---|---|
| 1 | Cover | Whoever opens | Introduce the team and the one-line pitch: *"CircleFi digitizes rotating savings circles — the ones millions of people already run informally — and makes them provably tamper-proof."* |
| 2 | Problem & Market Need | Speaker 1 | Walk through the problem/who/why-now cards. Ground it in something relatable: *"Think of a group chat where four friends each put in $100 a month and one person gets the pot. Now imagine someone says they paid and didn't — there's no record."* |
| 3 | Solution | Speaker 1 or 2 | Explain the concept, then the architecture choice slide. This is the one the professor will likely push on — be ready to explain **why centralized + hash-chain, not a public blockchain** (wallet friction, gas fees, onboarding non-crypto users). |
| 4 | PRD Summary | Speaker 2 | Quickly list the 5 features and tech stack. Don't over-explain — this is a checklist slide, move fast. |
| 5 | Technology & Demo | Speaker 2 → hand off | Explain the hash-chain diagram in ~30 seconds: each block stores the previous block's hash, so editing any past record breaks every hash after it. Then say "let's see it live" and switch to the browser. |
| — | **Live demo (switch to the running Streamlit app)** | Speaker 3 (or whoever is most comfortable driving) | See the exact click-by-click flow below. |
| 6 | Business & Revenue Model | Speaker 3 or 4 | Payout fee, insurance add-on, B2B credit-union licensing. Keep it to the "how do we make money without taxing people's savings" framing. |
| 7 | Competition & Differentiation | Speaker 4 | Point at the table: notebook apps have no proof, DeFi apps have too much friction, we're the middle ground. |
| 8 | Team & Roadmap | Speaker 4 | Quick intros + the milestone table. |
| 9 | Thank you / Q&A | Everyone | Open the floor. |

## The live demo, click by click

Run this exactly once before class so you know the timing — it takes about 90 seconds.

1. **Terminal:** `streamlit run app.py` → it opens in your browser automatically.
2. **Overview page:** point out the empty stats (0 circles), then click **"⚡ Seed sample
   demo circle"**. Say: *"This loads a circle with 4 members and 2 cycles already
   completed, so we don't have to click through setup live."*
3. Click **Join & Contribute** in the sidebar. Point at the progress bar (0/4 paid).
4. Click **Submit contribution** three times (it defaults to the next unpaid member each
   time) — narrate: *"Aadhithya pays... Samarth pays... Nidhi pays..."*
5. Click **Submit contribution** a 4th time for the last member (Naman) — the payout
   fires automatically and you'll see 🎈 balloons. Say: *"Once everyone's paid in, the
   payout is automatic — no organizer has to manually send money."*
6. Click **Ledger & Verification**. Scroll the table briefly, then click
   **"✅ Verify chain integrity"** — it should say **verified, no tampering detected**.
7. Expand **"⚠️ Simulate tampering"**, click **"Tamper with the first ledger entry's
   amount"**. Say: *"Now let's pretend someone edited the database directly to fake an
   amount."*
8. Click **"✅ Verify chain integrity"** again — it will say **TAMPERING DETECTED** and
   name the broken entry. This is the moment to pause and let it land: *"This is the
   whole point of the hash chain — nobody, not even someone with direct database access,
   can quietly edit a past record."*
9. Click **Trust & Dashboard** — show the green trust-score bars and the pot-growth
   chart. Say: *"And because everything's logged, we get a dashboard for free — who's
   reliable, and how the pot has grown."*

That's the whole demo. Don't linger on Create Circle unless asked — it's self-explanatory
and not worth live-demo time.

## Likely questions from the professor, and how to answer

- **"Why isn't this actually on a blockchain?"** — Onboarding friction: our users don't
  have wallets or want to pay gas fees. The hash chain gives the same tamper-evidence
  property without that barrier. Roadmap item: migrate to an L2 once there's demand.
- **"What stops the organizer from just editing the SQLite file directly, like your demo
  showed?"** — They can edit it, but they can't make it pass verification without also
  recomputing every hash after the edited entry, which requires rewriting the whole
  chain — and anyone with the "before" ledger (or any member's own copy/export) would
  immediately see the mismatch.
- **"What happens if someone never pays?"** — Covered in the PRD's Risks & Mitigations:
  trust score drops, and the optional insurance add-on is designed exactly for this.
- **"How is this different from Esusu/Oraan/existing ROSCA apps?"** — See the
  Competition slide: those digitize bookkeeping but you still have to trust their
  database. We added independent, cryptographic verification on top.
- **"Is this really decentralized?"** — No, and we say so directly: it's a centralized
  MVP with blockchain-style integrity guarantees, with a stated path to a real L2 later.
  Don't oversell it — the honesty here is a strength, not a weakness.

## Timing tip

If you're short on time, cut the Competition slide narration to one sentence and let the
table speak for itself — the live demo is the part worth protecting.
