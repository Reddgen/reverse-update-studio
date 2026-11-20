# How This Started

I go by **Reddgen** online.

I’m not a professional reverse engineer or a security researcher. I’m a
regular person who enjoys tinkering, learning how things work, and following a
question until it becomes something useful. I also write music:
[yelledbox.com](https://yelledbox.com).

For a long time, the kind of deep technical exploration I was curious about
felt out of reach. Life, family and the practical complexity of everyday
responsibilities don’t leave unlimited time for long, uninterrupted study. I
kept reading, observing and taking notes where I could.

New tools changed the economics of learning for me. Modern software and
AI-assisted workflows made it possible to test ideas, build small experiments,
and turn observation into something concrete without needing a lab or a large
team. That is the spirit behind this project: applied curiosity, not authority.

## Why I built it

I watched a lot of project and update videos. The same questions kept coming
back:

- When a program updates, what actually changed in the binary?
- Which old function corresponds to which new one?
- Which behavior is a known library path, and which is something nobody has
  named yet?
- Can I match the update I am being handed against the build I already have?
- What is the handoff between the past build and the recent one — the part I
  was calling a *handshake*?

Most explanations stop at “it updated.” I wanted to follow the handoff.

So I built a tool around that question. It matches past and recent builds using
names, code fingerprints and normalized instructions. It maps what it can to
source. It records known paths in a library. The parts that do not match become
puzzle pieces with stable IDs, so they can be logged, counted and studied later
instead of disappearing.

I didn’t know the proper names for these ideas, and I’m not going to pretend I
did. The closer terms are release diff, binary diff, function matching, pattern
or signature libraries, and novelty detection. I called the handoff a
“handshake” because that is what it felt like; a network handshake is a
different thing. See [docs/CONCEPTS.md](docs/CONCEPTS.md).

I don’t have the whole answer. The tool is a way to ask the question carefully.

Release changes are often hard to see. Two builds look similar from the
outside, but the useful differences are buried in functions, symbols and source
lines. The tool is my attempt to make those changes legible:

- compare two builds;
- show what changed;
- point to the source line;
- trace unknown paths;
- make updates verifiable.

It is a how-to tool. It does not run games, bypass protections, or replace
proper research. It is meant to help people ask better questions about software
they are allowed to study.

I hope it is useful. I hope it saves someone time. I hope it makes a hard subject
a little more approachable. And I hope I can keep learning and building for the
greater good — while being honest about the limits of my time, knowledge and
experience.

If you use it, please use it lawfully, with permission, and with respect for the
people who wrote the software you are studying. See [ETHICS.md](ETHICS.md).

What a time to be alive.
