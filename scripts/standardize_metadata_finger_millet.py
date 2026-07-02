import pandas as pd
import re
import collections
import difflib
import itertools
import sys

path = sys.argv[1]  # 使うパスに合わせて変更
df = pd.read_csv(path, index_col=0)

meta_cols = list(df.columns[:9])  # 1〜10列目
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
    s = re.sub(r"[_\-]+", "_", s)
    s = re.sub(r"__+", "_", s)
    return s.strip("_")

def clean_temperature(x):
    if pd.isna(x):
        return x
    m = re.search(r"(\d+(?:\.\d+)?)", str(x))
    return m.group(1) if m else str(x).strip()

out = df.copy()

# tissue/stage側の明らかな単複・typoも辞書で（必要に応じて）
out["stage"] = out["stage"].replace({"not_collected":"NA","seedling":"seedling_stage", "Seedling":"seedling_stage", "15_days_old_leaves":"15_days"})
out["treatment"] = out["treatment"].replace({"":"NA","not_collected":"NA"})
out["cultivar"] = out["cultivar"].replace({"":"NA","missing":"NA"})
out["temperature"]= out["temperature"].replace({"":"NA"})
for c in cols_clean:
    out[c] = out[c].map(to_lower_snake)

out["stage"] = out["stage"].map(to_lower_snake_stage)
out["tissue"] = out["tissue"].map(to_lower_snake_stage)
out["stage"] = out["stage"].replace({"na":"NA"})
out["tissue"] = out["tissue"].replace({"na":"NA"})

out["tissue"] = out["tissue"].replace({"leaves":"leaf", "":"NA", "plant_seedlings":"seedling","total_seedlings":"seedling","whole_seedling":"seedling"})
out["stage"] = out["stage"].replace({"seedling": "seedling_stage"})

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



# --- 0c) CSVファイル上の10列目だけ "_" を削除し、";" を "; " に統一 ---
# ※ index_col=0 のため、DataFrameの10列目（index除く）= out.columns[9]
if out.shape[1] >= 10:
    col10 = out.columns[8]

    def _clean_col10(v):
        if pd.isna(v):
            return v
        if not isinstance(v, str):   # 数値列なら型を壊さない
            return v
        v = v.replace("_", " ")
        v = re.sub(r";\s*", "; ", v)  # ";", ";  ", ";    " などを全部 "; " に
        return v

    out[col10] = out[col10].map(_clean_col10)

# index_col=0 で「一列目」が index として読まれている場合のヘッダ名も念のため変更
if out.index.name in rename_map:
    out.index.name = rename_map[out.index.name]

# DataFrameの列名を変更
out = out.rename(columns=rename_map)

# --- 出力 ---
out_path = sys.argv[2]
out.to_csv(out_path)
print("\nSaved:", out_path)
