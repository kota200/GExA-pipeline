import pandas as pd
import re
import collections
import difflib
import itertools
import sys

print("第一引数はinputファイル、第二引数はoutputファイルパス")
path = sys.argv[1]  # 使うパスに合わせて変更
df = pd.read_csv(path, index_col=0)

meta_cols = list(df.columns[:9])  # 1〜9列目
cols_clean = ["treatment"]
col_line = "cultivar"
col_temp = "temperature"

def norm_key(s: str) -> str:
    """表記ゆれ検出用：小文字化＋区切り除去"""
    s = str(s).strip().casefold()
    s = re.sub(r"[\s_\-\/]+", "", s)
    s = re.sub(r"[^\w]", "", s)
    return s

def report_variants(df, col):
    vals = df[col].dropna().astype(str)
    groups = collections.defaultdict(set)
    for v in vals:
        groups[norm_key(v)].add(v)
    return {k: sorted(vs) for k, vs in groups.items() if len(vs) > 1}

def to_lower_snake_stage(x):
    x = to_lower_snake(x)
    if pd.isna(x):
        return x
    return str(x).lower()   # ここで stage だけ小文字化


# --- 1) まず「表記ゆれ候補」を列ごとに一覧化（確認用） ---
for c in ["treatment", "tissue", "stage", "cultivar", "temperature"]:
    v = report_variants(df, c)
    if v:
        print(f"\n[{c}] variants:")
        for k, forms in v.items():
            print(" ", forms)

# --- 2) 安全な正規化（lower_snake_case / ℃除去） ---
def to_lower_snake(x):
    if pd.isna(x):
        return x
    s = str(x).strip().replace("℃", "")
    s = re.sub(r"[\/\s]+", "_", s)
    s = re.sub(r"(-)+", r"\1", s)   # ---- -> -
    s = re.sub(r"(_)+", r"\1", s)   # ____ -> _
    s = re.sub(r"__+", "_", s)
    return s.strip("_")

def clean_temperature(x):
    if pd.isna(x):
        return x
    m = re.search(r"(\d+(?:\.\d+)?)", str(x))
    return m.group(1) if m else str(x).strip()

out = df.copy()

# tissue/stage側の明らかな単複・typoも辞書で（必要に応じて）
out["stage"] = out["stage"].replace({"missing":"","NA":"", "not_applicable":"", "the_rice_seedling_stage":"seedling", "seeding":"seedling", "flag_leaf":"flag_leaf_stage"})
out["treatment"] = out["treatment"].replace({"seed":"NA", "flower":"NA","seedling":"NA","stem":"NA","leaf":"NA","root":"NA"})
out["cultivar"] = out["cultivar"].replace({"Nip":"Nipponbare", "not_collected":"NA", "Wild_type__Nipponbare":"Nipponbare", "missing":"NA"})
out["temperature"]= out["temperature"].replace({"":"NA"})
out["tissue"] = out["tissue"].replace({"NA":"","na":"", "Flag_leaves":"flag_leaf","rice_leaf_tissues":"leaf","Seeds":"seed","anthers":"anther"})
out["treatment"] = out["treatment"].replace(r"_biological_replicate_[0-9]+$","",regex=True)
out["treatment"] = out["treatment"].replace(r"_replicate_[0-9]+$","",regex=True)
for c in cols_clean:
    out[c] = out[c].map(to_lower_snake)

out["stage"] = out["stage"].map(to_lower_snake_stage)
out["tissue"] = out["tissue"].map(to_lower_snake_stage)




out[col_temp] = out[col_temp].map(clean_temperature)

#空欄を "NA" にする（メタデータ列だけ：1〜9列目） ---
# 空文字や空白だけのセルを欠損扱いにしてから "NA" に統一
out[meta_cols] = (
    out[meta_cols]
    .replace(r"^\s*$", pd.NA, regex=True)
    .fillna("NA")
)

# --- 0b) CSVファイル上の 4〜7列目の "_" を " " にする（index_col=0 を考慮） ---
cols_4_7 = list(out.columns[2:6])  # 0-indexで [2,3,4,5]
out[cols_4_7] = (
    out[cols_4_7]
    .astype("string")
    .apply(lambda s: s.str.replace("_", " ", regex=False))
)

# --- code列が Foxtail_millet / Proso_millet / Switchgrass を含む行を除外 ---
# "_" と " " の揺れも拾う（Foxtail_millet / Foxtail millet どちらもOK）


code_col = "code" if "code" in out.columns else out.columns[7]  # 念のための保険





# --- 出力 ---
out_path = sys.argv[2]
out.to_csv(out_path)
print("\nSaved:", out_path)
