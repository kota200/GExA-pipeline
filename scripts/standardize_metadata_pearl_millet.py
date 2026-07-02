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
out["stage"] = out["stage"].replace({"not_collected":"NA","seeding": "seedling_stage","seedling":"seedling_stage", "Root": "NA", "not_applicable": "NA", "vegetative_growth": "vegetative_stage","vegetative":"vegetative_stage","Vegetative":"vegetative_stage", "Control": "NA", "6":"seedling_stage", "12":"seedling_stage", "24":"seedling_stage", "48":"seedling_stage", "72":"seedling_stage", "Leaf_and_Root":"NA", "three_leaves":"three_leaf_stage", "Three_leaf_stage":"three_leaf_stage", "Leaf":"NA", "3_leaf":"three_leaf_stage","Five_leaf_stage": "five_leaf_stage", "plant_stem_and_leaves":"shoot","":"NA", "inflorescence":"flowering_stage"})
out["treatment"] = out["treatment"].replace({"40_degrees_C_day-38_degrees_C_night_for_24_h_in_a_growth_chamber":"heat", "40_degrees_C_for_12_h_in_a_growth_chamber":"heat", "42_degree_celcius_for_6_hours":"heat", "4_degrees_C_for_12_h_in_a_growth_chamber":"cold", "4_degrees_C_for_24_h_in_a_growth_chamber":"cold", "Cold":"cold", "Control":"control", "Control-no_stress":"control", "FS1":"NA", "Heat":"heat", "Heat_stress":"heat","LS1":"NA", "LS2":"NA","LS3":"NA", "LS4":"NA", "LS5":"NA", "LS6":"NA", "LS7":"NA", "LS8":"NA", "LS9":"NA", "":"NA","No_stress":"control", "150mMol_salt1.2":"150mM_NaCl", "150mMol_salt2.2":"150mM_NaCl","Plants_were_grown_in_a_growth_chamber_under_a_28_degreesC_day/20_degreesC_night_condition._Florets_in_a_middle_part_of_their_panicles_were_sampled_two_days_after_anthers_emerged_from_the_florets_of_their_panicles.":"control","Plants_were_grown_in_a_growth_chamber_under_a_28_degreesC_day/20_degreesC_night_condition._Florets_in_a_middle_part_of_their_panicles_were_sampled_two_days_after_their_heads_of_panicles_became_about_to_emerge_from_the_flag_leaf.":"control", "Plants_were_grown_in_a_growth_chamber_under_a_28_degreesC_day/20_degreesC_night_condition._Florets_in_a_middle_part_of_their_panicles_were_sampled_two_days_after_their_heads_of_panicles_emerged_from_the_flag_leaf.":"control","Plants_were_grown_in_a_growth_chamber_under_a_28_degreesC_day/20_degreesC_night_condition._When_anthers_emerged_from_florets_of_their_panicles__the_condition_was_changed_to_42_degreesC_day/30_degreesC_night._The_plants_were_further_grown_for_two_days_under_this_condition__and_florets_in_a_middle_part_of_their_panicles_were_sampled.":"heat", "Plants_were_grown_in_a_growth_chamber_under_a_28_degreesC_day/20_degreesC_night_condition._When_their_heads_of_panicles_emerged_from_the_flag_leaf__the_condition_was_changed_to_42_degreesC_day/30_degreesC_night._The_plants_were_further_grown_for_two_days_under_this_condition__and_florets_in_a_middle_part_of_their_panicles_were_sampled.":"heat","Plants_were_grown_in_a_growth_chamber_under_a_28_degreesC_day/20_degreesC_night_condition._When_their_heads_of_panicles_emerged_from_the_flag_leaf__the_panicles_were_incubated_in_25-degreesC_water_for_30_seconds__and_florets_in_a_middle_part_of_their_panicles_were_sampled.":"control", "Plants_were_grown_in_a_growth_chamber_under_a_28_degreesC_day/20_degreesC_night_condition._When_their_heads_of_panicles_emerged_from_the_flag_leaf__the_panicles_were_incubated_in_42-degreesC_water_for_30_seconds__and_florets_in_a_middle_part_of_their_panicles_were_sampled.":"heat_water","Plants_were_grown_in_a_growth_chamber_under_a_28_degreesC_day/20_degreesC_night_condition._When_their_heads_of_panicles_were_about_to_emerge_from_the_flag_leaf__the_panicles_were_incubated_in_25-degreesC_water_for_30_seconds__and_florets_in_a_middle_part_of_their_panicles_were_sampled.":"control","Plants_were_grown_in_a_growth_chamber_under_a_28_degreesC_day/20_degreesC_night_condition._When_their_heads_of_panicles_were_about_to_emerge_from_the_flag_leaf__the_panicles_were_incubated_in_42-degreesC_water_for_30_seconds__and_florets_in_a_middle_part_of_their_panicles_were_sampled.":"heat_water","Plants_were_grown_in_a_growth_chamber_under_a_28_degreesC_day/20_degreesC_night_condition._When_their_heads_of_panicles_were_about_to_emerge_from_the_flag_leaf__the_condition_was_changed_to_42_degreesC_day/30_degreesC_night._The_plants_were_further_grown_for_two_days_under_this_condition__and_florets_in_a_middle_part_of_their_panicles_were_sampled.":"heat","SS1":"NA", "SS2":"NA","SS3":"NA", "TS1":"NA", "TS2":"NA", "TS3":"NA", "TS4":"NA", "TS5":"NA", "TS6":"NA", "Untreated":"control", "Waterlogging":"water_logging", "control1.3":"control","control2.2":"control", "control_1h":"control","control_3h":"control", "control_48h":"control", "control_7h":"control", "control_96h":"control", "control_for_12h":"control", "control_for_24h":"control", "second_inflorescence":"NA", "second_inflorescence":"NA", "third_inflorescence":"NA","Plants_were_grown_in_a_growth_chamber_under_a_28_degreesC_day_20_degreesC_night_condition._When_their_heads_of_panicles_were_about_to_emerge_from_the_flag_leaf_the_condition_was_changed_to_42_degreesC_day_30_degreesC_night._The_plants_were_further_grown_for_two_days_under_this_condition_and_florets_in_a_middle_part_of_their_panicles_were_sampled.":"heat","Plants_were_grown_in_a_growth_chamber_under_a_28_degreesC_day_20_degreesC_night_condition._When_their_heads_of_panicles_were_about_to_emerge_from_the_flag_leaf_the_condition_was_changed_to_42_degreesC_day_30_degreesC_night._The_plants_were_further_grown_for_two_days_under_this_condition_and_florets_in_a_middle_part_of_their_panicles_were_sampled.":"heat","control_for_12_h":"control", "control_for_24_h":"control","first_inflorescence":"NA","sample_treated_with_50C_for_60_min1.2":"heat", "sample_treated_with_50C_for_60_min2.2":"heat"})
out["cultivar"] = out["cultivar"].replace({"":"NA","841-B_and_PPMI-69":"841B_and_PPMI69","(Pennisetum_glaucum_(L.)_R._Br._ssp._monodii_(Maire)_Brun-_ken)":"Maire_Brunken","Chadi_Bajri-biological_replicate-1":"Chadi_Bajri", "Chadi_Bajri-biological_replicate-2":"Chadi_Bajri","Damodhar_Bajri-biological_replicate-1":"Damodhar_Bajri","Damodhar_Bajri-biological_replicate-2":"Damodhar_Bajri","ICMB01222C":"ICMB01222", "ICMB01222S":"ICMB01222","ICMB081C":"ICMB081", "ICMB081S":"ICMB081", "ICMB_843":"ICMB843", "ICMB_863":"ICMB863", "ICMB_93333":"ICMB93333","None":"NA", "PC701-biological_replicate-1":"PC701","PC701-biological_replicate-2":"PC701", "Pearl_millet_genotype_ICMR_356":"ICMR356", "Pearl_millet_genotypes_BMR_genotype":"BMR", "Pearl_millet_genotypes_BMR_genotypes":"BMR", "Pearl_millet_genotypes_Baif_Bajra_1":"Baif_Bajra_1","Pearl_millet_genotypes_ICMB_99666":"ICMB99666", "Pearl_millet_genotypes_IP8955":"IP8955","Pearl_millet_genotypes_IP8956":"IP8956", "Pearl_millet_genotypes_IP8957":"IP8957","Pearl_millet_genotypes_Non_BMR_genotypes":"Non_BMR","Pusa1201-biological_replicate-1":"Pusa1201", "Pusa1201-biological_replicate-2":"Pusa1201","Resistant_bulk":"NA","Suceptible_bulk":"NA","TifLeaf3":"Tifleaf3", "Tifleaf_3":"Tifleaf3","missing":"NA", "not_applicable":"NA", "tiff_leaf_3":"Tifleaf3"})
out["temperature"]= out["temperature"].replace({"":"NA"})
for c in cols_clean:
    out[c] = out[c].map(to_lower_snake)

