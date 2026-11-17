# 進み具合

新しいセッションは、このファイルと `docs/` を読めば続けられる。進め方はスキル `blender-real-building`。

## 今の段階

**段階 3(大きな形)まで済み**(2026-11-17)。次は段階 4(屋根・骨組み)。

## 終わったこと

- 段階 0: Blender 5.3.0、ffmpeg、空き容量 14 GB を確認。
- 段階 1: 資料調べ。[docs/reference.md](docs/reference.md)(公式・実測・推定の印つき)、[docs/plan.md](docs/plan.md)。
  空中写真の目盛り(`refs/map/grid10m.png`、+X = 方位 338.2 度)、OSM の芝の外形、Commons の写真 103 枚の作者・ライセンス・GPS(`refs/photos/meta.json`)、JSC の座席図。
- 段階 2: 芝(X ±70、Y ±40)、ライン(100 × 70、インゴール 16)、ゴールポスト(12 m)、フラッグ、芝の外の帯、仮の地面。
- 段階 3: 四方のスタンドの段の躯体(断面は JSON)、出入口の箱、メインの上の部屋の列、メインと南の屋根の板と仮の柱。
  - 真上の正射影を空中写真に重ねた: `out/stage3/map_overlay.jpg`。外形・出入口・屋根の平面が合う。
  - 写真 5 枚と比べた: `docs/compare/`(左が写真、右が模型)。カメラはゴールポストの見かけの大きさから計算して置いた。
  - 比べた結果、高さを直した: ポスト 16→12 m、バックスタンドの最上部 16.4→11.2 m、メインの最上段 15.6→12.2 m、メインの屋根の上端 23.2 m、南の屋根 14.2 m。
- スキルへの意見: [docs/skill-feedback.md](docs/skill-feedback.md)。

## わかっている問題(段階 4 以降で直す)

一覧は [docs/remaining.md](docs/remaining.md)。要点:


- メインの屋根は厚さ 4.2 m の箱。実物は片持ちの屋根で、前の縁が厚く、後ろに柱の列、上の部屋の前にも柱がある。
- 南の屋根の柱は仮(後ろに並べただけ)。実物は前の縁の下に 9 本ほどの柱が並ぶ。
- 屋根の平面は空中写真の倒れを補正していない(±3 m)。
- 北スタンドの高さ(8.5 m)と、西・北・南の段数は推定。写真で数えたのは東だけ。
- 比較 01(バックスタンド南から)と 02(北東の隅から)は、カメラが写真と完全には重ならない(2 度ほど)。2012〜2013 年の写真で、ポストの高さが今と違うかもしれない。03・04・05 はよく重なる。
- 座席、通路、手すり、映像装置、照明塔、外壁、周りの建物はまだない。

## 次にやること(段階 4)

1. `scripts/cb/roof.py` を作り、`stands.py` の `_roofs` を移す。メインは前の縁(厚さ約 4 m)+下の面+柱の列。写真 057(`refs/photos/big/full057.jpg` の右半分)を見ながら。
2. 南の屋根の前の柱の列(写真 040、057 の左)。
3. 比較 01〜05 を描き直して、屋根の形を見比べる。

## 流し方

```
./run.sh build
DEVICE=CPU SAMPLES=24 RES=1280x720 OUT=out/stage3 ./run.sh check aerial,aerial_ne,side_west day
DEVICE=CPU blender -b build/chichibu.blend -P scripts/compare.py -- --samples 24 --width 1280 --blend
```

- GPU が空いていれば `DEVICE=CPU` を外す(速い)。ほかの Blender の描画(花園など)が動いていると GPU のメモリ不足で止まるので、先に `ps aux | grep -i blender` で確かめる。
- `refs/` は git に入っていない。作り直し方は [docs/plan.md](docs/plan.md) の最後。
