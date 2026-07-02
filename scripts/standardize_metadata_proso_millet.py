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
out["stage"] = out["stage"].replace({"", ""})
out["treatment"] = out["treatment"].replace({"The_control":"control", "Treated_with_20%_PEG-6000_for_24h":"20%_PEG_24h","Treated_with_20%_PEG-6000_for_6h":"20%_PEG_6h","not_collected":"NA"})
out["cultivar"] = out["cultivar"].replace({"Disease-resistant_broomcorn_millet":"Disease_resistant","L.":"NA","broomcorn_millet":"NA","cultivar":"NA","not_applicable1":"NA","not_collected":"NA"})
out["temperature"]= out["temperature"].replace({"not_collected":"NA"})
for c in cols_clean:
    out[c] = out[c].map(to_lower_snake)

out["stage"] = out["stage"].map(to_lower_snake_stage)
out["tissue"] = out["tissue"].map(to_lower_snake_stage)
out["stage"] = out["stage"].replace({"na":"NA"})
out["tissue"] = out["tissue"].replace({"na":"NA"})

out["tissue"] = out["tissue"].replace({"leave":"leaf","tissue1":"NA","tissue2":"NA","tissue3":"NA","tissue4":"NA","tissue5":"NA","tissue6":"NA","tissue7":"NA","tissue8":"NA", "tissue9":"NA","tissue10":"NA","tissue11":"NA","tissue12":"NA","tissue13":"NA","tissue14":"NA","tissue15":"NA","tissue16":"NA","tissue17":"NA","tissue18":"NA","tissue19":"NA","tissue20":"NA","tissue21":"NA","leaves":"leaf","mature_seeds":"seed","mixture_of_roots_stems_leaves_and_seeds":"mixed"})
out["stage"] = out["stage"].replace({"14_day_seedlings": "14_days","4_week":"4_weeks","seedling":"seedling stage","booting":"booting stage","filling":"filling stage","fillling":"filling stage", "heading":"heading stage","seedling":"seedling_stage","tillering":"tillering stage","jointing":"jointing stage","not_applicable1":"NA","not_collected":"NA"})

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

# --- code列が Foxtail_millet / Pearl_millet / Switchgrass を含む行を除外 ---
# "_" と " " の揺れも拾う（Foxtail_millet / Foxtail millet どちらもOK）
print("Foxtail millet, Pearl millet, Switchgrassのデータを削除します")
pattern = r"(Foxtail[_\s]?millet|Pearl[_\s]?millet|Switchgrass)"

code_col = "code" if "code" in out.columns else out.columns[7]  # 念のための保険
mask_drop = out[code_col].astype("string").str.contains(pattern, case=False, na=False)

print(f"[filter] drop rows where {code_col} matches pattern: {mask_drop.sum()} rows")
out = out.loc[~mask_drop].copy()


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
