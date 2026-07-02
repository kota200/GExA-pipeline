import pandas as pd
import re
import collections
import difflib
import itertools
import sys
import numpy as np

input = sys.argv[1] # 使うパスに合わせて変更
df = pd.read_csv(input, index_col=0)

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
    s = re.sub(r"[_\-]+", "_", s)
    s = re.sub(r"__+", "_", s)
    return s.strip("_")


out = df.copy()

# tissue/stage側の明らかな単複・typoも辞書で（必要に応じて）

out["treatment"] = out["treatment"].replace(r"^\d+_hour$", np.nan, regex=True)
out["treatment"] = out["treatment"].replace(r"^Bacterial_strain(\d+)$",r"Inoculation_bacterial_strain_\1",regex=True)
out["treatment"] = out["treatment"].replace({"Bcterial_strain299":"Inoculation_bacterial_strain 299","salt_stress":"salt treatment","normal":"NA","Inoculated_group":"inoculation","water_treated":"water","untreated":"control","drought_stress":"drought","herbicide_treated":"herbicide","mock":"control","24_hr_exposure_to_Polyethylene_glycol_(PEG)":"PEG treatment for 24 hour","Claroideoglomus_etunicatum_inoculation":"Inoculation_Claroideoglomus_etunicatum","Control_group":"control","H-C0+BR":"brassinolide","H-C3+BR":"brassinolide","H-N0+BR":"brassinolide","H-N3+BR":"brassinolide","H-C0":"control","H-C3":"control","H-N3":"control","H-N0":"control"})
out["treatment"] = out["treatment"].replace(r"^NaCl_treatment_for_0\.5h_\d+$","salt treatment for 0.5 hour",regex=True)
out["treatment"] = out["treatment"].replace(r"^NaCl_treatment_for_48h_\d+$","salt treatment for 48 hour",regex=True)
out["treatment"] = out["treatment"].replace(r"^No_Salt_replicate\d+$","control",regex=True)
out["treatment"] = out["treatment"].replace(r"^Salt_replicate\d+$","salt treatment",regex=True)
out["treatment"] = out["treatment"].replace(r"^normal\d+$","control",regex=True)
out["tissue"] = out["tissue"].replace({"Roots":"root","developing_grain_sample":"developing seed","seedling-shoot":"shoot","leaf_sheaths":"leaf_sheath","Germinated_seeds":"Germinated_seed","roots":"root","seedlings":"seedling","spikelet":"spike","young_spikelets":"young_spike","leaves":"leaf","shoots_of_14_days_old_foxtail_millet_seedlings":"shoot","grain":"seed","Stem_top_second":"stem","Spikes":"spike","Plant":"NA","Leaf_top_foruth":"Leaf_top_fourth","Phytomer:_leaf__stem_node_and_internode":"shoot","3rd_Leaf_bundle_sheath":"third_Leaf_bundle_sheath","3rd_Leaf_mesophyll":"third_Leaf_mesophyll","Anthers":"anther","Above_ground_tissue":"shoot"})
out["tissue"] = out["tissue"].replace(r"^Crown_roots.*$", "crown_root", regex=True)
out["tissue"] = out["tissue"].replace(r"^Flag_Leaf.*$", "Flag_Leaf", regex=True)
out["tissue"] = out["tissue"].replace(r"^Primary_roots.*$", "Primary_root", regex=True)
out["tissue"] = out["tissue"].replace(r"^Seedling.*$", "seedling", regex=True)
out["tissue"] = out["tissue"].replace(r"^internode_below_the_panicle.*$", "internode_below_panicle", regex=True)
out["tissue"] = out["tissue"].replace(r"^leaf.*$", "leaf", regex=True)
out["tissue"] = out["tissue"].replace(r"^penultimate_internode.*","penultimate_internode", regex=True)
out["tissue"] = out["tissue"].replace(r"^The_control_plants_for_biological_replicate_.*$", "young spike", regex=True)
out["tissue"] = out["tissue"].replace(r"^The_edited_transformation_plants.*$", "Young spike of the_transformation_plants", regex=True)

