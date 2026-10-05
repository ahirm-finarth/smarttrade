"""Check staged/tracked files without printing secret values or matching content."""
import re
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
secrets = []
for line in (root / ".env").read_text().splitlines() if (root / ".env").exists() else []:
    match = re.match(r"\s*(?:export\s+)?(\w+)\s*=\s*(.*)", line)
    if match and any(key in match[1] for key in ("TOKEN", "PASSWORD", "API_KEY", "DATABASE_URL")):
        value = match[2].strip().strip("\"'")
        if value:
            secrets.append(value.encode())
files = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).split(b"\0")
failed = False
for name in filter(None, files):
    path = root / name.decode()
    if not path.is_file():
        continue
    content = path.read_bytes()
    if any(secret in content for secret in secrets) or re.search(rb"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})", content):
        failed = True
        print("Secret detected in tracked file:", path.relative_to(root))
    if path.name.startswith(".env") and path.name != ".env.example":
        failed = True
        print("Environment file is tracked:", path.relative_to(root))
if failed:
    raise SystemExit(1)
print("Secret check passed.")
