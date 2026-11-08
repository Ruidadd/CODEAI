# CODEAI

Trial repository for vibe coding.

## Skills

### cinecode (project skill)

`.claude/skills/cinecode/` holds a vendored copy of the **cinecode** skill: it makes a short film, animation, ad or music video entirely with code (three.js + ffmpeg) and ends in an MP4.

- **Use it** whenever the user asks for a short film, animation, ad, product/promo video, music video, explainer, or says "cinecode" (any language). Read `.claude/skills/cinecode/SKILL.md` and follow it; it starts with two questions (mode and purpose).
- **Make films in a separate, empty folder**, never inside the skill folder itself.
- **Needs** Node 22+, Python 3.9+ and ffmpeg/ffprobe on PATH. Scripts are dependency-free.
- **Source:** https://github.com/sarpstar/cinecode (MIT, Sarp Yıldız). Pinned to upstream commit `67f9807112b97ae253d4a5f0eccaccc46c3b2633` (2026-11-03). The `docs/media/` gallery images and the upstream `.github/` CI were left out of the copy; everything else is verbatim.
- **Update:** re-clone upstream and copy it over `.claude/skills/cinecode/` with the same exclusions, then bump the pinned commit here. Do not also install it under `~/.claude/skills/cinecode`; the kit should exist in one place only so the agent never sees two copies.
