# usage: ci_gate.sh <pr> "<squash title>"
# Rebase the PR branch onto main (server-side update), wait for CI on the new head,
# verify the review stamp locally, merge pinned to that head. Heavy gates run in CI.
set -u
n=$1; title=$2
export GH_TOKEN=$(env -u GH_TOKEN gh auth token --hostname github.com --user jttrs); R=jttrs/magic-manager
REQ="pytest web-check e2e extension review-stamp"
base=$(gh api repos/$R/pulls/$n --jq .base.sha); main=$(gh api repos/$R/branches/main --jq .commit.sha)
if [ "$base" != "$main" ]; then
  gh api -X PUT repos/$R/pulls/$n/update-branch -f update_method=rebase >/dev/null 2>&1 \
    || { echo "#$n server rebase failed (conflict?) — rebase the branch by hand"; exit 2; }
  sleep 15
fi
head=$(gh api repos/$R/pulls/$n --jq .head.sha); echo "#$n head ${head:0:7}"
for i in $(seq 90); do
  st=$(gh api "repos/$R/commits/$head/check-runs?per_page=100" --jq '[.check_runs[] | {n:.name,s:.status,c:.conclusion}]')
  pend=0; bad=""
  for c in $REQ; do
    v=$(echo "$st" | jq -r --arg c "$c" '[.[]|select(.n==$c)] | if length==0 then "missing" elif .[0].s!="completed" then "pending" else .[0].c end')
    case $v in success) ;; pending|missing) pend=1;; *) bad="$bad $c=$v";; esac
  done
  [ -n "$bad" ] && { echo "#$n CI failed:$bad"; exit 1; }
  [ $pend = 0 ] && break
  sleep 20
done
[ $pend = 0 ] || { echo "#$n CI timed out"; exit 1; }
echo "#$n CI green: $REQ"
git fetch -q origin
uv run python scripts/pr_review.py check --body-file <(gh api repos/$R/pulls/$n --jq .body) --base origin/main --head "$head" > /tmp/rv.log 2>&1; r=$?; cat /tmp/rv.log
[ $r = 0 ] || { echo "#$n review stamp missing/stale — not merging"; exit 3; }
[ "${DRY:-}" = 1 ] && { echo "#$n ok (dry)"; exit 0; }
gh api -X PUT repos/$R/pulls/$n/merge -f merge_method=squash -f sha="$head" -f commit_title="$title (#$n)" --jq .merged
