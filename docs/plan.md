# 計画

秩父宮ラグビー場を Blender 5.3 の Python スクリプトだけで再現する。画面は開かず `blender -b` で作り、描いた画像を参考写真と見比べて直す。
進め方はスキル `blender-real-building`(東大阪市花園ラグビー場で作ったもの)に従う。

## 段階

| 段階 | やること | 状態 |
|---|---|---|
| 0 環境 | Blender 5.3.0、ffmpeg、空き容量 14 GB(93% 使用) | 済み |
| 1 資料と計画 | 公式の数字、空中写真の目盛り、OSM、参考写真、座標の決まり | 済み([reference.md](reference.md)) |
| 2 地面・競技面 | 芝、ライン、ゴールポスト、フラッグ、芝の外の帯 | 済み |
| 3 大きな形 | 四方のスタンドの段の躯体、メインの上の部屋 | 済み(真上の重ね合わせと写真 5 枚との比較) |
| 4 屋根・骨組み | メインの片持ち屋根(柱、梁、前の縁)、南の屋根と柱の列 | 済み(1 回目) |
| 5 細部 | 座席(青・黄)、縦通路、出入口の箱、手すり、上の部屋の窓 | 済み(1 回目)。看板・ゲート番号はまだ |
| 6 設備 | 映像装置、照明塔 4 基 | 済み(1 回目)。夜の光と看板はまだ |
| 7 外側と周り | 周りの建物・道・運動場・木(OSM)、神宮球場 | 1 回目。スタジアムの外壁と正面入場口はまだ |
| 8 質感と光 | 昼(午後の西日)、夜 | |
| 9 見比べ | 写真と並べて違いを大きい順に直す | 段階 3〜7 の途中で 5 枚と比べている |

## ファイル

```
config/dimensions.json   寸法(ここだけ直せば形が追従する)。整えるときは python3 tools/json_fmt.py config/dimensions.json
config/surroundings.json 周りの建物・道・木(OSM から tools/osm_surroundings.py で作る。© OpenStreetMap contributors)
scripts/build.py         最初から全部作って build/chichibu.blend に保存
scripts/render.py        決まった角度で描く(run.sh check)
scripts/compare.py       参考写真と同じ角度で描いて並べる(docs/compare/)。--blend で半透明の重ね絵(カメラ合わせ用)
scripts/orbit.py         一周の動画(段階 8 以降)
scripts/cb/              部品。pitch(2)、stands(3)、roof(4)、seats・details(5)、screen・lights(6)、exterior(7)
                         layout.py が断面を段の一覧に直す。materials.py に色
tools/osm_measure.py     OSM の外形をこの座標に直して表示する
tools/osm_surroundings.py refs/osm/*.json → config/surroundings.json
refs/                    空中写真・参考写真・公式の座席図・OSM の生データ(git に入れない)
out/                     描いた画像(git に入れない)
```

ひな形(花園)の `roof.py`・`seats.py`・`details.py`・`lights.py` は、仕組みを残して秩父宮の寸法と形に書き直した。
`screen.py`・`exterior.py` は秩父宮用に新しく書いた(周りは花園の乱数の家並みではなく OSM の外形から)。`signage.py`(看板)は前の壁の看板だけ(社名は架空)。
`build.py` はないファイルを飛ばすので、足せばそのまま組み込まれる。

## 自分で決めたこと

- **作る時期**: 今の秩父宮(2016〜2018 年ごろの姿)。新しい秩父宮ではない。
- **座標**: 原点は芝の中心、+X は北北西(方位 338.2 度)、+Y は西。地面は平ら(Z = 0)。
- **スタンドの平面の端は折れ線**で書く(`u0` / `u1` を `[[d, u], ...]` にした)。秩父宮はバックスタンドの四隅もメインの両翼も角を落とした形で、ひな形の直線(u = a + b·d)では書けなかった。
- **屋根は段階 3 では板だけ**にし、段階 4 で `roof.py` に移して柱と梁を作った。
- **周りは OSM の外形から**作る。北青山は家並みではなくビル街なので、花園の乱数の家並みより実際の外形のほうが写真と合う。
  OSM の生データは `refs/` に置き、模型の座標に直した `config/surroundings.json` だけを git に入れる(build が refs/ に頼らないように。ODbL なので出どころを書く)。
- **周りは今の姿、スタジアムは 2016〜2018 年の姿**。OSM は今の建物しかないため。
- **物差しは規則で決まった寸法だけ**(クロスバー 3 m、ポスト間隔 5.6 m)。ポストの高さは写真から測った(12 m)。
- **GPU が使えないときは CPU で描く**: `DEVICE=CPU ./run.sh check ...`。花園の仕上げの描画が GPU を使っていると、こちらはメモリ不足で止まる。
- 企業のロゴや広告は依頼がなければ架空にする(段階 6)。施設名は再現してよい。

## 流し方

```
./run.sh build                                          # 1 秒以下
DEVICE=CPU SAMPLES=24 RES=1280x720 OUT=out/stage3 ./run.sh check aerial,side_west day
DEVICE=CPU RES=1300x1300 SAMPLES=12 OUT=out/stage3 ./run.sh check map day
~/.claude/skills/blender-real-building/scripts/overlay_map.sh out/stage3/map_day.jpg refs/map/grid10m.png out/stage3/map_overlay.jpg
DEVICE=CPU blender -b build/chichibu.blend -P scripts/compare.py -- --samples 24 --width 1280 --blend
```

OSM を取り直すとき(Overpass は重い問い合わせを落とすので種類ごとに分ける):

```
C="around:650,35.672651,139.718350"
curl -s --data-urlencode "data=[out:json][timeout:90];(way($C)[building];relation($C)[building];);out geom;" https://maps.mail.ru/osm/tools/overpass/api/interpreter -o refs/osm/buildings.json
# highways は way($C)[highway~"^(primary|secondary|...)$"]、areas は leisure・landuse・natural・natural=tree の node
python3 tools/osm_surroundings.py
```

`refs/` は git に入らないので、新しい環境では作り直す:

```
python3 ~/.claude/skills/blender-real-building/scripts/aerial_grid.py --lat 35.672651 --lon 139.718350 --azimuth 338.2 --half 130 --out refs/map
```

参考写真は [reference.md](reference.md) の表のファイルを Commons から `refs/commons/` に落とす(ファイル名の空白は `_`)。
