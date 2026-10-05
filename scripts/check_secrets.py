"""Scan tracked files, optional git history/build, without revealing secret content."""

import argparse
import os
import re
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--history", action="store_true")
parser.add_argument("--frontend-build", action="store_true")
args = parser.parse_args()
llm_placeholders = {"EMPTY", "NONE", "NULL", "DUMMY", "PLACEHOLDER"}


def is_secret_value(name, value):
    # These non-credential LLM sentinels also occur as framework identifiers.
    return bool(value) and not (
        name == "LLM_API_KEY" and value.upper() in llm_placeholders
    )


secret_names = {
    "GH_TOKEN",
    "LLM_API_KEY",
    "MYSQL_PASSWORD",
    "DB_PASSWORD",
    "DATABASE_URL",
}
secrets = {
    os.environ[name].encode()
    for name in secret_names
    if is_secret_value(name, os.environ.get(name, ""))
}
for line in (
    (root / ".env").read_text().splitlines() if (root / ".env").exists() else []
):
    match = re.match(r"\s*(?:export\s+)?(\w+)\s*=\s*(.*)", line)
    if match and match[1] in secret_names:
        value = match[2].strip().strip("\"'")
        if is_secret_value(match[1], value):
            secrets.add(value.encode())
pattern = re.compile(rb"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})")
failed = False
checked = 0


def inspect_content(content, label):
    global failed, checked
    checked += 1
    if any(secret in content for secret in secrets) or pattern.search(content):
        failed = True
        print("Secret detected in:", label)


files = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).split(b"\0")
for name in filter(None, files):
    path = root / name.decode()
    if not path.is_file():
        continue
    inspect_content(path.read_bytes(), str(path.relative_to(root)))
    if path.name.startswith(".env") and path.name != ".env.example":
        failed = True
        print("Environment file is tracked:", path.relative_to(root))
if args.history:
    hashes = subprocess.check_output(
        ["git", "rev-list", "--objects", "--all"], cwd=root
    ).splitlines()
    for line in hashes:
        object_id = line.split(b" ", 1)[0].decode()
        kind = subprocess.check_output(
            ["git", "cat-file", "-t", object_id], cwd=root
        ).strip()
        if kind == b"blob":
            inspect_content(
                subprocess.check_output(
                    ["git", "cat-file", "blob", object_id], cwd=root
                ),
                "git history blob " + object_id[:12],
            )
if args.frontend_build:
    for directory in [root / "frontend/.next/static", root / "frontend/.next/server"]:
        for path in directory.rglob("*"):
            if path.is_file():
                inspect_content(path.read_bytes(), str(path.relative_to(root)))
if failed:
    raise SystemExit(1)
print(f"Secret check passed ({checked} files/blobs).")
