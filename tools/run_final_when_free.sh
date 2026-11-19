#!/bin/sh
# 仕上げ(4K 静止画 5 角度 × 昼夜 → out/final/、一周の動画 → out/chichibu_orbit.mp4)を、
# ほかの Blender(花園など)が GPU を使い終わるのを待ってから流す。止まったら同じコマンドを流し直す(動画は続きから)。
#   caffeinate -i tools/run_final_when_free.sh > out/final_run.log 2>&1 &
cd "$(dirname "$0")/.."
wait_free() {
  n=0
  while [ $n -lt 2 ]; do
    if pgrep -f "Blender.*\.blend" | xargs -I{} ps -o command= -p {} 2>/dev/null | grep -v chichibu.blend | grep -q blend; then
      n=0; echo "[final] ほかの Blender が動いているので待つ $(date +%H:%M)"; sleep 120
    else
      n=$((n + 1)); sleep 30
    fi
  done
}
wait_free
echo "[final] 静止画を始める $(date +%H:%M)"
./run.sh stills
c=$(ls out/final/*.png 2>/dev/null | wc -l)
if [ "$c" -lt 10 ]; then echo "[final] 静止画が $c 枚しかない。動画は始めない"; exit 1; fi
wait_free
echo "[final] 動画を始める $(date +%H:%M)"
./run.sh video
ls out/chichibu_orbit.mp4 && echo "[final] 終わり $(date +%H:%M)"
