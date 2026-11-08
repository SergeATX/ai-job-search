#!/bin/sh
# Install PII hooks (pre-commit, commit-msg, pre-push) into a repo. Usage: install-hooks.sh [repo-dir]
# Existing hooks are kept and chained (saved as <hook>.pre-pii, or linked from core.hooksPath).
set -e
cd "${1:-.}"
root="$(git rev-parse --show-toplevel)"; cd "$root"
hooks="$(git rev-parse --git-path hooks)"; hooks="$root/${hooks#$root/}"
[ -d "$root/.git/hooks" ] && hooks="$root/.git/hooks"
cfg="$(git config --local core.hooksPath || true)"
for h in pre-commit commit-msg pre-push; do
  f="$hooks/$h"
  if [ -e "$f" ] && ! grep -q "pii-scan-hook" "$f"; then mv "$f" "$f.pre-pii"; fi
  if [ ! -e "$f.pre-pii" ] && [ -n "$cfg" ] && [ -x "$root/$cfg/$h" ]; then
    ln -s "../../$cfg/$h" "$f.pre-pii"
  fi
  case $h in
    pre-commit) scan='python3 "$root/tools/pii_scan.py" --staged || exit 1' ;;
    commit-msg) scan='python3 "$root/tools/pii_scan.py" --msg "$1" || exit 1' ;;
    pre-push)   scan='python3 "$root/tools/pii_scan.py" --push-stdin <<EOT || exit 1
$input
EOT' ;;
  esac
  {
    echo '#!/bin/sh'
    echo '# pii-scan-hook'
    echo 'root="$(git rev-parse --show-toplevel)"'
    [ "$h" = pre-push ] && echo 'input="$(cat)"'
    echo "$scan"
    echo "chain=\"\$(dirname \"\$0\")/$h.pre-pii\""
    if [ "$h" = pre-push ]; then echo '[ -x "$chain" ] && { printf "%s\n" "$input" | "$chain" "$@" || exit 1; }'
    else echo '[ -x "$chain" ] && { "$chain" "$@" || exit 1; }'; fi
    echo 'exit 0'
  } > "$f"
  chmod +x "$f"
done
[ -n "$cfg" ] && git config --local --unset core.hooksPath
echo "pii hooks installed in $root"
