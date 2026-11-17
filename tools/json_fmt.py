"""config/dimensions.json を読みやすく整える(辞書は字下げ、配列は 1 行)。

使い方: python3 tools/json_fmt.py config/dimensions.json
"""
import collections
import json
import sys


def dump(o, ind=0):
    sp = "  " * ind
    if isinstance(o, dict):
        if not o:
            return "{}"
        items = []
        for k, v in o.items():
            items.append("%s  %s: %s" % (sp, json.dumps(k, ensure_ascii=False), dump(v, ind + 1)))
        return "{\n" + ",\n".join(items) + "\n" + sp + "}"
    return json.dumps(o, ensure_ascii=False)


p = sys.argv[1]
cfg = json.load(open(p), object_pairs_hook=collections.OrderedDict)
s = dump(cfg) + "\n"
assert json.loads(s) == json.loads(json.dumps(cfg))
open(p, "w").write(s)
print("整えました:", p, len(s.splitlines()), "行")
