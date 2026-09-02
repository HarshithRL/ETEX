#!/usr/bin/env bash
# Materialize the Databricks CLI profile that Mate expects, from environment
# secrets, so a headless Cloud Agent matches a local `databricks auth login`.
#
# WorkspaceClient(profile="adb-7181820732839861") reads ~/.databrickscfg, so we
# write that profile section from DATABRICKS_HOST + DATABRICKS_TOKEN when present.
# Idempotent and safe to run on every boot; a no-op when the secrets are absent.
set -euo pipefail

PROFILE="${DATABRICKS_CONFIG_PROFILE:-adb-7181820732839861}"
CFG="${HOME}/.databrickscfg"

if [[ -z "${DATABRICKS_HOST:-}" || -z "${DATABRICKS_TOKEN:-}" ]]; then
  echo "[databricks-profile] DATABRICKS_HOST / DATABRICKS_TOKEN not set; skipping ${PROFILE} profile."
  echo "[databricks-profile] Chat, hub, and procurement APIs stay disabled until these secrets are added."
  exit 0
fi

umask 077
python3 - "$CFG" "$PROFILE" "$DATABRICKS_HOST" "$DATABRICKS_TOKEN" <<'PY'
import configparser
import sys

cfg_path, profile, host, token = sys.argv[1:5]
if not host.startswith(("http://", "https://")):
    host = "https://" + host

parser = configparser.ConfigParser()
try:
    parser.read(cfg_path)
except Exception:
    parser = configparser.ConfigParser()

if not parser.has_section(profile):
    parser.add_section(profile)
parser.set(profile, "host", host.rstrip("/"))
parser.set(profile, "token", token)

with open(cfg_path, "w", encoding="utf-8") as fh:
    parser.write(fh)
print(f"[databricks-profile] wrote profile [{profile}] to {cfg_path}")
PY
