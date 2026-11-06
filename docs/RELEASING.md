# Releasing GlucOSC

How a release is built, the security choices behind it, and the checklist to follow.

## What gets built

| File | Built by | Where |
|---|---|---|
| `GlucOSC-windows-x64.zip` | `packaging/build_windows.ps1` (PyInstaller) | GitHub Actions, `windows-2022` |
| `GlucOSC-x86_64.AppImage` | `packaging/build_appimage.sh` (PyInstaller + appimagetool) | GitHub Actions, `ubuntu-22.04` |
| `GlucOSC-Unity.unitypackage`, `GlucOSC-Unity.zip` | `tools/make_unitypackage.py` (standard library only, reproducible) | GitHub Actions, `ubuntu-24.04` |
| `SHA256SUMS.txt` + signed build provenance | release job | GitHub Actions |

The source code archive is added by GitHub automatically.

## Why it is built this way

Recent attacks (GhostAction, the npm worms, LiteLLM on PyPI, OVHcloud's release binaries swapped on GitHub) mostly worked in these ways:

1. **Stolen maintainer credentials** (tokens taken from a developer's computer, or phished) used to push workflows or replace release files.
2. **Moved tags on third-party actions**, so a workflow pinned to `@v4` suddenly ran different code.
3. **Freshly published malicious package versions** pulled in automatically by `pip install` or `npm install`.
4. **Secrets in CI** being read and sent out.

What this repo does about each:

| Risk | Defence here |
|---|---|
| Moved action tags | Every `uses:` is pinned to a full 40-character commit hash. Only GitHub's own actions are used; the release is created with the preinstalled `gh` tool, not a third-party action. Dependabot proposes updates only after a release is 14 days old. |
| New malicious package versions | `packaging/requirements-build.txt` pins every Python package (including the ones PySide6 and PyInstaller pull in) to an exact version **and** SHA-256 hash. `lock_deps.py` checks the upload date of the exact file it locks and skips anything younger than 14 days (a version you pin by hand with `==` only gets a warning). The builds install with `--require-hashes --only-binary=:all: --no-deps`, so nothing else can sneak in and no package runs install scripts. |
| Unpinned downloads | appimagetool and the AppImage runtime are fixed to one release each and checked against a recorded hash. The build stops if either does not match. |
| Secrets in CI | There are none. The build jobs get a read-only token. Only the final job gets write access, and it uses it only to create a **draft** release. |
| Replaced release files | Draft first; you publish by hand. **Immutable releases** (below) stop files from being swapped after publishing. Users can check the signed provenance with `gh attestation verify ... --signer-workflow ... --source-ref refs/tags/vX.Y.Z`, which only accepts files built by `release.yml` from a release tag, not by some other workflow or branch. |
| Account takeover | Settings below: passkey or security key, no long-lived tokens, protected tags, immutable releases. |

**Be clear about the limits.** Someone holding your login or a token with `workflow` scope can do what you can: push a new workflow to another branch that asks for write access (it would skip the `release` approval gate, which only guards this workflow), create releases, or attest their own files. Signing and checksums can't stop someone who *is* you to GitHub. That is why account security matters most, and why immutable releases plus the strict `gh attestation verify` command are required steps, not extras. None of this protects against a compromise of GitHub itself, PyPI files that were already malicious 14+ days before you locked them, or malware on the computer you push from. Keep your OS and browser updated, and don't run random scripts on that machine.

## One-time setup

### Your GitHub account
- Sign in with a **passkey or hardware security key** (Settings > Password and authentication). Remove SMS as a 2FA method if you can.
- Settings > Developer settings: delete personal access tokens you don't use. If you need one, make it **fine-grained**, limited to this repository, with an expiry date.
- Settings > Applications: revoke OAuth apps and GitHub Apps you don't recognise.
- Settings > Emails: tick **Keep my email addresses private** and **Block command line pushes that expose my email**. Use the `...@users.noreply.github.com` address shown there for `git config user.email`.
- Infostealer malware targets saved tokens (including the `gh` CLI's login). Log `gh` out (`gh auth logout`) on machines where you don't need it.

### Repository settings
- **Settings > Actions > General**
  - Actions permissions: **Allow reploidsham, and select non-reploidsham, actions and reusable workflows**, then tick **Allow actions created by GitHub** only.
  - Tick **Require actions to be pinned to a full-length commit SHA** (if your settings page shows it).
  - Fork pull request workflows: **Require approval for all external contributors**.
  - Workflow permissions: **Read repository contents and packages permissions**; untick **Allow GitHub Actions to create and approve pull requests**.
- **Settings > Environments > New environment `release`**: add yourself under **Required reviewers**, and under deployment branches and tags allow only tags matching `v*`. The release job then waits for your click. (This guards this workflow only; see the limits above.)
- **Settings > Rules > Rulesets** (required)
  - Branch ruleset for `main`: block force pushes and deletion.
  - Tag ruleset for `v*`: restrict creations, updates and deletions to yourself (add yourself to the bypass list), so released tags can't be moved.
- **Immutable releases** (required): turn on release immutability in the repository settings (search the Settings page for "immutable"). Once a release is published, its files and tag can no longer be changed.
- **Settings > Code security**: turn on Dependabot alerts, secret scanning with push protection, and **Private vulnerability reporting**.

## Locking the Python build tools

Run on your own computer, not in CI, so the lock is made somewhere you control:

```
python3 packaging/lock_deps.py          # newest versions that are at least 14 days old
git diff packaging/requirements-build.txt
git add packaging/requirements-build.txt && git commit -m "Lock build tools"
```

Needs Python 3.9+ with pip 22.2+ and access to pypi.org. It locks for Python 3.12 (CI uses exactly 3.12.15) on Linux x86_64 and Windows x64 together. If it says pip could not find wheels for a platform, the newest release probably dropped that platform; pin an older version with `==` in `packaging/requirements-build.in`. Linux and Windows need different extra packages, and pip normally only sees the ones for the machine it runs on, so the script works out the Windows-only ones itself. Re-run it when you want newer tools, not for every release.

## Quick local test build (Linux)

`bash build-test-appimage.sh` builds the AppImage, runs `--self-check` on the finished file (languages, rotate mode, `BG_Words`, Qt bundled), writes `dist/BUILD-INFO.txt`, and prints `NEWEST BUILD OK` with the file to use. Anything else it prints is the reason to stop. It is for testing only; releases come from the GitHub workflow.

## Test build (no release)

Actions tab > **release** > **Run workflow**. This builds everything and keeps the files as workflow artifacts for 7 days, without making a release. Download the Windows zip and try it on a Windows PC before your first real release.

## Release checklist

1. Unity side checked in VRChat with the files from this commit (dot, plain words, language dial, rotate mode).
2. Windows zip from a test build checked on a real Windows PC, and the AppImage on a clean Linux install other than your own (start, connect, values arrive in VRChat).
3. `CHANGELOG.md` updated. Screenshot placeholders in `README.md` replaced (or left as text).
4. No tokens, secrets, phone IPs or personal data in any file or screenshot (`git grep -n -i -E "secret|token|192\.168"` and look at what it finds).
5. Tag and push:
   ```
   git tag -a v0.1.0 -m "GlucOSC 0.1.0"
   git push origin v0.1.0
   ```
6. Approve the `release` job when it asks. A **draft** release appears under Releases.
7. Download every file from the draft, run `sha256sum -c SHA256SUMS.txt` and the `gh attestation verify` command from the release notes, and try the Windows and Linux apps once more.
8. Press **Publish release**.

## Updating a pinned build tool

- **GitHub Actions**: accept Dependabot's pull request, or change the hash and the `# vX.Y.Z` comment by hand. Get the hash with `git ls-remote --tags https://github.com/actions/checkout`, and use the line ending in `^{}` when there is one (that is the commit, not the tag object).
- **appimagetool / AppImage runtime**: change the version in `packaging/build_appimage.sh`, download the file yourself, run `sha256sum` on it, and paste the new hash.
- **Python packages**: `python3 packaging/lock_deps.py`.

## Hosting elsewhere

The repository works on any Git host; only `.github/` is GitHub-specific.

- **Mirror on Codeberg** (non-profit, Forgejo): push the same repository there as a second copy and link it in the README. If one account is ever taken over, people can compare the two.
- **Building without GitHub Actions**: run `packaging/build_appimage.sh` on Linux and `pwsh packaging\build_windows.ps1` on a Windows PC, run `sha256sum` over the files, and upload them by hand. You lose the signed provenance but depend on fewer services.
