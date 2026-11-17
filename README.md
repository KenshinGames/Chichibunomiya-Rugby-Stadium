# Chichibunomiya-Rugby-Stadium

秩父宮ラグビー場(東京都港区北青山、1947 年開場)を、Blender 5.3 の Python スクリプトだけで再現する個人作品。

- 今の段階と続け方: [PROGRESS.md](PROGRESS.md)
- 寸法の出どころ(公式・実測・推定): [docs/reference.md](docs/reference.md)
- 計画とファイル構成: [docs/plan.md](docs/plan.md)
- 参考写真との比較: [docs/compare/](docs/compare/)

```
./run.sh build                       # build/chichibu.blend を作る
./run.sh check aerial,broadcast day  # 確認用に描く(out/check/)
```

寸法は [config/dimensions.json](config/dimensions.json) にまとめてあり、形はすべてそこから計算する。
周りの建物・道・木(config/surroundings.json)は © OpenStreetMap contributors(ODbL)のデータから作った。
参考写真は Wikimedia Commons のもの。比較画像(docs/compare/)は元の写真のライセンスに従う(CC BY-SA の写真を含むものは CC BY-SA 4.0)。
