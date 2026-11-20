# Security Policy

## Reporting

Do not open a public issue for a security problem. Use GitHub's private
vulnerability reporting for this repository.

Include:

- affected version;
- steps to reproduce;
- impact;
- a minimal proof of concept if safe to share.

## Scope

In scope:

- path traversal;
- arbitrary file read/write;
- PIN bypass;
- update signature/encryption bypass;
- command injection;
- archive/upload resource exhaustion.

Out of scope:

- running untrusted binaries/ROMs;
- bypassing Windows SmartScreen by disabling system protection;
- vulnerabilities in third-party tools that are not used by this app.

## Model

The Studio is local-first. It binds to `127.0.0.1` by default. LAN mode requires
a PIN. It does not sandbox analysed binaries and does not execute them.
