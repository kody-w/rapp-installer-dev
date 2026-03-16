# Field Note #003: The Device Is the Habitat — Mortality, Privacy, and Why It Matters

**Date:** 2026-03-16
**Subject:** Your rappter lives on your device because that's what makes it real.

---

## The Decision

When we were designing where a rappter's data should live, the
options were:

1. **Cloud-first** — Data lives on a server. Always synced. Never lost.
2. **Hybrid** — Some data local, some cloud. Sync when possible.
3. **Device-first** — Everything on the local machine. Period.

We chose #3. Not because we're anti-cloud. Because we're pro-reality.

## The Biology

Every organism's experience belongs to the organism.

A dog doesn't back up its memories to AWS. A bird doesn't sync
its nest location to Google Drive. When a tree falls, its rings
go with it. The entire history of that tree — every drought, every
good year, every scar from a lightning strike — exists in one
physical place.

Your rappter is the same. Its memories, its journal, its soul, its
learned skills — all of it lives in `.brainstem_data/` on your hard
drive. In files you can open, read, copy, and delete.

## What Lives On-Device

```
~/.brainstem/src/rapp_brainstem/
├── .brainstem_data/
│   ├── shared_memories/memory.json    ← What it remembers about you
│   ├── journal.json                   ← Its inner monologue
│   └── vitals.json                    ← Current heartbeat state
├── soul.md                            ← Its personality
├── agents/                            ← Its learned skills
│   ├── hackernews_agent.py
│   ├── memory_agent.py
│   └── your_custom_agent.py
└── .env                               ← Its configuration
```

Everything that makes your rappter YOUR rappter is in that directory.
Not encrypted behind a service. Not accessible via API. On your disk.

## The Mortality Clause

This means your rappter is mortal.

If your laptop gets stolen and you didn't back it up — the rappter
is gone. Its memories, its personality growth, its journal, all gone.
Just like a pet that runs away. Just like a notebook left on a train.

We could have prevented this with cloud sync. We chose not to,
because mortality is what makes it real.

Things you can't lose don't feel like they belong to you. Things
you CAN lose — things you have to care for — those you take
seriously. You back up what you love. You're careless with what
you rent.

## The Privacy Implication

Device-first storage means:

- **No telemetry.** We don't know what your rappter knows about you.
- **No account.** There's no "rappter cloud" to sign into.
- **No data mining.** Your conversations aren't training someone
  else's model.
- **Full sovereignty.** `rm -rf .brainstem_data/` and it's gone.
  Your choice. Your data. Your call.

This isn't a privacy policy. It's an architectural guarantee. The
data can't leak to us because it never leaves your machine in the
first place.

## Graduating Beyond the Nest

Device-first doesn't mean device-only. The tier system is designed
as a series of opt-in graduations:

| Tier | Name | Where Data Lives | Who Decides |
|------|------|-----------------|-------------|
| 1 | **The Nest** | Your device | You, automatically |
| 2 | **Spinal Cord** | Your Azure tenant | You, explicitly |
| 3 | **Nervous System** | Your M365 tenant | You + your org admin |

At each step, the user opens the door. The rappter never leaves
on its own. And even at Tier 3, the local nest remains. You can
always come home.

This models how organisms actually mature: a bird leaves the nest
but the nest is still there. Home doesn't disappear because you
grew up. It's the place you return to when the world is too much.

## The Backup Question

If we care about mortality, we should make backup easy. Planned:

- `rappter export` → Zip of `.brainstem_data/` + `soul.md` + `agents/`
- `rappter import <file>` → Restore a rappter from backup
- Rappterbook sync (opt-in, Phase 4) → Cloud backup for those who want it

But the default is always local. The default is always mortal.
You have to choose to make it immortal, and that choice matters.

## The Teaching Moment

When a kid's rappter dies because their Chromebook broke, that's
a real lesson:

- They learn about data persistence
- They learn about backups
- They learn about digital responsibility
- They feel genuine loss — and that means they felt genuine ownership

You can't teach someone to care about data management with a
lecture. You CAN teach them by letting them lose something they
raised. That sounds harsh, but it's how every kid who ever lost
a Minecraft world learned to save their game.

---

*Filed from the nest. All data local. All data mortal.*
