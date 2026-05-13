import base64
import io
import math
import struct
import wave
from itertools import product
from pathlib import Path

import streamlit as st


st.set_page_config(
    page_title="Cyprus Conjoint Predictions",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


ATTRIBUTES = [
    "political_structure",
    "territorial_arrangements",
    "compensation_property",
    "security_guarantees",
    "judicial_system",
    "energy_cooperation",
]


GSP_LOGO = Path("gsp_logo.png")
UCFS_LOGO = Path("ucfs_logo.png")
INCPEACE_LOGO = Path("incpeace_logo.png")
LSE_HELLENIC_LOGO = Path("lse_hellenic.png")


LEVELS = {
    "political_structure": [
        "rotating_presidency",
        "parliamentary_quarter_approval",
        "parliamentary_simple_majority",
        "separate_presidents_veto",
    ],
    "territorial_arrangements": [
        "morphou_stays_tc",
        "plus_morphou",
        "plus_morphou_karpasia_yialousa",
        "plus_old_morphou_karpasia_yialousa",
        "morphou_north_karpasia_federal_areas",
    ],
    "compensation_property": [
        "comp_50000",
        "comp_150000",
        "comp_200000",
        "comp_300000",
        "comp_300000_housing",
    ],
    "security_guarantees": [
        "un_former_guarantors",
        "un_nato",
        "un_eu_countries",
        "un_third_countries",
    ],
    "judicial_system": [
        "equal_gc_tc_rotating_chair",
        "equal_gc_tc_echr_minority",
        "echr_majority",
        "un_special_tribunal",
    ],
    "energy_cooperation": [
        "cyprus_turkey_pipeline",
        "electricity_interconnection",
        "joint_solar_buffer_zone",
        "east_med_pipeline",
        "vasiliko_lng",
    ],
}


DEFAULT_PACKAGE = {
    "political_structure": "parliamentary_quarter_approval",
    "territorial_arrangements": "morphou_north_karpasia_federal_areas",
    "compensation_property": "comp_300000_housing",
    "security_guarantees": "un_eu_countries",
    "judicial_system": "un_special_tribunal",
    "energy_cooperation": "cyprus_turkey_pipeline",
}


AGREEMENT_THRESHOLD = 0.55


MODEL = {
    "GC": {
        "n_respondents": 775,
        "n_profiles": 7750,
        "forced": {
            "intercept": 0.0621724390,
            "effects": {
                "political_structure": [0.0, 0.0923672109, 0.0888449798, 0.0124212924],
                "territorial_arrangements": [0.0, 0.1426529268, 0.1920025101, 0.1955381864, 0.1428630795],
                "compensation_property": [0.0, 0.0601733243, 0.0778371268, 0.0712828585, 0.0872024445],
                "security_guarantees": [0.0, 0.0784392929, 0.1430113298, 0.1006150665],
                "judicial_system": [0.0, 0.0510109728, 0.0599218446, 0.0711048637],
                "energy_cooperation": [0.0, 0.0973105688, 0.1049016546, 0.0743202673, 0.0709743423],
            },
        },
    },
    "TC": {
        "n_respondents": 867,
        "n_profiles": 8572,
        "forced": {
            "intercept": 0.6698720995,
            "effects": {
                "political_structure": [0.0, 0.0473050389, 0.0317658462, -0.0026556465],
                "territorial_arrangements": [0.0, -0.1558565629, -0.1652104473, -0.1935891476, -0.0989018284],
                "compensation_property": [0.0, 0.0283518356, -0.0021436807, 0.0229309287, 0.0338531091],
                "security_guarantees": [0.0, 0.0003673689, -0.0244668556, -0.0226344237],
                "judicial_system": [0.0, -0.0121059164, -0.0184363395, -0.0138930431],
                "energy_cooperation": [0.0, -0.0896216006, -0.0505976814, -0.0938678383, -0.0773204659],
            },
        },
    },
}


UI = {
    "English": {
        "title": "Conjoint Analysis Predictions",
        "language": "Language",
        "package": "Settlement package",
        "results_title": "Predicted support by community",
        "forced": "Predicted support by forced-choice question",
        "gc_support": "Greek Cypriot support",
        "tc_support": "Turkish Cypriot support",
        "joint_support": "Joint support",
        "difference": "Difference between communities",
        "summary": "Summary",
        "extremes_title": "Most and least supportive packages in both communities",
        "highest_gc_heading": "Highest predicted support among Greek Cypriots",
        "lowest_gc_heading": "Lowest predicted support among Greek Cypriots",
        "highest_tc_heading": "Highest predicted support among Turkish Cypriots",
        "lowest_tc_heading": "Lowest predicted support among Turkish Cypriots",
        "package_intro": "The package is estimated at {support}",
        "package_parts": {
            "political_structure": "On political structure, it combines {level}",
            "territorial_arrangements": "On the territorial aspect, it entails {level}",
            "compensation_property": "On compensation and property, it gives {level}",
            "security_guarantees": "On security and implementation, it proposes that {level} will be responsible",
            "judicial_system": "On the judicial system, it provides for {level}",
            "energy_cooperation": "Finally, on energy co-operation, it proposes {level}",
        },
        "viable_title": "Packages above 55% in both communities",
        "viable_intro": "{count} of {total} possible packages reach at least 55% predicted support in both communities. The strongest joint-support packages are:",
        "viable_none": "No package in this design reaches at least 55% predicted support in both communities.",
        "sound_toggle": "Enable sound cues",
        "agreement_success_title": "Shared agreement achieved",
        "agreement_success_body": "This package reaches at least 55% predicted support in both communities.",
        "agreement_progress_title": "Keep negotiating",
        "agreement_progress_body": "The goal is 55% or higher predicted support in both communities.",
        "passed": "Passed",
        "below_target": "Below target",
        "gc": "Greek Cypriot Community",
        "tc": "Turkish Cypriot Community",
        "sample": "Sample",
        "profiles": "profiles",
        "method_note": "Predictions use the first-stage forced-choice linear probability model estimated from the raw conjoint exports for each community.",
        "attributes": {
            "political_structure": "Political Structure",
            "territorial_arrangements": "Territorial Arrangements",
            "compensation_property": "Compensation & Property",
            "security_guarantees": "Security Guarantees",
            "judicial_system": "Judicial System",
            "energy_cooperation": "Energy Cooperation",
        },
    },
    "Ελληνικά": {
        "title": "Προβλέψεις Ανάλυσης Conjoint",
        "language": "Γλώσσα",
        "package": "Πακέτο λύσης",
        "results_title": "Προβλεπόμενη στήριξη ανά κοινότητα",
        "forced": "Προβλεπόμενη στήριξη στην ερώτηση αναγκαστικής επιλογής",
        "gc_support": "Ελληνοκυπριακή στήριξη",
        "tc_support": "Τουρκοκυπριακή στήριξη",
        "joint_support": "Κοινή στήριξη",
        "difference": "Διαφορά μεταξύ κοινοτήτων",
        "summary": "Σύνοψη",
        "extremes_title": "Πακέτα με τη μεγαλύτερη και τη μικρότερη στήριξη και στις δύο κοινότητες",
        "highest_gc_heading": "Υψηλότερη προβλεπόμενη στήριξη μεταξύ των Ελληνοκυπρίων",
        "lowest_gc_heading": "Χαμηλότερη προβλεπόμενη στήριξη μεταξύ των Ελληνοκυπρίων",
        "highest_tc_heading": "Υψηλότερη προβλεπόμενη στήριξη μεταξύ των Τουρκοκυπρίων",
        "lowest_tc_heading": "Χαμηλότερη προβλεπόμενη στήριξη μεταξύ των Τουρκοκυπρίων",
        "package_intro": "Το πακέτο εκτιμάται στο {support}",
        "package_parts": {
            "political_structure": "Στην πολιτειακή δομή, συνδυάζει {level}",
            "territorial_arrangements": "Στο εδαφικό, προβλέπει ότι {level}",
            "compensation_property": "Στην αποζημίωση και την περιουσία, δίνει {level}",
            "security_guarantees": "Στην ασφάλεια και την εφαρμογή, προτείνει ότι {level} θα έχει την ευθύνη",
            "judicial_system": "Στο δικαστικό σύστημα, προβλέπει {level}",
            "energy_cooperation": "Τέλος, στην ενεργειακή συνεργασία, προτείνει {level}",
        },
        "viable_title": "Πακέτα πάνω από 55% και στις δύο κοινότητες",
        "viable_intro": "{count} από τα {total} δυνατά πακέτα φτάνουν τουλάχιστον 55% προβλεπόμενη στήριξη και στις δύο κοινότητες. Τα ισχυρότερα πακέτα κοινής στήριξης είναι:",
        "viable_none": "Κανένα πακέτο σε αυτόν τον σχεδιασμό δεν φτάνει τουλάχιστον 55% προβλεπόμενη στήριξη και στις δύο κοινότητες.",
        "gc": "Ελληνοκυπριακή Κοινότητα",
        "tc": "Τουρκοκυπριακή Κοινότητα",
        "sample": "Δείγμα",
        "profiles": "προφίλ",
        "method_note": "Οι προβλέψεις βασίζονται στο πρώτο στάδιο της αναγκαστικής επιλογής, με γραμμικό μοντέλο πιθανότητας που εκτιμήθηκε από τα αρχικά αρχεία conjoint για κάθε κοινότητα.",
        "attributes": {
            "political_structure": "Πολιτειακή Δομή",
            "territorial_arrangements": "Εδαφικές Ρυθμίσεις",
            "compensation_property": "Αποζημίωση & Περιουσία",
            "security_guarantees": "Εγγυήσεις Ασφάλειας",
            "judicial_system": "Δικαστικό Σύστημα",
            "energy_cooperation": "Ενεργειακή Συνεργασία",
        },
    },
    "Türkçe": {
        "title": "Konjoint Analizi Tahminleri",
        "language": "Dil",
        "package": "Çözüm paketi",
        "results_title": "Toplumlara göre tahmini destek",
        "forced": "Zorunlu tercih sorusunda tahmini destek",
        "gc_support": "Kıbrıslı Rum desteği",
        "tc_support": "Kıbrıslı Türk desteği",
        "joint_support": "Ortak destek",
        "difference": "Toplumlar arasındaki fark",
        "summary": "Özet",
        "extremes_title": "Her iki toplumda en yüksek ve en düşük destek alan paketler",
        "highest_gc_heading": "Kıbrıslı Rumlar arasında en yüksek tahmini destek",
        "lowest_gc_heading": "Kıbrıslı Rumlar arasında en düşük tahmini destek",
        "highest_tc_heading": "Kıbrıslı Türkler arasında en yüksek tahmini destek",
        "lowest_tc_heading": "Kıbrıslı Türkler arasında en düşük tahmini destek",
        "package_intro": "Bu paket {support} olarak tahmin edilmektedir",
        "package_parts": {
            "political_structure": "Siyasi yapı bakımından {level} seçeneğini içerir",
            "territorial_arrangements": "Toprak düzenlemeleri bakımından {level}",
            "compensation_property": "Tazminat ve mülkiyet bakımından {level}",
            "security_guarantees": "Güvenlik ve uygulama bakımından {level} sorumlu olur",
            "judicial_system": "Yargı sistemi bakımından {level} seçeneğini içerir",
            "energy_cooperation": "Son olarak enerji işbirliği bakımından {level} seçeneğini önerir",
        },
        "viable_title": "Her iki toplumda da %55'in üzerine çıkan paketler",
        "viable_intro": "{total} olası paketin {count} tanesi her iki toplumda da en az %55 tahmini desteğe ulaşır. En güçlü ortak destek paketleri şunlardır:",
        "viable_none": "Bu tasarımda hiçbir paket her iki toplumda da en az %55 tahmini desteğe ulaşmıyor.",
        "gc": "Kıbrıslı Rum Toplumu",
        "tc": "Kıbrıslı Türk Toplumu",
        "sample": "Örneklem",
        "profiles": "profil",
        "method_note": "Tahminler, her toplum için ham konjoint çıktılarından hesaplanan birinci aşama zorunlu tercih doğrusal olasılık modeline dayanır.",
        "attributes": {
            "political_structure": "Siyasi Yapı",
            "territorial_arrangements": "Toprak Düzenlemeleri",
            "compensation_property": "Tazminat & Mülkiyet",
            "security_guarantees": "Güvenlik Garantileri",
            "judicial_system": "Yargı Sistemi",
            "energy_cooperation": "Enerji İşbirliği",
        },
    },
}


LABELS = {
    "English": {
        "rotating_presidency": "Rotating presidency, cross-voting and veto power for co-chairs (presidential system)",
        "parliamentary_quarter_approval": "Political parties according to electoral support, with at least one quarter of MPs from each community approving legislation (parliamentary system)",
        "parliamentary_simple_majority": "Political parties supported by a simple majority (parliamentary system)",
        "separate_presidents_veto": "Presidents elected separately by each community, with veto power (presidential system)",
        "morphou_stays_tc": "Morphou stays under Turkish Cypriot administration",
        "plus_morphou": "Plus Morphou",
        "plus_morphou_karpasia_yialousa": "Plus Morphou, Rizokarpaso and Yialousa",
        "plus_old_morphou_karpasia_yialousa": "Plus old Morphou, Rizokarpaso and Yialousa",
        "morphou_north_karpasia_federal_areas": "Morphou and North Karpasia become Federal Areas",
        "comp_50000": "50,000 Euros on average, depending on a fair UN-expert estimate of loss",
        "comp_150000": "150,000 Euros on average, depending on a fair UN-expert estimate of loss",
        "comp_200000": "200,000 Euros on average, depending on a fair UN-expert estimate of loss",
        "comp_300000": "300,000 Euros on average, depending on a fair UN-expert estimate of loss",
        "comp_300000_housing": "300,000 Euros on average plus guaranteed housing anywhere in Cyprus",
        "un_former_guarantors": "UN with the three former guarantors Greece, Turkey and the United Kingdom",
        "un_nato": "UN with a third party such as NATO",
        "un_eu_countries": "UN with EU countries such as Ireland, France and Germany",
        "un_third_countries": "UN with third countries such as Japan, Australia and Canada",
        "equal_gc_tc_rotating_chair": "Equal number of GCs and TCs with rotating chair",
        "equal_gc_tc_echr_minority": "Equal number of GCs and TCs with a minority of judges appointed by the ECHR",
        "echr_majority": "Majority of judges appointed by the ECHR",
        "un_special_tribunal": "Special international UN tribunal with headquarters in Cyprus",
        "cyprus_turkey_pipeline": "Natural gas pipeline from Cyprus to Turkey",
        "electricity_interconnection": "Electricity interconnection from Israel via Cyprus to Greece",
        "joint_solar_buffer_zone": "Joint solar park in the buffer zone with the other community",
        "east_med_pipeline": "Natural gas pipeline from Israel via Cyprus to Greece (East Med)",
        "vasiliko_lng": "Natural gas liquefaction station in cooperation with Israel in Vasiliko",
    },
    "Ελληνικά": {
        "rotating_presidency": "Εκ περιτροπής προεδρία, με διασταυρούμενη ψήφο και δικαίωμα βέτο για τους συμπροέδρους (προεδρικό σύστημα)",
        "parliamentary_quarter_approval": "Πολιτικά κόμματα ανάλογα με την εκλογική τους δύναμη, με έγκριση τουλάχιστον του ενός τετάρτου των βουλευτών από κάθε κοινότητα (κοινοβουλευτικό σύστημα)",
        "parliamentary_simple_majority": "Πολιτικά κόμματα με στήριξη απλής πλειοψηφίας (κοινοβουλευτικό σύστημα)",
        "separate_presidents_veto": "Πρόεδροι που εκλέγονται χωριστά από κάθε κοινότητα, με δικαίωμα βέτο (προεδρικό σύστημα)",
        "morphou_stays_tc": "Η Μόρφου παραμένει υπό τουρκοκυπριακή διοίκηση",
        "plus_morphou": "Συν τη Μόρφου",
        "plus_morphou_karpasia_yialousa": "Συν τη Μόρφου, το Ριζοκάρπασο και τη Γιαλούσα",
        "plus_old_morphou_karpasia_yialousa": "Συν την παλιά Μόρφου, το Ριζοκάρπασο και τη Γιαλούσα",
        "morphou_north_karpasia_federal_areas": "Η Μόρφου και η Βόρεια Καρπασία γίνονται Ομοσπονδιακές Περιοχές",
        "comp_50000": "50.000 ευρώ κατά μέσο όρο, βάσει δίκαιης εκτίμησης απώλειας από εμπειρογνώμονες του ΟΗΕ",
        "comp_150000": "150.000 ευρώ κατά μέσο όρο, βάσει δίκαιης εκτίμησης απώλειας από εμπειρογνώμονες του ΟΗΕ",
        "comp_200000": "200.000 ευρώ κατά μέσο όρο, βάσει δίκαιης εκτίμησης απώλειας από εμπειρογνώμονες του ΟΗΕ",
        "comp_300000": "300.000 ευρώ κατά μέσο όρο, βάσει δίκαιης εκτίμησης απώλειας από εμπειρογνώμονες του ΟΗΕ",
        "comp_300000_housing": "300.000 ευρώ κατά μέσο όρο και εγγυημένη κατοικία οπουδήποτε στην Κύπρο",
        "un_former_guarantors": "ΟΗΕ με τις τρεις πρώην εγγυήτριες δυνάμεις, Ελλάδα, Τουρκία και Ηνωμένο Βασίλειο",
        "un_nato": "ΟΗΕ με τρίτο μέρος όπως το ΝΑΤΟ",
        "un_eu_countries": "ΟΗΕ με χώρες της ΕΕ όπως η Ιρλανδία, η Γαλλία και η Γερμανία",
        "un_third_countries": "ΟΗΕ με τρίτες χώρες όπως η Ιαπωνία, η Αυστραλία και ο Καναδάς",
        "equal_gc_tc_rotating_chair": "Ίσος αριθμός Ε/Κ και Τ/Κ με εκ περιτροπής προεδρεύοντα",
        "equal_gc_tc_echr_minority": "Ίσος αριθμός Ε/Κ και Τ/Κ με μειοψηφία δικαστών διορισμένων από το ΕΔΑΔ",
        "echr_majority": "Πλειοψηφία δικαστών διορισμένων από το ΕΔΑΔ",
        "un_special_tribunal": "Ειδικό διεθνές δικαστήριο του ΟΗΕ με έδρα στην Κύπρο",
        "cyprus_turkey_pipeline": "Αγωγός φυσικού αερίου από την Κύπρο προς την Τουρκία",
        "electricity_interconnection": "Ηλεκτρική διασύνδεση από το Ισραήλ μέσω Κύπρου προς την Ελλάδα",
        "joint_solar_buffer_zone": "Κοινό ηλιακό πάρκο στη νεκρή ζώνη με την τουρκοκυπριακή κοινότητα",
        "east_med_pipeline": "Αγωγός φυσικού αερίου από το Ισραήλ μέσω Κύπρου προς την Ελλάδα (East Med)",
        "vasiliko_lng": "Σταθμός υγροποίησης φυσικού αερίου σε συνεργασία με το Ισραήλ στο Βασιλικό",
    },
    "Türkçe": {
        "rotating_presidency": "Dönüşümlü başkanlık, eş başkanlar için çapraz oy ve veto hakkı (başkanlık sistemi)",
        "parliamentary_quarter_approval": "Siyasi partiler seçimlerdeki desteklerine göre temsil edilir ve her toplumdan milletvekillerinin en az dörtte biri yasayı onaylar (parlamenter sistem)",
        "parliamentary_simple_majority": "Basit çoğunluğun desteğine sahip siyasi partiler tarafından (parlamenter sistem)",
        "separate_presidents_veto": "Her toplum tarafından ayrı ayrı seçilecek ve veto yetkisine sahip başkanlar tarafından (başkanlık sistemi)",
        "morphou_stays_tc": "Omorfo, Kıbrıs Türk yönetimi altında kalır",
        "plus_morphou": "Omorfo, Kıbrıs Rum yönetimi altına alınır",
        "plus_morphou_karpasia_yialousa": "Omporfo, Karpaz ve Yeni Erenköy Kıbrıs Rum yönetimi altına geçer",
        "plus_old_morphou_karpasia_yialousa": "Omorfo, Karpaz ve Yeni Erenköy'ün eski şehirleri Kıbrıs Rum yönetimine devredilir",
        "morphou_north_karpasia_federal_areas": "Omorfo ve Kuzey Karpaz ortaklaşa yönetilen Federal Bölgeler olur",
        "comp_50000": "BM uzmanlarının kayıplara ilişkin adil tahminlerine göre ortalama 50.000 Euro",
        "comp_150000": "BM uzmanlarının kayıplara ilişkin adil tahminlerine göre ortalama 150.000 Euro",
        "comp_200000": "BM uzmanlarının kayıp tahminine göre ortalama 200.000 Euro",
        "comp_300000": "BM uzmanlarının kayıp tahminine göre ortalama 300.000 Euro",
        "comp_300000_housing": "Ortalama 300.000 Euro ve Kıbrıs'ın herhangi bir yerinde garantili konut",
        "un_former_guarantors": "BM ile üç eski garantör ülke Yunanistan, Türkiye ve Birleşik Krallık",
        "un_nato": "BM ile NATO gibi üçüncü taraflar",
        "un_eu_countries": "İrlanda, Fransa ve Almanya gibi AB ülkeleri ile BM",
        "un_third_countries": "BM ile Japonya, Avustralya ve Kanada gibi üçüncü ülkeler",
        "equal_gc_tc_rotating_chair": "Eşit sayıda Kıbrıslı Rum ve Kıbrıslı Türk yargıç ile dönüşümlü başkanlık",
        "equal_gc_tc_echr_minority": "Eşit sayıda Kıbrıslı Rum ve Kıbrıslı Türk yargıç ile AİHM tarafından atanan azınlık yargıçlar",
        "echr_majority": "AİHM tarafından atanan yargıçların çoğunluğu",
        "un_special_tribunal": "Kıbrıs'ta merkezi bulunan özel bir uluslararası BM mahkemesi",
        "cyprus_turkey_pipeline": "Kıbrıs ile Türkiye arasında doğal gaz boru hattı",
        "electricity_interconnection": "İsrail'den Kıbrıs üzerinden Yunanistan'a elektrik bağlantısı",
        "joint_solar_buffer_zone": "Kıbrıs Rum toplumu ile kullanılmayan ara bölgede ortak güneş enerjisi parkı",
        "east_med_pipeline": "İsrail'den Kıbrıs üzerinden Yunanistan'a doğal gaz boru hattı (Doğu Akdeniz)",
        "vasiliko_lng": "İsrail ile işbirliği içinde Vasiliko'da doğal gaz sıvılaştırma istasyonu",
    },
}


def clamp_probability(value: float) -> float:
    return min(max(value, 0.0), 1.0)


def predict(group: str, model_name: str, selected: dict[str, str]) -> float:
    model = MODEL[group][model_name]
    value = model["intercept"]

    for attribute in ATTRIBUTES:
        selected_level = selected[attribute]
        level_index = LEVELS[attribute].index(selected_level)
        value += model["effects"][attribute][level_index]

    return clamp_probability(value)


def all_packages() -> list[dict[str, str]]:
    packages = []
    level_lists = [LEVELS[attribute] for attribute in ATTRIBUTES]

    for combination in product(*level_lists):
        packages.append(dict(zip(ATTRIBUTES, combination)))

    return packages


def find_extreme_package(group: str, find_max: bool) -> tuple[float, dict[str, str]]:
    scored = [(predict(group, "forced", package), package) for package in all_packages()]
    return max(scored, key=lambda item: item[0]) if find_max else min(scored, key=lambda item: item[0])


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def whole_pct(value: float) -> str:
    return f"{value * 100:.0f}%"


def text_value(text: dict[str, object], key: str, fallback: str) -> str:
    value = text.get(key)
    return str(value) if value else fallback


def support_status(value: float) -> str:
    return "passed" if value >= AGREEMENT_THRESHOLD else "below_target"


def play_agreement_tone(kind: str) -> None:
    if kind not in {"success", "failure"}:
        return

    sequence = [(523.25, 0.11), (659.25, 0.11), (783.99, 0.18)] if kind == "success" else [(220, 0.14), (164.81, 0.20)]
    sample_rate = 44100
    amplitude = 0.18 if kind == "success" else 0.11
    silence = int(sample_rate * 0.035)
    frames = []

    for frequency, duration in sequence:
        sample_count = int(sample_rate * duration)
        for sample_index in range(sample_count):
            fade = min(1.0, sample_index / max(1, sample_rate * 0.015), (sample_count - sample_index) / max(1, sample_rate * 0.04))
            value = int(32767 * amplitude * fade * math.sin(2 * math.pi * frequency * sample_index / sample_rate))
            frames.append(struct.pack("<h", value))
        frames.extend(struct.pack("<h", 0) for _ in range(silence))

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b"".join(frames))

    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    st.markdown(
        f"""
        <audio autoplay style="display:none">
            <source src="data:audio/wav;base64,{encoded}" type="audio/wav">
        </audio>
        """,
        unsafe_allow_html=True,
    )