out["stage"] = out["stage"].map(to_lower_snake_stage)
out["tissue"] = out["tissue"].map(to_lower_snake_stage)
out["stage"] = out["stage"].replace({"na":"NA"})
out["tissue"] = out["tissue"].replace({"na":"NA"})

out["tissue"] = out["tissue"].replace({"flower_and_leaf":"all_tissues","lateral_roots":"lateral_root", "crown_roots":"crown_root","primary_roots":"primary_root","leaves": "leaf", "leave": "leaf", "roots": "root", "plant_stem":"stem", "inflorescence": "flower", "spike": "flower", "plant_stem_and_leaves": "shoot", "root__leaf__stem__spike": "all_tissues", "leaf_and_root":"all_tissues", "inflorescence": "flower", "ci134root_1":"root", "ci134root_2":"root", "ci134root_3":"root","ci134shoot_1":"shoot","ci134shoot_2":"shoot","ci134shoot_3":"shoot","root_leaf_stem_spike":"all_tissues", "plant_leaves":"leaf","all_tissues":"NA", "":"NA"})
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

# --- code列が Foxtail_millet / Proso_millet / Switchgrass を含む行を除外 ---
# "_" と " " の揺れも拾う（Foxtail_millet / Foxtail millet どちらもOK）
print("Foxtail millet, Proso millet, Switchgrassのデータを削除します")
pattern = r"(Foxtail[_\s]?millet|Proso[_\s]?millet|Switchgrass)"

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


# --- 出力 ---
out_path = sys.argv[2]
out.to_csv(out_path)
print("\nSaved:", out_path)
