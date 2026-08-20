# How the hub deploys

Two lanes, both building the same artifact: `python3 tools/build_site.py` → `site/`.

## Production — GitHub Pages

`.github/workflows/pages.yml` runs on every push to `main`: validate (`--check`), build, deploy to GitHub Pages. Enable once under Settings → Pages → Source: "GitHub Actions".

## Previews — Cloudflare Pages (Git integration)

The repo is connected to a Cloudflare Pages project from the Cloudflare dashboard (Workers & Pages → the project). Cloudflare builds every push itself:

- **Build command**: `python3 tools/build_site.py`
- **Build output directory**: `site`
- **Production branch**: `main`

Every push to a PR branch gets its own immutable preview URL (`https://<hash>.<project>.pages.dev`) plus a branch alias, posted by Cloudflare as a commit status on the PR. Pushes to `main` update the project's production URL.

## Fallback — CI-driven preview

`.github/workflows/preview.yml` can deploy previews from GitHub Actions instead (useful if the Git integration is ever disconnected). It needs two repository secrets — `CLOUDFLARE_API_TOKEN` (Account → Cloudflare Pages → Edit) and `CLOUDFLARE_ACCOUNT_ID` — and skips cleanly while they are absent, so it is safe to leave in place alongside the Git integration.

## Why deploys don't run from the Claude Code container

The session container's egress policy blocks `api.cloudflare.com` and `*.pages.dev` (verified 403 at the proxy), so all deploying happens on GitHub's or Cloudflare's infrastructure; the container only pushes commits.