def render_agreement_status(text: dict[str, object], gc_support: float, tc_support: float) -> bool:
    success = gc_support >= AGREEMENT_THRESHOLD and tc_support >= AGREEMENT_THRESHOLD
    status_class = "success" if success else "progress"
    icon = "&#129309;" if success else "&#127919;"
    title = text_value(
        text,
        "agreement_success_title" if success else "agreement_progress_title",
        "Shared agreement achieved" if success else "Keep negotiating",
    )
    body = text_value(
        text,
        "agreement_success_body" if success else "agreement_progress_body",
        "This package reaches at least 55% predicted support in both communities."
        if success
        else "The goal is 55% or higher predicted support in both communities.",
    )
    gc_status = support_status(gc_support)
    tc_status = support_status(tc_support)
    passed = text_value(text, "passed", "Passed")
    below_target = text_value(text, "below_target", "Below target")

    st.markdown(
        f"""
        <section class="agreement-status agreement-status-{status_class}">
            <div class="agreement-symbol">{icon}</div>
            <div class="agreement-copy">
                <div class="agreement-title">{title}</div>
                <div class="agreement-body">{body}</div>
            </div>
            <div class="agreement-badges">
                <span class="agreement-badge agreement-badge-{gc_status}">{text['gc_support']}: {whole_pct(gc_support)} - {"&#10003;" if gc_status == "passed" else "&#9679;"} {passed if gc_status == "passed" else below_target}</span>
                <span class="agreement-badge agreement-badge-{tc_status}">{text['tc_support']}: {whole_pct(tc_support)} - {"&#10003;" if tc_status == "passed" else "&#9679;"} {passed if tc_status == "passed" else below_target}</span>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    return success


def diagnose_culprit(selected: dict[str, str], gc_support: float, tc_support: float) -> dict[str, object] | None:
    current_gap = {
        "GC": max(0.0, AGREEMENT_THRESHOLD - gc_support),
        "TC": max(0.0, AGREEMENT_THRESHOLD - tc_support),
    }
    failed_groups = [group for group, gap in current_gap.items() if gap > 0]
    if not failed_groups:
        return None

    baseline_gap = sum(current_gap[group] for group in failed_groups)
    best: dict[str, object] | None = None

    for attribute in ATTRIBUTES:
        current_level = selected[attribute]
        for candidate_level in LEVELS[attribute]:
            if candidate_level == current_level:
                continue

            candidate = dict(selected)
            candidate[attribute] = candidate_level
            candidate_gc = predict("GC", "forced", candidate)
            candidate_tc = predict("TC", "forced", candidate)
            candidate_gap = {
                "GC": max(0.0, AGREEMENT_THRESHOLD - candidate_gc),
                "TC": max(0.0, AGREEMENT_THRESHOLD - candidate_tc),
            }
            gap_reduction = baseline_gap - sum(candidate_gap[group] for group in failed_groups)
            joint_after = min(candidate_gc, candidate_tc)

            if best is None or (gap_reduction, joint_after) > (best["gap_reduction"], best["joint_after"]):
                best = {
                    "attribute": attribute,
                    "current_level": current_level,
                    "candidate_level": candidate_level,
                    "gc_after": candidate_gc,
                    "tc_after": candidate_tc,
                    "joint_after": joint_after,
                    "gap_reduction": gap_reduction,
                    "failed_groups": failed_groups,
                }

    if best and best["gap_reduction"] > 0:
        return best
    return None


def render_culprit_feedback(language: str, selected: dict[str, str], gc_support: float, tc_support: float) -> None:
    culprit = diagnose_culprit(selected, gc_support, tc_support)
    text = UI[language]
    if culprit is None:
        st.markdown(
            """
            <section class="culprit-card">
                <div class="culprit-title">&#128269; No single clear bottleneck found</div>
                <div class="culprit-body">Try changing a combination of attributes. A single attribute switch does not clearly move the package toward 55% in the community or communities below target.</div>
            </section>
            """,
            unsafe_allow_html=True,
        )
        return

    attribute = culprit["attribute"]
    current_level = culprit["current_level"]
    candidate_level = culprit["candidate_level"]
    failed_names = ", ".join(text["gc"] if group == "GC" else text["tc"] for group in culprit["failed_groups"])

    st.markdown(
        f"""
        <section class="culprit-card">
            <div class="culprit-title">&#128269; Likely bottleneck: {text["attributes"][attribute]}</div>
            <div class="culprit-body">
                The community below target is: <strong>{failed_names}</strong>.
                The current choice is <strong>{LABELS[language][current_level]}</strong>.
                Try an alternative such as <strong>{LABELS[language][candidate_level]}</strong>.
            </div>
            <div class="culprit-impact">
                This looks like the most promising single attribute to experiment with next.
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_card(label: str, value: float) -> None:
    st.markdown(
        f"""
        <section class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{whole_pct(value)}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_result_card(group: str, language: str, selected: dict[str, str], forced: float) -> None:
    text = UI[language]
    community_name = text["gc"] if group == "GC" else text["tc"]
    sample = MODEL[group]

    st.markdown(
        f"""
        <section class="result-card">
            <div class="community-name">{community_name}</div>
            <div class="sample-line">{text["sample"]}: {sample["n_respondents"]:,} | {sample["n_profiles"]:,} {text["profiles"]}</div>
            <div class="metric-single">
                <div class="metric-label">{text["forced"]}</div>
                <div class="metric-value">{pct(forced)}</div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_summary_table(text: dict[str, str], gc_support: float, tc_support: float) -> None:
    joint_support = min(gc_support, tc_support)
    difference = abs(gc_support - tc_support)

    rows = [
        (text["gc_support"], whole_pct(gc_support)),
        (text["tc_support"], whole_pct(tc_support)),
        (text["joint_support"], whole_pct(joint_support)),
        (text["difference"], whole_pct(difference)),
    ]
    body = "\n".join(f"<tr><td>{label}</td><td>{value}</td></tr>" for label, value in rows)

    st.markdown(
        f"""
        <section class="summary-card">
            <div class="summary-title">{text["summary"]}</div>
            <table class="summary-table">
                <tbody>{body}</tbody>
            </table>
        </section>
        """,
        unsafe_allow_html=True,
    )


def package_sentence(language: str, package: dict[str, str], include_attribute_names: bool = False) -> str:
    if include_attribute_names:
        attributes = UI[language]["attributes"]
        return "; ".join(
            f"{attributes[attribute]}: {LABELS[language][package[attribute]]}"
            for attribute in ATTRIBUTES
        )

    return "; ".join(LABELS[language][package[attribute]] for attribute in ATTRIBUTES)


TC_ENGLISH_LEVELS = {
    "territorial_arrangements": {
        "morphou_stays_tc": "that Morphou stays under Turkish Cypriot administration",
        "plus_morphou": "that Morphou is returned under Greek Cypriot administration",
        "plus_morphou_karpasia_yialousa": "that Morphou, Rizokarpaso and Yialousa are returned under Greek Cypriot administration",
        "plus_old_morphou_karpasia_yialousa": "that old Morphou, Rizokarpaso and Yialousa are returned under Greek Cypriot administration",
        "morphou_north_karpasia_federal_areas": "that Morphou and North Karpasia become jointly administered Federal Areas",
    },
    "compensation_property": {
        "comp_50000": "50,000 Euros on average to users who lose the property currently used, depending on a fair UN-expert estimate of loss",
        "comp_150000": "150,000 Euros on average to users who lose the property currently used, depending on a fair UN-expert estimate of loss",
        "comp_200000": "200,000 Euros on average to users who lose the property currently used, depending on a fair UN-expert estimate of loss",
        "comp_300000": "300,000 Euros on average to users who lose the property currently used, depending on a fair UN-expert estimate of loss",
        "comp_300000_housing": "300,000 Euros on average to users who will lose property plus guaranteed housing anywhere in Cyprus",
    },
}


GC_ENGLISH_LEVELS = {
    "compensation_property": {
        "comp_50000": "50,000 Euros on average to owners of properties, Internally Displaced Greek Cypriot People (IDPs), depending on a fair UN-expert estimate of loss",
        "comp_150000": "150,000 Euros on average to owners of properties, Internally Displaced Greek Cypriot People (IDPs), depending on a fair UN-expert estimate of loss",
        "comp_200000": "200,000 Euros on average to owners of properties, Internally Displaced Greek Cypriot People (IDPs), depending on a fair UN-expert estimate of loss",
        "comp_300000": "300,000 Euros on average to owners of properties, Internally Displaced Greek Cypriot People (IDPs), depending on a fair UN-expert estimate of loss",
        "comp_300000_housing": "300,000 Euros on average to owners of properties, Internally Displaced Greek Cypriot People (IDPs), plus guaranteed housing anywhere in Cyprus",
    },
}


GC_GREEK_LEVELS = {
    "compensation_property": {
        "comp_50000": "50.000 ευρώ κατά μέσο όρο στους ιδιοκτήτες περιουσιών, Ελληνοκύπριους Εσωτερικά Εκτοπισμένους (IDPs), βάσει δίκαιης εκτίμησης απώλειας από εμπειρογνώμονες του ΟΗΕ",
        "comp_150000": "150.000 ευρώ κατά μέσο όρο στους ιδιοκτήτες περιουσιών, Ελληνοκύπριους Εσωτερικά Εκτοπισμένους (IDPs), βάσει δίκαιης εκτίμησης απώλειας από εμπειρογνώμονες του ΟΗΕ",
        "comp_200000": "200.000 ευρώ κατά μέσο όρο στους ιδιοκτήτες περιουσιών, Ελληνοκύπριους Εσωτερικά Εκτοπισμένους (IDPs), βάσει δίκαιης εκτίμησης απώλειας από εμπειρογνώμονες του ΟΗΕ",
        "comp_300000": "300.000 ευρώ κατά μέσο όρο στους ιδιοκτήτες περιουσιών, Ελληνοκύπριους Εσωτερικά Εκτοπισμένους (IDPs), βάσει δίκαιης εκτίμησης απώλειας από εμπειρογνώμονες του ΟΗΕ",
        "comp_300000_housing": "300.000 ευρώ κατά μέσο όρο στους ιδιοκτήτες περιουσιών, Ελληνοκύπριους Εσωτερικά Εκτοπισμένους (IDPs), και εγγυημένη κατοικία οπουδήποτε στην Κύπρο",
    },
}


TC_GREEK_LEVELS = {
    "territorial_arrangements": {
        "morphou_stays_tc": "η Μόρφου παραμένει υπό τουρκοκυπριακή διοίκηση",
        "plus_morphou": "η Μόρφου επιστρέφεται υπό ελληνοκυπριακή διοίκηση",
        "plus_morphou_karpasia_yialousa": "η Μόρφου, το Ριζοκάρπασο και η Γιαλούσα επιστρέφονται υπό ελληνοκυπριακή διοίκηση",
        "plus_old_morphou_karpasia_yialousa": "η παλιά Μόρφου, το Ριζοκάρπασο και η Γιαλούσα επιστρέφονται υπό ελληνοκυπριακή διοίκηση",
        "morphou_north_karpasia_federal_areas": "η Μόρφου και η Βόρεια Καρπασία γίνονται κοινά διοικούμενες Ομοσπονδιακές Περιοχές",
    },
    "compensation_property": {
        "comp_50000": "50.000 ευρώ κατά μέσο όρο στους χρήστες που χάνουν την περιουσία που χρησιμοποιούν σήμερα, βάσει δίκαιης εκτίμησης απώλειας από εμπειρογνώμονες του ΟΗΕ",
        "comp_150000": "150.000 ευρώ κατά μέσο όρο στους χρήστες που χάνουν την περιουσία που χρησιμοποιούν σήμερα, βάσει δίκαιης εκτίμησης απώλειας από εμπειρογνώμονες του ΟΗΕ",
        "comp_200000": "200.000 ευρώ κατά μέσο όρο στους χρήστες που χάνουν την περιουσία που χρησιμοποιούν σήμερα, βάσει δίκαιης εκτίμησης απώλειας από εμπειρογνώμονες του ΟΗΕ",
        "comp_300000": "300.000 ευρώ κατά μέσο όρο στους χρήστες που χάνουν την περιουσία που χρησιμοποιούν σήμερα, βάσει δίκαιης εκτίμησης απώλειας από εμπειρογνώμονες του ΟΗΕ",
        "comp_300000_housing": "300.000 ευρώ κατά μέσο όρο στους χρήστες που θα χάσουν περιουσία και εγγυημένη κατοικία οπουδήποτε στην Κύπρο",
    },
}


GC_TURKISH_LEVELS = {
    "compensation_property": {
        "comp_50000": "mülk sahiplerine, Kıbrıslı Rum Yerinden Edilmiş Kişilere (IDPs), BM uzmanlarının adil kayıp tahminine göre ortalama 50.000 Euro verir",
        "comp_150000": "mülk sahiplerine, Kıbrıslı Rum Yerinden Edilmiş Kişilere (IDPs), BM uzmanlarının adil kayıp tahminine göre ortalama 150.000 Euro verir",
        "comp_200000": "mülk sahiplerine, Kıbrıslı Rum Yerinden Edilmiş Kişilere (IDPs), BM uzmanlarının adil kayıp tahminine göre ortalama 200.000 Euro verir",
        "comp_300000": "mülk sahiplerine, Kıbrıslı Rum Yerinden Edilmiş Kişilere (IDPs), BM uzmanlarının adil kayıp tahminine göre ortalama 300.000 Euro verir",
        "comp_300000_housing": "mülk sahiplerine, Kıbrıslı Rum Yerinden Edilmiş Kişilere (IDPs), ortalama 300.000 Euro ve Kıbrıs'ın herhangi bir yerinde garantili konut verir",
    },
}


TC_TURKISH_LEVELS = {
    "territorial_arrangements": {
        "morphou_stays_tc": "Omorfo'nun Kıbrıs Türk yönetimi altında kalmasını içerir",
        "plus_morphou": "Omorfo'nun Kıbrıs Rum yönetimine iade edilmesini içerir",
        "plus_morphou_karpasia_yialousa": "Omorfo, Karpaz ve Yeni Erenköy'ün Kıbrıs Rum yönetimine iade edilmesini içerir",
        "plus_old_morphou_karpasia_yialousa": "eski Omorfo, Karpaz ve Yeni Erenköy'ün Kıbrıs Rum yönetimine iade edilmesini içerir",
        "morphou_north_karpasia_federal_areas": "Omorfo ve Kuzey Karpaz'ın ortak yönetilen Federal Bölgeler olmasını içerir",
    },
    "compensation_property": {
        "comp_50000": "halen kullandıkları mülkü kaybeden kullanıcılara, BM uzmanlarının adil kayıp tahminine göre ortalama 50.000 Euro verir",
        "comp_150000": "halen kullandıkları mülkü kaybeden kullanıcılara, BM uzmanlarının adil kayıp tahminine göre ortalama 150.000 Euro verir",
        "comp_200000": "halen kullandıkları mülkü kaybeden kullanıcılara, BM uzmanlarının adil kayıp tahminine göre ortalama 200.000 Euro verir",
        "comp_300000": "halen kullandıkları mülkü kaybeden kullanıcılara, BM uzmanlarının adil kayıp tahminine göre ortalama 300.000 Euro verir",
        "comp_300000_housing": "mülk kaybedecek kullanıcılara ortalama 300.000 Euro ve Kıbrıs'ın herhangi bir yerinde garantili konut verir",
    },
}


def narrative_level(language: str, group: str, attribute: str, level: str) -> str:
    if language == "English" and group == "GC":
        text = GC_ENGLISH_LEVELS.get(attribute, {}).get(level, LABELS[language][level])
    elif language == "English" and group == "TC":
        text = TC_ENGLISH_LEVELS.get(attribute, {}).get(level, LABELS[language][level])
    elif language == "Ελληνικά" and group == "GC":
        text = GC_GREEK_LEVELS.get(attribute, {}).get(level, LABELS[language][level])
    elif language == "Ελληνικά" and group == "TC":
        text = TC_GREEK_LEVELS.get(attribute, {}).get(level, LABELS[language][level])
    elif language == "Türkçe" and group == "GC":
        text = GC_TURKISH_LEVELS.get(attribute, {}).get(level, LABELS[language][level])
    elif language == "Türkçe" and group == "TC":
        text = TC_TURKISH_LEVELS.get(attribute, {}).get(level, LABELS[language][level])
    else:
        text = LABELS[language][level]

    if attribute == "territorial_arrangements":
        prefixes = {
            "English": "in addition to Varoshia and 50 villages returned under Greek Cypriot administration",
            "Ελληνικά": "επιπλέον της επιστροφής της Αμμοχώστου και 50 χωριών υπό ελληνοκυπριακή διοίκηση",
            "Türkçe": "Maraş ve 50 köyün Kıbrıs Rum yönetimine iadesine ek olarak",
        }
        prefix = prefixes.get(language)
        if not prefix:
            return text
        return f"{prefix}, {text}"

    return text


def package_narrative(language: str, group: str, package: dict[str, str], support: float) -> str:
    text = UI[language]
    parts = [text["package_intro"].format(support=pct(support))]

    for attribute in ATTRIBUTES:
        level = narrative_level(language, group, attribute, package[attribute])
        parts.append(text["package_parts"][attribute].format(level=level))

    return "; ".join(parts) + "."


def render_extreme_narratives(language: str) -> None:
    text = UI[language]
    gc_high, gc_high_package = find_extreme_package("GC", find_max=True)
    gc_low, gc_low_package = find_extreme_package("GC", find_max=False)
    tc_high, tc_high_package = find_extreme_package("TC", find_max=True)
    tc_low, tc_low_package = find_extreme_package("TC", find_max=False)

    narratives = [
        (text["highest_gc_heading"], package_narrative(language, "GC", gc_high_package, gc_high)),
        (text["lowest_gc_heading"], package_narrative(language, "GC", gc_low_package, gc_low)),
        (text["highest_tc_heading"], package_narrative(language, "TC", tc_high_package, tc_high)),
        (text["lowest_tc_heading"], package_narrative(language, "TC", tc_low_package, tc_low)),
    ]
    paragraphs = "\n".join(
        f"<h4>{heading}</h4><p>{paragraph}</p>"
        for heading, paragraph in narratives
    )

    st.markdown(
        f"""
        <section class="narrative-card">
            <div class="summary-title">{text["extremes_title"]}</div>
            <div class="narrative-text">{paragraphs}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def find_viable_packages(threshold: float = AGREEMENT_THRESHOLD) -> list[dict[str, object]]:
    viable = []

    for package in all_packages():
        gc_support = predict("GC", "forced", package)
        tc_support = predict("TC", "forced", package)
        joint_support = min(gc_support, tc_support)

        if gc_support >= threshold and tc_support >= threshold:
            viable.append(
                {
                    "package": package,
                    "gc_support": gc_support,
                    "tc_support": tc_support,
                    "joint_support": joint_support,
                }
            )

    return sorted(viable, key=lambda item: item["joint_support"], reverse=True)


def render_viable_packages(language: str) -> None:
    text = UI[language]
    viable = find_viable_packages()
    total = 4 * 5 * 5 * 4 * 4 * 5

    if not viable:
        content = f"<p>{text['viable_none']}</p>"
    else:
        rows = []
        for item in viable[:10]:
            package = item["package"]
            rows.append(
                "<li>"
                f"<strong>{text['joint_support']}: {whole_pct(item['joint_support'])}</strong>"
                f"<span>{text['gc_support']}: {whole_pct(item['gc_support'])} | {text['tc_support']}: {whole_pct(item['tc_support'])}</span>"
                f"<p>{package_sentence(language, package, include_attribute_names=True)}</p>"
                "</li>"
            )

        content = (
            f"<p>{text['viable_intro'].format(count=len(viable), total=total)}</p>"
            f"<ol class='viable-list'>{''.join(rows)}</ol>"
        )

    st.markdown(
        f"""
        <section class="narrative-card">
            <div class="summary-title">{text["viable_title"]}</div>
            <div class="narrative-text">{content}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_project_information() -> None:
    st.markdown(
        """
        <section class="info-section">
            <h2>Survey information</h2>
            <p><strong>Greek Cypriot survey:</strong> Fieldwork was completed in the period 19/11/2024-19/01/2025 by the University Centre for Field Studies (N=800).</p>
            <p><strong>Turkish Cypriot survey:</strong> Fieldwork was completed in the period 26/09/2025-17/10/2025 by Lipa Consultancy (N=813).</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    logo_left, logo_middle, logo_right = st.columns([2, 1, 2])
    with logo_left:
        if INCPEACE_LOGO.exists():
            st.image(str(INCPEACE_LOGO), width=245)
    with logo_right:
        if LSE_HELLENIC_LOGO.exists():
            st.image(str(LSE_HELLENIC_LOGO), width=130)

    st.markdown(
        """
        <section class="team-section">
            <h2>Research Team</h2>
            <p><strong>Charis Psaltis (PI of Green Transition)</strong> — University of Cyprus</p>
            <p><strong>Neophytos Loizides (co-PI of Inclusive Peace)</strong> — University of Warwick</p>
            <p><strong>Nikandros Ioannides (Conceptualisation of tool)</strong> — Cyprus University of Technology</p>
            <p><strong>Edward Morgan-Jones</strong> — University of Kent</p>
            <p><strong>Laura Sudulich</strong> — University of Essex</p>
            <p><strong>Andreas Michael</strong> — University of Cyprus</p>
            <p><strong>Allison McCulloch (Co-PI of Inclusive Peace)</strong> — Brandon University</p>
            <p><strong>Ilke Dagli</strong> — Centre for Sustainable Peace and Democratic Development (SeeD)</p>
            <p><strong>Eliz Tefik</strong> — Lipa Consultancy</p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_logo_header() -> None:
    if not GSP_LOGO.exists() and not UCFS_LOGO.exists():
        return

    st.markdown("<div class='logo-safe-space'></div>", unsafe_allow_html=True)
    left_logo, spacer, right_logo = st.columns([1, 4, 1])

    with left_logo:
        if GSP_LOGO.exists():
            st.image(str(GSP_LOGO), width=135)

    with right_logo:
        if UCFS_LOGO.exists():
            st.image(str(UCFS_LOGO), width=135)


st.markdown(
    """
    <style>
    .block-container {
        max-width: 1320px;
        padding-top: 2.8rem;
    }
    .logo-safe-space {
        height: 1.4rem;
    }
    h1 {
        font-size: 2.75rem !important;
        font-weight: 500 !important;
        margin: 0.35rem 0 2.2rem 0 !important;
        text-align: center;
    }
    [data-testid="stSidebar"] {
        background: #f4f5f7;
        border-right: 1px solid #dedede;
    }
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] label {
        color: #1f2933;
        font-weight: 700 !important;
    }
    .kpi-card {
        min-height: 92px;
        border: 1px solid #d8e2ef;
        border-radius: 8px;
        padding: 1rem 1.15rem;
        background: #f8fbff;
    }
    .kpi-label {
        color: #334155;
        font-size: 0.82rem;
        letter-spacing: 0.06em;
        line-height: 1.25;
        text-transform: uppercase;
    }
    .kpi-value {
        color: #07355f;
        font-size: 1.75rem;
        font-weight: 750;
        line-height: 1.1;
        margin-top: 0.35rem;
    }
    .agreement-status {
        display: grid;
        grid-template-columns: auto minmax(220px, 1fr) auto;
        align-items: center;
        gap: 1rem;
        border: 1px solid #d8dee4;
        border-left-width: 6px;
        border-radius: 8px;
        padding: 1rem 1.15rem;
        margin: 1rem 0 0.35rem 0;
        background: #ffffff;
    }
    .agreement-status-success {
        border-left-color: #1f9d55;
        background: #f6fcf8;
    }
    .agreement-status-progress {
        border-left-color: #c28a13;
        background: #fffaf0;
    }
    .agreement-symbol {
        display: grid;
        place-items: center;
        width: 3.15rem;
        height: 3.15rem;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.74);
        font-size: 1.75rem;
        line-height: 1;
    }
    .agreement-title {
        color: #17212b;
        font-size: 1.16rem;
        font-weight: 760;
        line-height: 1.25;
    }
    .agreement-body {
        color: #475569;
        font-size: 0.96rem;
        line-height: 1.4;
        margin-top: 0.18rem;
    }
    .agreement-badges {
        display: flex;
        flex-wrap: wrap;
        justify-content: flex-end;
        gap: 0.45rem;
    }
    .agreement-badge {
        border: 1px solid #d8dee4;
        border-radius: 999px;
        padding: 0.42rem 0.65rem;
        background: #ffffff;
        color: #334155;
        font-size: 0.86rem;
        font-weight: 700;
        line-height: 1.15;
        white-space: nowrap;
    }
    .agreement-badge-passed {
        border-color: #a9d7b8;
        color: #166534;
    }
    .agreement-badge-below_target {
        border-color: #f0cf83;
        color: #8a5b00;
    }
    .culprit-card {
        border: 1px solid #e4d6b2;
        border-radius: 8px;
        padding: 1rem 1.15rem;
        margin: 0.65rem 0 0.35rem 0;
        background: #fffdf7;
    }
    .culprit-title {
        color: #17212b;
        font-size: 1.04rem;
        font-weight: 760;
        line-height: 1.3;
    }
    .culprit-body,
    .culprit-impact {
        color: #475569;
        font-size: 0.96rem;
        line-height: 1.45;
        margin-top: 0.38rem;
    }
    .culprit-impact {
        color: #334155;
    }
    .result-card {
        min-height: 275px;
        height: 275px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        border: 1px solid #d8dee4;
        border-radius: 8px;
        padding: 1.55rem 1.55rem;
        margin: 0 0 1rem 0;
        background: #ffffff;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }
    .community-name {
        font-size: 1.45rem;
        line-height: 1.25;
        color: #17212b;
        margin-bottom: 0.25rem;
    }
    .sample-line {
        color: #657282;
        font-size: 0.92rem;
        margin-bottom: 1rem;
    }
    .metric-single {
        max-width: 520px;
    }
    .metric-label {
        color: #2a3542;
        min-height: 2.7rem;
        font-size: 1rem;
        line-height: 1.35;
    }
    .metric-value {
        font-size: 2.7rem;
        font-weight: 650;
        color: #0f2537;
        margin-top: 0.2rem;
    }
    .method-note {
        color: #4b5563;
        font-size: 0.95rem;
        line-height: 1.45;
        max-width: 920px;
        margin-top: 0.8rem;
    }
    .summary-card {
        border: 1px solid #d8dee4;
        border-radius: 8px;
        background: #ffffff;
        padding: 1.35rem 1.45rem;
        margin-top: 1.1rem;
    }
    .narrative-card {
        border: 1px solid #d8dee4;
        border-radius: 8px;
        background: #ffffff;
        padding: 1.35rem 1.45rem;
        margin-top: 1.1rem;
    }
    .summary-title {
        color: #111827;
        font-size: 1.25rem;
        font-weight: 700;
        line-height: 1.25;
    }
    .summary-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 0.75rem;
        font-size: 0.98rem;
    }
    .summary-table td {
        border-top: 1px solid #e5e7eb;
        color: #111827;
        padding: 0.55rem 0.25rem;
    }
    .summary-table td:last-child {
        font-weight: 700;
        text-align: right;
    }
    .narrative-text {
        color: #344154;
        font-size: 0.98rem;
        line-height: 1.55;
        margin-top: 0.75rem;
    }
    .narrative-text h4 {
        color: #17212b;
        font-size: 1.02rem;
        font-weight: 750;
        line-height: 1.35;
        margin: 1rem 0 0.3rem 0;
    }
    .narrative-text h4:first-child {
        margin-top: 0;
    }
    .narrative-text p {
        margin: 0 0 0.85rem 0;
    }
    .narrative-text p:last-child {
        margin-bottom: 0;
    }
    .viable-list {
        margin: 0.75rem 0 0 1.25rem;
        padding: 0;
    }
    .viable-list li {
        padding: 0.35rem 0 0.7rem 0;
    }
    .viable-list span {
        display: block;
        color: #526173;
        font-size: 0.92rem;
        margin-top: 0.15rem;
    }
    .viable-list p {
        margin: 0.2rem 0 0 0;
    }
    .info-section,
    .team-section {
        margin-top: 2.4rem;
        padding-top: 1.35rem;
        border-top: 1px solid #e3e8ef;
        color: #0f2537;
    }
    .info-section h2,
    .team-section h2 {
        color: #07355f;
        font-size: 1.75rem;
        font-weight: 500;
        line-height: 1.25;
        margin: 0 0 1rem 0;
        text-align: center;
    }
    .info-section p,
    .team-section p {
        font-size: 1rem;
        line-height: 1.45;
        margin: 0 0 0.8rem 0;
    }
    .team-section {
        margin-bottom: 2.5rem;
    }
    @media (max-width: 860px) {
        .agreement-status {
            grid-template-columns: auto 1fr;
        }
        .agreement-badges {
            grid-column: 1 / -1;
            justify-content: flex-start;
        }
        .agreement-badge {
            white-space: normal;
        }
        h1 {
            font-size: 1.8rem !important;
            text-align: left;
        }
        .result-card {
            height: auto;
            min-height: 245px;
        }
        .metric-value {
            font-size: 1.85rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


language = st.sidebar.selectbox("Language / Γλώσσα / Dil", list(UI.keys()))
text = UI[language]
enable_sounds = st.sidebar.toggle(text_value(text, "sound_toggle", "Enable sound cues"), value=True)

render_logo_header()
st.title(text["title"])

st.sidebar.header(text["package"])
selected_levels = {}

for attribute in ATTRIBUTES:
    selected_levels[attribute] = st.sidebar.selectbox(
        text["attributes"][attribute],
        LEVELS[attribute],
        index=LEVELS[attribute].index(DEFAULT_PACKAGE[attribute]),
        format_func=lambda level, lang=language: LABELS[lang][level],
        key=attribute,
    )

gc_support = predict("GC", "forced", selected_levels)
tc_support = predict("TC", "forced", selected_levels)
joint_support = min(gc_support, tc_support)

kpi_left, kpi_mid, kpi_right = st.columns([1, 1, 1], gap="large")

with kpi_left:
    render_kpi_card(text["gc_support"], gc_support)

with kpi_mid:
    render_kpi_card(text["joint_support"], joint_support)

with kpi_right:
    render_kpi_card(text["tc_support"], tc_support)

shared_success = render_agreement_status(text, gc_support, tc_support)
current_agreement_state = "success" if shared_success else "failure"
previous_agreement_state = st.session_state.get("agreement_sound_state")
if enable_sounds and previous_agreement_state is not None and previous_agreement_state != current_agreement_state:
    play_agreement_tone(current_agreement_state)
st.session_state.agreement_sound_state = current_agreement_state
if not shared_success:
    render_culprit_feedback(language, selected_levels, gc_support, tc_support)

st.markdown("<div style='height: 0.75rem;'></div>", unsafe_allow_html=True)
st.subheader(text["results_title"])
left, right = st.columns([1, 1], gap="large")

with left:
    render_result_card("GC", language, selected_levels, gc_support)

with right:
    render_result_card("TC", language, selected_levels, tc_support)

render_summary_table(text, gc_support, tc_support)
render_extreme_narratives(language)
render_viable_packages(language)
render_project_information()

st.markdown(f"<p class='method-note'>{text['method_note']}</p>", unsafe_allow_html=True)