out["stage"] = out["stage"].replace({"pre-flowering":"pre-flowering stage","Three_days_imbibition_seed":"3 days after seed imbibition","3-Leaf":"3 leaf stage","7DAA":"7 days","2_days_after_heading":"heading stage","2 week":"2 weeks","2_weeks_plant":"2 weeks","radication_protrusion":"radicle protrusion","Mature stage":"maturing stage","Mature":"maturing stage","plantlet":"NA","opening_foxtail_millet_florets":"reproductive stage","not_applicable":"NA","normal_control":"NA","missing":"NA","fully_expanded_third_leaves":"NA","foxtail_millet_five_leaf_stage":"5 leaf stage","foxtail_millet_hydroponic_for_7_days":"NA","jointing1":"jointing stage","jointing2":"jointing stage", "seeding":"seedling stage","seeding_stage":"seedling stage","seedlings":"seedling stage","seedling_stage":"seedling stage","two_weeks_seedings":"2 weeks","two-week-old_seedling_stage":"2 weeks","maturing_stages":"mature stage","seed_development":"seed_development_stage","six_leaf-old_stage":"6_leaf_stage","young_panicle_two_days_after_heading":"heading stage","harvest1":"harvest stage","harvest2":"harvest stage", "heading1":"heading stage","heading2":"heading stage","maturation_stage":"maturing_stage","mature_pollen_stage":"maturing_stage","foxtail_millet_three_leaf_stage":"three_leaf_stage","drought_+HA_treatment":"NA","drought_treatment":"NA","One_tip_two_leaf":"NA","Heading_period":"heading_stage","DPA_1_7_14_21_28_35":"NA","DPA_7_14_21_28_35":"NA","0_24_hours_after_treatment/control":"NA","10_days_after_planting":"10 days","10day":"10 days","12_days_after_planting":"12 days","12day":"12 days","14DAA":"14 days","14_days_after_planting":"14 days","16_days_after_planting":"16_days","21DAA":"21 days","21_days_post_germination":"21 days","28DAA":"28 days","30_day-old_seedling_(10_days_before_Xiaomi_heading)":"30 days","30_day-old_seedling_(10_days_before_heading)":"30 days","30d":"30 days","35DAA":"35 days", "4th_leaf_Collar":"NA","5-Leaf":"Fifth_leaf_stage", "60days":"60 days", "7-Leaf":"7 leaf stage"})

out["cultivar"] = out["cultivar"].replace(r"^xiaomi\d+$", "Xiaomi", regex=True)
out["cultivar"] = out["cultivar"].replace(r"^Xiaomi\d+$", "Xiaomi", regex=True)
out["cultivar"] = out["cultivar"].astype("string").str.replace(r"_rep\d+$", "", regex=True)
out["cultivar"] = out["cultivar"].replace(r"^NIL-A-\d+$", "NIL-A", regex=True)
out["cultivar"] = out["cultivar"].replace(r"^NIL-B-\d+$", "NIL-B", regex=True)
out["cultivar"] = out["cultivar"].replace(r"^A-\d+$", "A", regex=True)
out["cultivar"] = out["cultivar"].replace(r"^B-\d+$", "B", regex=True)
out["cultivar"] = out["cultivar"].replace(r"^JG21.*$", "JG21", regex=True)
out["cultivar"] = out["cultivar"].replace(r"^biological_replicate.*$", "NA", regex=True)

out["cultivar"] = out["cultivar"].replace({"xiaomi":"Xiaomi","foxtail_millet":"NA","YG1":"Yugu1","foxtail millet":"NA","jingu_21":"Jingu21","Jingu_21":"Jingu21","Changnong_35":"Changnong35","Setaria_italica":"NA","Setaria_viridis":"NA","Setaria_italic_Yugu1":"Yugu1","Yugu-1":"Yugu1","hydroponic_culture":"NA","missing":"NA","not_applicable":"NA","not_collected":"NA"})

for c in cols_clean:
    out[c] = out[c].map(to_lower_snake)

out["stage"] = out["stage"].map(to_lower_snake_stage)
out["tissue"] = out["tissue"].map(to_lower_snake_stage)
out["stage"] = out["stage"].replace({"na":"NA"})
out["tissue"] = out["tissue"].replace({"na":"NA"})




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
print("Pearl millet, Proso millet, Switchgrassのデータを削除します")
pattern = r"(Pearl[_\s]?millet|Proso[_\s]?millet|Switchgrass)"

code_col = "code" if "code" in out.columns else out.columns[7]  # 念のための保険
mask_drop = out[code_col].astype("string").str.contains(pattern, case=False, na=False)

print(f"[filter] drop rows where {code_col} matches pattern: {mask_drop.sum()} rows")
out = out.loc[~mask_drop].copy()
out["stage"] = out["stage"].replace({"fifth leaf stage":"5-leaf stage","two week old seedling":"2 weeks","two days after heading":"heading stage","three leaf stage":"3-leaf stage","seedling":"seedling stage","mature stage":"maturing stage","foxtail millet in hydroponics for 12 days":"under hydroponics for 12 days","2 week":"2 weeks","before flowering":"pre-flowering stage","pre flowering":"pre-flowering stage","pre flowering stage":"pre-flowering stage"})
out["stage"] = out["stage"].replace({"6 leaf stage":"6-leaf stage","3 leaf stage":"3-leaf stage","7 leaf stage":"7-leaf stage","5 leaf stage":"5-leaf stage"})
out["temperature"] = out["temperature"].replace({"Not_applicable":"NA"})
out["treatment"] = out["treatment"].replace({"Drought stress":"drought","Control":"control","NaCl":"salt treatment"})
out["tissue"] = out["tissue"].replace({"leave":"leaf","leaves":"leaf","whole seedling":"whole plant"})
out["cultivar"] = out["cultivar"].replace(r"-rep\d+$", "", regex=True)

# --- 出力 ---
out_path = sys.argv[2]
out.to_csv(out_path)
print("\nSaved:", out_path)
