#!/usr/bin/env bash
# Downloads House roll-call XML for the 119th Congress (2025 and 2026) from the House Clerk.
# Skips files already downloaded; stops a year after 3 missing roll numbers in a row.
# Files go to the shared, committed folder data/rollcalls/house/119 (same for every member), not a member folder.
cd "$(dirname "$0")/.." || exit 1
OUT=data/rollcalls/house/119
mkdir -p $OUT
for year in 2025 2026; do
  miss=0; n=1
  while (( miss < 3 )); do
    f=$(printf "$OUT/%s-roll%03d.xml" $year $n)
    if [[ ! -s $f ]]; then
      code=$(curl -s -A "Mozilla/5.0" -o "$f.tmp" -w "%{http_code}" "https://clerk.house.gov/evs/$year/roll$(printf %03d $n).xml")
      if [[ $code == 200 ]] && grep -q "<rollcall-vote" "$f.tmp"; then
        mv "$f.tmp" "$f"; miss=0
      else
        rm -f "$f.tmp"; miss=$((miss+1))
      fi
      sleep 0.25
    fi
    n=$((n+1))
  done
  echo "$year: $(ls $OUT/$year-roll*.xml 2>/dev/null | wc -l | tr -d ' ') roll calls"
done
