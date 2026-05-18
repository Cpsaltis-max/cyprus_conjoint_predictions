import base64
import html
import io
import math
import subprocess
import struct
import sys
import textwrap
import urllib.parse
import wave
from itertools import product
from pathlib import Path

import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import PIL


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
SOUND_FILES = {
    "success": Path("sounds/success.mp3"),
    "failure": Path("sounds/failure.mp3"),
}


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


ATTRIBUTE_COLORS = {
    "political_structure": "#ef4444",
    "territorial_arrangements": "#f59e0b",
    "compensation_property": "#10b981",
    "security_guarantees": "#3b82f6",
    "judicial_system": "#8b5cf6",
    "energy_cooperation": "#06b6d4",
}


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
        "agreement_success_detail": "This is one of 118 possible combinations out of 8,000 that can be accepted by at least 55% of voters in both communities in a referendum. At the bottom of the page, you can see the 10 most popular combinations.",
        "agreement_progress_title": "Keep negotiating",
        "agreement_progress_body": "The goal is 55% or higher predicted support in both communities.",
        "language_hint": "Choose your language (English, Ελληνικά, Türkçe)",
        "options": "Options",
        "ready_title": "Ready to test the package?",
        "ready_body": "When your selections are set, check whether the package reaches the 55% acceptability goal in both communities.",
        "package_instruction": 'Select one option from each attribute to build your solution package and then press the button "Check acceptability".',
        "check_acceptability": "Check acceptability",
        "select_option_placeholder": "Choose an option",
        "select_all_warning": "Please select one option from each attribute before checking acceptability.",
        "try_again": "Try again",
        "share_success_title": "Share your discovery",
        "share_success_text": "I discovered one of the 118 variations of the Guterres framework that can be accepted by both communities!",
        "download_success_image": "Download success image",
        "share_on_facebook": "Share on Facebook",
        "share_on_x": "Share on X",
        "research_method_note": 'The app is based on an experimental method called "conjoint survey experiment". In previous published research of our team (<a href="https://journals.sagepub.com/doi/10.1177/00220027221108221" target="_blank" rel="noopener noreferrer">read the article</a>) this method was applied to identify possible “zones of agreement” between Greek Cypriots and Turkish Cypriots on a future peace settlement. Representative samples from both communities were shown pairs of hypothetical peace packages and asked to choose between them. Each package varied across five key attributes: federal executive, territorial readjustments, property compensation, implementation/security monitoring, and Supreme Court composition. By randomly varying these attributes, the method estimates which elements increase or decrease public support. The analysis uses a binary outcome, whether a package was preferred, and estimates marginal effects to reveal both community divergences and potential compromise positions.',
        "bottleneck_title": "Likely bottleneck to explore",
        "below_target_sentence": "{community} is below target.",
        "current_choice_sentence": "The current choice is {choice}.",
        "try_attribute_sentence": "Try an alternative {attribute} option.",
        "try_attributes_sentence": "Try alternatives in these attributes: {attributes}.",
        "bottleneck_impact": "These look like the most promising attributes to experiment with next.",
        "no_bottleneck_title": "No single clear bottleneck found",
        "no_bottleneck_body": "Try changing a combination of attributes. A single attribute switch does not clearly move the package toward 55% in the community or communities below target.",
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

UI["Ελληνικά"].update(
    {
        "language_hint": "Επιλέξτε γλώσσα (English, Ελληνικά, Türkçe)",
        "options": "Επιλογές",
        "ready_title": "Έτοιμοι να ελέγξετε το πακέτο;",
        "ready_body": "Όταν ολοκληρώσετε τις επιλογές σας, ελέγξτε αν το πακέτο φτάνει τον στόχο αποδοχής 55% και στις δύο κοινότητες.",
        "package_instruction": 'Επιλέξτε μία επιλογή από κάθε χαρακτηριστικό για να διαμορφώσετε το πακέτο λύσης σας και μετά πατήστε το κουμπί "Έλεγχος αποδοχής".',
        "check_acceptability": "Έλεγχος αποδοχής",
        "select_option_placeholder": "Επιλέξτε επιλογή",
        "select_all_warning": "Παρακαλώ επιλέξτε μία επιλογή από κάθε χαρακτηριστικό πριν ελέγξετε την αποδοχή.",
        "try_again": "Προσπαθήστε ξανά",
        "share_success_title": "Μοιραστείτε την ανακάλυψή σας",
        "share_success_text": "Ανακάλυψα μία από τις 118 παραλλαγές του πλαισίου Γκουτέρες που μπορούν να γίνουν αποδεκτές και από τις δύο κοινότητες!",
        "download_success_image": "Λήψη εικόνας επιτυχίας",
        "share_on_facebook": "Κοινοποίηση στο Facebook",
        "share_on_x": "Κοινοποίηση στο X",
        "research_method_note": 'Η εφαρμογή βασίζεται σε μια πειραματική μέθοδο που ονομάζεται "πείραμα conjoint survey". Σε προηγούμενη δημοσιευμένη έρευνα της ομάδας μας (<a href="https://journals.sagepub.com/doi/10.1177/00220027221108221" target="_blank" rel="noopener noreferrer">διαβάστε το άρθρο</a>) η μέθοδος αυτή εφαρμόστηκε για να εντοπιστούν πιθανές “ζώνες συμφωνίας” ανάμεσα σε Ελληνοκύπριους και Τουρκοκύπριους για μια μελλοντική ειρηνευτική διευθέτηση. Αντιπροσωπευτικά δείγματα και από τις δύο κοινότητες είδαν ζεύγη υποθετικών πακέτων λύσης και κλήθηκαν να επιλέξουν ανάμεσά τους. Κάθε πακέτο διέφερε σε πέντε βασικά χαρακτηριστικά: ομοσπονδιακή εκτελεστική εξουσία, εδαφικές αναπροσαρμογές, αποζημίωση περιουσιών, παρακολούθηση εφαρμογής και ασφάλειας, και σύνθεση του Ανώτατου Δικαστηρίου. Με την τυχαία διαφοροποίηση αυτών των χαρακτηριστικών, η μέθοδος εκτιμά ποια στοιχεία αυξάνουν ή μειώνουν τη δημόσια στήριξη. Η ανάλυση χρησιμοποιεί ένα δυαδικό αποτέλεσμα, δηλαδή αν ένα πακέτο προτιμήθηκε, και εκτιμά οριακές επιδράσεις για να αναδείξει τόσο τις αποκλίσεις μεταξύ των κοινοτήτων όσο και πιθανές θέσεις συμβιβασμού.',
        "bottleneck_title": "Πιθανό σημείο προς διερεύνηση",
        "below_target_sentence": "Η {community} είναι κάτω από τον στόχο.",
        "current_choice_sentence": "Η τρέχουσα επιλογή είναι {choice}.",
        "try_attribute_sentence": "Δοκιμάστε μια εναλλακτική επιλογή στο χαρακτηριστικό {attribute}.",
        "try_attributes_sentence": "Δοκιμάστε εναλλακτικές επιλογές στα εξής χαρακτηριστικά: {attributes}.",
        "bottleneck_impact": "Αυτά φαίνεται να είναι τα πιο υποσχόμενα χαρακτηριστικά για να πειραματιστείτε στη συνέχεια.",
        "no_bottleneck_title": "Δεν βρέθηκε ένα σαφές μοναδικό εμπόδιο",
        "no_bottleneck_body": "Δοκιμάστε να αλλάξετε συνδυασμό χαρακτηριστικών. Μια αλλαγή σε ένα μόνο χαρακτηριστικό δεν φαίνεται να φέρνει καθαρά το πακέτο πιο κοντά στο 55%.",
        "agreement_success_title": "Επιτεύχθηκε κοινή αποδοχή",
        "agreement_success_body": "Αυτό το πακέτο φτάνει τουλάχιστον 55% προβλεπόμενη στήριξη και στις δύο κοινότητες.",
        "agreement_success_detail": "Αυτός είναι ένας από τους 118 πιθανούς συνδυασμούς από σύνολο 8.000 που μπορούν να γίνουν αποδεκτοί από τουλάχιστον 55% των ψηφοφόρων και στις δύο κοινότητες σε δημοψήφισμα. Στο τέλος της σελίδας μπορείτε να δείτε τους 10 πιο δημοφιλείς συνδυασμούς.",
        "agreement_progress_title": "Συνεχίστε τη διαπραγμάτευση",
        "agreement_progress_body": "Ο στόχος είναι 55% ή υψηλότερη προβλεπόμενη στήριξη και στις δύο κοινότητες.",
        "passed": "Πέρασε",
        "below_target": "Κάτω από τον στόχο",
    }
)

UI["Türkçe"].update(
    {
        "language_hint": "Dilinizi seçin (English, Ελληνικά, Türkçe)",
        "options": "Seçenekler",
        "ready_title": "Paketi test etmeye hazır mısınız?",
        "ready_body": "Seçimleriniz hazır olduğunda, paketin iki toplumda da %55 kabul edilebilirlik hedefine ulaşıp ulaşmadığını kontrol edin.",
        "package_instruction": '"Kabul edilebilirliği kontrol et" düğmesine basmadan önce her özellikten bir seçenek seçerek çözüm paketinizi oluşturun.',
        "check_acceptability": "Kabul edilebilirliği kontrol et",
        "select_option_placeholder": "Bir seçenek seçin",
        "select_all_warning": "Kabul edilebilirliği kontrol etmeden önce her özellikten bir seçenek seçin.",
        "try_again": "Tekrar deneyin",
        "share_success_title": "Keşfinizi paylaşın",
        "share_success_text": "Guterres çerçevesinin iki toplum tarafından kabul edilebilecek 118 varyasyonundan birini keşfettim!",
        "download_success_image": "Başarı görselini indir",
        "share_on_facebook": "Facebook'ta paylaş",
        "share_on_x": "X'te paylaş",
        "research_method_note": 'Bu uygulama "conjoint survey experiment" adı verilen deneysel bir yönteme dayanmaktadır. Ekibimizin daha önce yayımlanan araştırmasında (<a href="https://journals.sagepub.com/doi/10.1177/00220027221108221" target="_blank" rel="noopener noreferrer">makaleyi okuyun</a>) bu yöntem, Kıbrıslı Rumlar ve Kıbrıslı Türkler arasında gelecekteki bir barış anlaşmasına ilişkin olası “uzlaşma alanlarını” belirlemek için uygulanmıştır. Her iki toplumdan temsili örneklemlere varsayımsal barış paketlerinden oluşan ikili seçenekler gösterilmiş ve aralarından birini seçmeleri istenmiştir. Her paket beş temel özellik bakımından değişmiştir: federal yürütme, toprak düzenlemeleri, mülkiyet tazminatı, uygulama/güvenlik izlemesi ve Yüksek Mahkeme bileşimi. Bu özellikleri rastgele değiştirerek yöntem, hangi unsurların kamu desteğini artırdığını veya azalttığını tahmin eder. Analiz, bir paketin tercih edilip edilmediğini gösteren ikili bir sonuç kullanır ve hem toplumlar arası ayrışmaları hem de olası uzlaşma pozisyonlarını ortaya koymak için marjinal etkileri tahmin eder.',
        "bottleneck_title": "Keşfedilecek olası darboğaz",
        "below_target_sentence": "{community} hedefin altında.",
        "current_choice_sentence": "Mevcut seçim {choice}.",
        "try_attribute_sentence": "{attribute} için alternatif bir seçenek deneyin.",
        "try_attributes_sentence": "Şu özelliklerde alternatif seçenekleri deneyin: {attributes}.",
        "bottleneck_impact": "Bir sonraki deneme için en umut verici özellikler bunlar gibi görünüyor.",
        "no_bottleneck_title": "Tek bir belirgin darboğaz bulunamadı",
        "no_bottleneck_body": "Özelliklerin bir kombinasyonunu değiştirmeyi deneyin. Tek bir özellik değişikliği paketi hedefe açık biçimde yaklaştırmıyor.",
        "agreement_success_title": "Ortak kabul sağlandı",
        "agreement_success_body": "Bu paket iki toplumda da en az %55 tahmini desteğe ulaşıyor.",
        "agreement_success_detail": "Bu, referandumda her iki toplumdaki seçmenlerin en az %55'i tarafından kabul edilebilecek 8.000 olası kombinasyon içindeki 118 kombinasyondan biridir. Sayfanın sonunda en popüler 10 kombinasyonu görebilirsiniz.",
        "agreement_progress_title": "Müzakereye devam edin",
        "agreement_progress_body": "Hedef, iki toplumda da %55 veya daha yüksek tahmini destektir.",
        "passed": "Geçti",
        "below_target": "Hedefin altında",
    }
)


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


def level_label(language: str, level: str) -> str:
    return LABELS.get(language, {}).get(level, level)


def support_status(value: float) -> str:
    return "passed" if value >= AGREEMENT_THRESHOLD else "below_target"


def play_agreement_tone(kind: str) -> None:
    if kind not in {"success", "failure"}:
        return

    sound_path = SOUND_FILES[kind]
    if sound_path.exists():
        encoded = base64.b64encode(sound_path.read_bytes()).decode("ascii")
        st.markdown(
            f"""
            <audio autoplay style="display:none">
                <source src="data:audio/mpeg;base64,{encoded}" type="audio/mpeg">
            </audio>
            """,
            unsafe_allow_html=True,
        )
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
    detail = text_value(text, "agreement_success_detail", "") if success else ""
    detail_html = f"<div class='agreement-detail'>{detail}</div>" if detail else ""
    gc_status = support_status(gc_support)
    tc_status = support_status(tc_support)
    passed = text_value(text, "passed", "Passed")
    below_target = text_value(text, "below_target", "Below target")
    gc_mark = "&#10003;" if gc_status == "passed" else "&#9679;"
    tc_mark = "&#10003;" if tc_status == "passed" else "&#9679;"
    gc_text = passed if gc_status == "passed" else below_target
    tc_text = passed if tc_status == "passed" else below_target

    st.markdown(
        f"<section class='agreement-status agreement-status-{status_class}'>"
        f"<div class='agreement-symbol'>{icon}</div>"
        "<div class='agreement-copy'>"
        f"<div class='agreement-title'>{title}</div>"
        f"<div class='agreement-body'>{body}</div>"
        f"{detail_html}"
        "</div>"
        "<div class='agreement-badges'>"
        f"<span class='agreement-badge agreement-badge-{gc_status}'>{text['gc_support']}: {whole_pct(gc_support)} - {gc_mark} {gc_text}</span>"
        f"<span class='agreement-badge agreement-badge-{tc_status}'>{text['tc_support']}: {whole_pct(tc_support)} - {tc_mark} {tc_text}</span>"
        "</div>"
        "</section>",
        unsafe_allow_html=True,
    )
    return success


def create_success_package_svg(language: str, selected: dict[str, str], gc_support: float, tc_support: float) -> bytes:
    text = UI[language]
    width = 1080
    row_height = 92
    top_height = 250
    bottom_height = 180
    height = top_height + row_height * len(ATTRIBUTES) + bottom_height
    joint_support = min(gc_support, tc_support)
    headline = text_value(
        text,
        "share_success_text",
        "I discovered one of the 118 variations of the Guterres framework that can be accepted by both communities!",
    )

    def svg_text_lines(content: str, x: int, y: int, size: int, color: str, weight: int = 400, max_chars: int = 64) -> str:
        lines = textwrap.wrap(content, width=max_chars)
        return "".join(
            f'<text x="{x}" y="{y + index * int(size * 1.35)}" font-size="{size}" font-weight="{weight}" fill="{color}">{html.escape(line)}</text>'
            for index, line in enumerate(lines)
        )

    rows = []
    y = top_height
    for attribute in ATTRIBUTES:
        color = ATTRIBUTE_COLORS[attribute]
        attribute_name = text["attributes"][attribute]
        level_name = level_label(language, selected[attribute])
        rows.append(
            f'<rect x="70" y="{y}" width="940" height="72" rx="18" fill="{color}" opacity="0.12"/>'
            f'<rect x="70" y="{y}" width="10" height="72" rx="5" fill="{color}"/>'
            f'<circle cx="108" cy="{y + 36}" r="13" fill="{color}"/>'
            f'<text x="135" y="{y + 30}" font-size="25" font-weight="800" fill="#17212b">{html.escape(attribute_name)}</text>'
            f'<text x="135" y="{y + 58}" font-size="19" fill="#475569">{html.escape(level_name[:92])}</text>'
        )
        y += row_height

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
        '<rect width="100%" height="100%" fill="#f8fbff"/>'
        '<circle cx="80" cy="80" r="150" fill="#e0f2fe"/>'
        '<circle cx="990" cy="110" r="120" fill="#fef3c7"/>'
        '<circle cx="930" cy="930" r="180" fill="#ede9fe"/>'
        '<text x="70" y="78" font-size="48" font-weight="850" fill="#0f2537">55%+ ✓</text>'
        f'{svg_text_lines(headline, 70, 132, 29, "#17212b", 760, 58)}'
        f'<text x="70" y="220" font-size="24" font-weight="760" fill="#166534">{html.escape(text["gc_support"])}: {whole_pct(gc_support)}</text>'
        f'<text x="405" y="220" font-size="24" font-weight="760" fill="#0f2537">{html.escape(text["joint_support"])}: {whole_pct(joint_support)}</text>'
        f'<text x="725" y="220" font-size="24" font-weight="760" fill="#166534">{html.escape(text["tc_support"])}: {whole_pct(tc_support)}</text>'
        f'{"".join(rows)}'
        f'<text x="70" y="{height - 92}" font-size="26" font-weight="800" fill="#0f2537">Cyprus Conjoint Predictions</text>'
        f'<text x="70" y="{height - 52}" font-size="22" fill="#475569">https://cyprusconjointpredictions-knbomutrnxm22cyulm9bjq.streamlit.app/</text>'
        '</svg>'
    )
    return svg.encode("utf-8")


def image_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    pil_fonts_dir = Path(PIL.__file__).resolve().parent / "fonts"
    font_name = "DejaVu Sans:style=Bold" if bold else "DejaVu Sans"
    fontconfig_path = ""
    try:
        fontconfig = subprocess.run(
            ["fc-match", "-f", "%{file}", font_name],
            check=False,
            capture_output=True,
            text=True,
            timeout=1,
        )
        fontconfig_path = fontconfig.stdout.strip()
    except Exception:
        fontconfig_path = ""

    matplotlib_font = ""
    try:
        from matplotlib import font_manager

        matplotlib_font = font_manager.findfont("DejaVu Sans", fallback_to_default=True)
    except Exception:
        matplotlib_font = ""

    discovered_fonts = []
    for root in [
        Path("/usr/share/fonts"),
        Path("/usr/local/share/fonts"),
        Path(sys.prefix) / "lib",
        Path.home() / ".fonts",
    ]:
        if root.exists():
            discovered_fonts.extend(str(path) for path in root.rglob("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"))
            discovered_fonts.extend(str(path) for path in root.rglob("NotoSans-Bold.ttf" if bold else "NotoSans-Regular.ttf"))
            discovered_fonts.extend(str(path) for path in root.rglob("LiberationSans-Bold.ttf" if bold else "LiberationSans-Regular.ttf"))

    candidates = (
        [
            "DejaVuSans-Bold.ttf",
            "Arial Bold.ttf",
            fontconfig_path,
            matplotlib_font,
            r"C:\Windows\Fonts\segoeuib.ttf",
            r"C:\Windows\Fonts\arialbd.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
            str(pil_fonts_dir / "DejaVuSans-Bold.ttf"),
            *discovered_fonts,
        ]
        if bold
        else [
            "DejaVuSans.ttf",
            "Arial.ttf",
            fontconfig_path,
            matplotlib_font,
            r"C:\Windows\Fonts\segoeui.ttf",
            r"C:\Windows\Fonts\arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
            str(pil_fonts_dir / "DejaVuSans.ttf"),
            *discovered_fonts,
        ]
    )
    for candidate in candidates:
        if not candidate:
            continue
        if Path(candidate).exists() or not any(sep in candidate for sep in ("\\", "/")):
            try:
                return ImageFont.truetype(candidate, size)
            except OSError:
                continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def wrapped_lines(draw: ImageDraw.ImageDraw, content: str, font_obj: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in str(content).splitlines() or [""]:
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        current = ""
        for word in words:
            test = f"{current} {word}".strip()
            if draw.textbbox((0, 0), test, font=font_obj)[2] <= max_width or not current:
                current = test
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
    return lines


def draw_wrapped_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    content: str,
    font_obj: ImageFont.FreeTypeFont,
    fill: str,
    max_width: int,
    line_spacing: int = 8,
) -> int:
    x, y = xy
    for line in wrapped_lines(draw, content, font_obj, max_width):
        draw.text((x, y), line, font=font_obj, fill=fill)
        bbox = draw.textbbox((x, y), line, font=font_obj)
        y += (bbox[3] - bbox[1]) + line_spacing
    return y


def create_success_package_png(language: str, selected: dict[str, str], gc_support: float, tc_support: float) -> bytes:
    text = UI[language]
    width = 1080
    top_height = 500
    bottom_height = 230
    joint_support = min(gc_support, tc_support)
    headline = text_value(
        text,
        "share_success_text",
        "I discovered one of the 118 variations of the Guterres framework that can be accepted by both communities!",
    )

    probe = Image.new("RGB", (width, 200), "#f8fbff")
    probe_draw = ImageDraw.Draw(probe)
    title_font = image_font(86, True)
    headline_font = image_font(48, True)
    metric_font = image_font(38, True)
    attr_font = image_font(46, True)
    level_font = image_font(38)
    footer_font = image_font(30)
    row_specs = []
    for attribute in ATTRIBUTES:
        attribute_name = text["attributes"][attribute]
        level_name = level_label(language, selected[attribute])
        attr_lines = wrapped_lines(probe_draw, attribute_name, attr_font, 730)
        level_lines = wrapped_lines(probe_draw, level_name, level_font, 730)
        row_height = max(190, 64 + len(attr_lines) * 58 + len(level_lines) * 50)
        row_specs.append((attribute, attr_lines, level_lines, row_height))

    height = top_height + sum(row[3] + 18 for row in row_specs) + bottom_height
    image = Image.new("RGB", (width, height), "#f8fbff")
    draw = ImageDraw.Draw(image)
    draw.ellipse((-135, -95, 280, 320), fill="#e0f2fe")
    draw.ellipse((835, -30, 1125, 260), fill="#fef3c7")
    draw.ellipse((805, height - 380, 1215, height + 30), fill="#ede9fe")

    draw.text((70, 70), "55%+ OK", font=title_font, fill="#0f2537")
    headline_end_y = draw_wrapped_text(draw, (70, 185), headline, headline_font, "#17212b", 940, 16)
    metrics_y = max(375, headline_end_y + 28)
    draw.text((70, metrics_y), f"{text['gc_support']}: {whole_pct(gc_support)}", font=metric_font, fill="#166534")
    draw.text((70, metrics_y + 52), f"{text['joint_support']}: {whole_pct(joint_support)}", font=metric_font, fill="#0f2537")
    draw.text((560, metrics_y + 52), f"{text['tc_support']}: {whole_pct(tc_support)}", font=metric_font, fill="#166534")

    y = top_height
    for attribute, attr_lines, level_lines, row_height in row_specs:
        color = ATTRIBUTE_COLORS[attribute]
        draw.rounded_rectangle((70, y, 1010, y + row_height), radius=24, fill="#ffffff", outline="#d8e2ef", width=3)
        draw.rounded_rectangle((70, y, 90, y + row_height), radius=9, fill=color)
        draw.ellipse((115, y + 38, 163, y + 86), fill=color)
        text_y = y + 34
        for line in attr_lines:
            draw.text((190, text_y), line, font=attr_font, fill="#17212b")
            text_y += 58
        text_y += 10
        for line in level_lines:
            draw.text((190, text_y), line, font=level_font, fill="#475569")
            text_y += 50
        y += row_height + 24

    draw.text((70, height - 125), "Cyprus Conjoint Predictions", font=image_font(42, True), fill="#0f2537")
    draw.text((70, height - 68), "cyprusconjointpredictions.streamlit.app", font=footer_font, fill="#475569")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def render_success_share_panel(language: str, selected: dict[str, str], gc_support: float, tc_support: float) -> None:
    text = UI[language]
    share_text = text_value(
        text,
        "share_success_text",
        "I discovered one of the 118 variations of the Guterres framework that can be accepted by both communities!",
    )
    app_url = "https://cyprusconjointpredictions-knbomutrnxm22cyulm9bjq.streamlit.app/"
    encoded_url = urllib.parse.quote(app_url, safe="")
    encoded_text = urllib.parse.quote(f"{share_text} {app_url}", safe="")
    facebook_url = f"https://www.facebook.com/sharer/sharer.php?u={encoded_url}"
    x_url = f"https://twitter.com/intent/tweet?text={encoded_text}"
    image_bytes = create_success_package_png(language, selected, gc_support, tc_support)

    st.markdown(
        f"""
        <section class="share-card">
            <div class="share-title">{text_value(text, "share_success_title", "Share your discovery")}</div>
            <div class="share-text">{share_text}</div>
            <div class="share-actions">
                <a href="{facebook_url}" target="_blank" rel="noopener noreferrer">{text_value(text, "share_on_facebook", "Share on Facebook")}</a>
                <a href="{x_url}" target="_blank" rel="noopener noreferrer">{text_value(text, "share_on_x", "Share on X")}</a>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    st.download_button(
        text_value(text, "download_success_image", "Download success image"),
        image_bytes,
        file_name="cyprus-conjoint-success-package.png",
        mime="image/png",
        use_container_width=True,
    )


def diagnose_culprit_for_group(
    selected: dict[str, str],
    group: str,
    support: float,
    excluded_attributes: set[str] | None = None,
) -> dict[str, object] | None:
    baseline_gap = max(0.0, AGREEMENT_THRESHOLD - support)
    if baseline_gap <= 0:
        return None

    best: dict[str, object] | None = None
    excluded_attributes = excluded_attributes or set()

    for attribute in ATTRIBUTES:
        if attribute in excluded_attributes:
            continue
        current_level = selected[attribute]
        for candidate_level in LEVELS[attribute]:
            if candidate_level == current_level:
                continue

            candidate = dict(selected)
            candidate[attribute] = candidate_level
            candidate_gc = predict("GC", "forced", candidate)
            candidate_tc = predict("TC", "forced", candidate)
            candidate_support = candidate_gc if group == "GC" else candidate_tc
            gap_reduction = baseline_gap - max(0.0, AGREEMENT_THRESHOLD - candidate_support)
            joint_after = min(candidate_gc, candidate_tc)

            if best is None or (gap_reduction, candidate_support, joint_after) > (
                best["gap_reduction"],
                best["candidate_support"],
                best["joint_after"],
            ):
                best = {
                    "group": group,
                    "attribute": attribute,
                    "current_level": current_level,
                    "candidate_level": candidate_level,
                    "candidate_support": candidate_support,
                    "gc_after": candidate_gc,
                    "tc_after": candidate_tc,
                    "joint_after": joint_after,
                    "gap_reduction": gap_reduction,
                }

    if best and best["gap_reduction"] > 0:
        return best
    return None


def diagnose_culprits_for_group(
    selected: dict[str, str],
    group: str,
    support: float,
    excluded_attributes: set[str] | None = None,
    limit: int = 3,
) -> list[dict[str, object]]:
    baseline_gap = max(0.0, AGREEMENT_THRESHOLD - support)
    if baseline_gap <= 0:
        return []

    excluded_attributes = excluded_attributes or set()
    best_by_attribute: list[dict[str, object]] = []

    for attribute in ATTRIBUTES:
        if attribute in excluded_attributes:
            continue

        current_level = selected[attribute]
        best_for_attribute: dict[str, object] | None = None
        for candidate_level in LEVELS[attribute]:
            if candidate_level == current_level:
                continue

            candidate = dict(selected)
            candidate[attribute] = candidate_level
            candidate_gc = predict("GC", "forced", candidate)
            candidate_tc = predict("TC", "forced", candidate)
            candidate_support = candidate_gc if group == "GC" else candidate_tc
            gap_reduction = baseline_gap - max(0.0, AGREEMENT_THRESHOLD - candidate_support)
            joint_after = min(candidate_gc, candidate_tc)

            if best_for_attribute is None or (gap_reduction, candidate_support, joint_after) > (
                best_for_attribute["gap_reduction"],
                best_for_attribute["candidate_support"],
                best_for_attribute["joint_after"],
            ):
                best_for_attribute = {
                    "group": group,
                    "attribute": attribute,
                    "current_level": current_level,
                    "candidate_support": candidate_support,
                    "joint_after": joint_after,
                    "gap_reduction": gap_reduction,
                }

        if best_for_attribute and best_for_attribute["gap_reduction"] > 0:
            best_by_attribute.append(best_for_attribute)

    best_by_attribute.sort(
        key=lambda item: (item["gap_reduction"], item["candidate_support"], item["joint_after"]),
        reverse=True,
    )
    return best_by_attribute[:limit]


def render_culprit_feedback(language: str, selected: dict[str, str], gc_support: float, tc_support: float) -> None:
    gc_diagnostics = diagnose_culprits_for_group(selected, "GC", gc_support)
    excluded_for_tc = {item["attribute"] for item in gc_diagnostics[:1]} if gc_diagnostics and tc_support < AGREEMENT_THRESHOLD else set()
    tc_diagnostics = diagnose_culprits_for_group(selected, "TC", tc_support, excluded_for_tc)
    diagnostics_by_group = [("GC", gc_diagnostics), ("TC", tc_diagnostics)]
    text = UI[language]
    if not gc_diagnostics and not tc_diagnostics:
        st.markdown(
            "<section class='culprit-card'>"
            f"<div class='culprit-title'>&#128269; {text_value(text, 'no_bottleneck_title', 'No single clear bottleneck found')}</div>"
            f"<div class='culprit-body'>{text_value(text, 'no_bottleneck_body', 'Try changing a combination of attributes.')}</div>"
            "</section>",
            unsafe_allow_html=True,
        )
        return

    rows = []
    for group, diagnostics in diagnostics_by_group:
        if not diagnostics:
            continue
        group_name = text["gc"] if group == "GC" else text["tc"]
        current_choices = "; ".join(
            f"<strong>{text['attributes'][item['attribute']]}</strong>: {level_label(language, item['current_level'])}"
            for item in diagnostics
        )
        attribute_names = ", ".join(f"<strong>{text['attributes'][item['attribute']]}</strong>" for item in diagnostics)
        rows.append(
            "<div class='culprit-community-row'>"
            f"<div>{text_value(text, 'below_target_sentence', '{community} is below target.').format(community=f'<strong>{group_name}</strong>')}</div>"
            f"<div>{text_value(text, 'current_choice_sentence', 'The current choice is {choice}.').format(choice=current_choices)}</div>"
            f"<div>{text_value(text, 'try_attributes_sentence', 'Try alternatives in these attributes: {attributes}.').format(attributes=attribute_names)}</div>"
            "</div>"
        )

    rows_html = "".join(rows)
    st.markdown(
        "<section class='culprit-card'>"
        f"<div class='culprit-title'>&#128269; {text_value(text, 'bottleneck_title', 'Likely bottleneck to explore')}</div>"
        f"<div class='culprit-body'>{rows_html}</div>"
        f"<div class='culprit-impact'>{text_value(text, 'bottleneck_impact', 'This looks like the most promising single attribute to experiment with next.')}</div>"
        "</section>",
        unsafe_allow_html=True,
    )


def render_attribute_picker_header(language: str, attribute: str) -> None:
    color = ATTRIBUTE_COLORS[attribute]
    attribute_label = html.escape(UI[language]["attributes"][attribute])
    options = "".join(
        f"<li>{html.escape(level_label(language, level))}</li>"
        for level in LEVELS[attribute]
    )

    st.sidebar.markdown(
        f"""
        <div class="attribute-picker" style="--attribute-color: {color};">
            <div class="attribute-picker-label">
                <span class="attribute-color-dot"></span>
                <span>{attribute_label}</span>
                <span class="attribute-hover-cue">{html.escape(text_value(UI[language], "options", "Options"))}</span>
            </div>
            <div class="attribute-options-panel">
                <div class="attribute-options-title">{attribute_label}</div>
                <ul>{options}</ul>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def package_key(attribute: str) -> str:
    return f"package_level_{attribute}"


def ensure_package_state() -> None:
    for attribute in ATTRIBUTES:
        key = package_key(attribute)
        if key not in st.session_state or st.session_state[key] not in LEVELS[attribute]:
            st.session_state[key] = None


def reset_package_attempt() -> None:
    for attribute in ATTRIBUTES:
        st.session_state[package_key(attribute)] = None
    st.session_state.acceptability_checked = False
    st.session_state.agreement_sound_state = None
    st.session_state.package_warning = False


def render_package_popovers(language: str) -> dict[str, str | None]:
    ensure_package_state()
    text = UI[language]
    previous_selected = {attribute: st.session_state[package_key(attribute)] for attribute in ATTRIBUTES}
    fallback_instruction = 'Select one option from each attribute to build your solution package and then press the button "Check acceptability".'
    package_instruction = text_value(text, "package_instruction", fallback_instruction)

    st.subheader(text["package"])
    st.markdown(
        f"<p class='package-instruction'>{package_instruction}</p>",
        unsafe_allow_html=True,
    )
    for attribute in ATTRIBUTES:
        color = ATTRIBUTE_COLORS[attribute]
        attribute_label = html.escape(text["attributes"][attribute])
        current_level = st.session_state[package_key(attribute)]
        selected_label = html.escape(
            level_label(language, current_level)
            if current_level
            else text_value(text, "select_option_placeholder", "Choose an option")
        )

        card_col, option_col = st.columns([2.25, 3.0], gap="small")
        with card_col:
            st.markdown(
                f"""
                <div class="popover-attribute-card" style="--attribute-color: {color};">
                    <div class="popover-attribute-label">
                        <span class="attribute-color-dot"></span>
                        <span>{attribute_label}</span>
                    </div>
                    <div class="popover-selected-level">{selected_label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with option_col:
            st.markdown(
                f"<span class='option-color-marker option-color-{attribute}'></span>",
                unsafe_allow_html=True,
            )
            st.selectbox(
                text["attributes"][attribute],
                LEVELS[attribute],
                index=LEVELS[attribute].index(current_level) if current_level in LEVELS[attribute] else None,
                key=package_key(attribute),
                format_func=lambda level, lang=language: level_label(lang, level),
                placeholder=text_value(text, "options", "Options"),
                label_visibility="collapsed",
            )

    selected = {attribute: st.session_state[package_key(attribute)] for attribute in ATTRIBUTES}
    if selected != previous_selected:
        st.session_state.acceptability_checked = False
        st.session_state.agreement_sound_state = None
        if all(selected.get(attribute) for attribute in ATTRIBUTES):
            st.session_state.package_warning = False

    return selected


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
            f"{attributes[attribute]}: {level_label(language, package[attribute])}"
            for attribute in ATTRIBUTES
        )

    return "; ".join(level_label(language, package[attribute]) for attribute in ATTRIBUTES)


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
        text = GC_ENGLISH_LEVELS.get(attribute, {}).get(level, level_label(language, level))
    elif language == "English" and group == "TC":
        text = TC_ENGLISH_LEVELS.get(attribute, {}).get(level, level_label(language, level))
    elif language == "Ελληνικά" and group == "GC":
        text = GC_GREEK_LEVELS.get(attribute, {}).get(level, level_label(language, level))
    elif language == "Ελληνικά" and group == "TC":
        text = TC_GREEK_LEVELS.get(attribute, {}).get(level, level_label(language, level))
    elif language == "Türkçe" and group == "GC":
        text = GC_TURKISH_LEVELS.get(attribute, {}).get(level, level_label(language, level))
    elif language == "Türkçe" and group == "TC":
        text = TC_TURKISH_LEVELS.get(attribute, {}).get(level, level_label(language, level))
    else:
        text = level_label(language, level)

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


def render_project_information(language: str) -> None:
    text = UI[language]
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
    st.markdown(
        f"""
        <section class="method-explainer">
            <p>{text_value(text, "research_method_note", "")}</p>
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
        background:
            linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(248, 250, 252, 0.93)),
            linear-gradient(135deg, rgba(239, 68, 68, 0.14), rgba(16, 185, 129, 0.10) 34%, rgba(59, 130, 246, 0.12) 68%, rgba(139, 92, 246, 0.12));
        border-right: 1px solid #d7dee8;
    }
    [data-testid="stSidebar"],
    [data-testid="stSidebar"] > div,
    [data-testid="stSidebar"] [data-testid="stSidebarContent"] {
        overflow: visible;
    }
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] label {
        color: #1f2933;
        font-weight: 700 !important;
    }
    [data-testid="stSidebar"] h2 {
        margin-top: 1.4rem;
    }
    [data-testid="stSidebar"] {
        display: none;
    }
    .attribute-picker {
        position: relative;
        margin: 1.05rem 0 0.38rem 0;
        z-index: 20;
    }
    .attribute-picker:hover {
        z-index: 200;
    }
    .attribute-picker-label {
        display: flex;
        align-items: center;
        gap: 0.55rem;
        border: 1px solid color-mix(in srgb, var(--attribute-color) 42%, #ffffff);
        border-left: 6px solid var(--attribute-color);
        border-radius: 8px;
        padding: 0.62rem 0.7rem;
        background: color-mix(in srgb, var(--attribute-color) 10%, #ffffff);
        color: #17212b;
        font-size: 0.95rem;
        font-weight: 780;
        line-height: 1.25;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }
    .attribute-color-dot {
        flex: 0 0 auto;
        width: 0.72rem;
        height: 0.72rem;
        border-radius: 999px;
        background: var(--attribute-color);
        box-shadow: 0 0 0 3px color-mix(in srgb, var(--attribute-color) 18%, transparent);
    }
    .attribute-hover-cue {
        margin-left: auto;
        border-radius: 999px;
        padding: 0.2rem 0.48rem;
        background: rgba(255, 255, 255, 0.78);
        color: #475569;
        font-size: 0.7rem;
        font-weight: 800;
        text-transform: uppercase;
    }
    .attribute-options-panel {
        position: absolute;
        top: 0;
        left: calc(100% + 1rem);
        display: none;
        width: min(430px, calc(100vw - 390px));
        max-height: 360px;
        overflow: auto;
        border: 1px solid color-mix(in srgb, var(--attribute-color) 42%, #d8dee4);
        border-top: 5px solid var(--attribute-color);
        border-radius: 8px;
        padding: 0.88rem 1rem;
        background: #ffffff;
        box-shadow: 0 18px 40px rgba(15, 23, 42, 0.20);
    }
    .attribute-picker:hover .attribute-options-panel {
        display: block;
    }
    .attribute-options-title {
        color: #111827;
        font-size: 0.98rem;
        font-weight: 820;
        line-height: 1.25;
        margin-bottom: 0.48rem;
    }
    .attribute-options-panel ul {
        margin: 0;
        padding-left: 1.1rem;
    }
    .attribute-options-panel li {
        color: #334155;
        font-size: 0.9rem;
        line-height: 1.35;
        padding: 0.28rem 0;
    }
    .popover-attribute-card {
        border: 1px solid color-mix(in srgb, var(--attribute-color) 32%, #d8dee4);
        border-left: 6px solid var(--attribute-color);
        border-radius: 7px 7px 0 0;
        padding: 0.48rem 0.62rem 0.62rem 0.62rem;
        margin: 0.04rem 0 0 0;
        background: color-mix(in srgb, var(--attribute-color) 8%, #ffffff);
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
        min-height: 4.2rem;
        overflow: visible;
    }
    .popover-attribute-label {
        display: flex;
        align-items: center;
        gap: 0.45rem;
        color: #17212b;
        font-size: 1rem;
        font-weight: 820;
        line-height: 1.18;
    }
    .popover-selected-level {
        color: #475569;
        font-size: 0.86rem;
        line-height: 1.32;
        margin-top: 0.22rem;
        overflow: visible;
    }
    .package-instruction {
        color: #475569;
        font-size: 0.98rem;
        line-height: 1.32;
        margin: -0.3rem 0 0.35rem 0;
    }
    .option-color-marker {
        display: none;
    }
    div[data-testid="stSelectbox"] {
        margin-bottom: 0.08rem;
    }
    div[data-testid="stSelectbox"] [data-baseweb="select"] > div {
        min-height: 2.9rem;
        height: 2.9rem;
        border-radius: 8px !important;
        color: #ffffff !important;
        font-size: 0.86rem;
        font-weight: 780;
        white-space: nowrap;
        overflow: hidden;
    }
    div[data-baseweb="popover"] {
        width: min(680px, 46vw) !important;
        min-width: min(560px, 40vw) !important;
        max-width: min(680px, 46vw) !important;
        margin-left: 7rem !important;
    }
    div[data-baseweb="popover"] ul,
    div[data-baseweb="popover"] [role="listbox"],
    div[data-baseweb="menu"] {
        width: min(680px, 46vw) !important;
        min-width: min(560px, 40vw) !important;
        max-width: min(680px, 46vw) !important;
    }
    div[data-baseweb="popover"] [role="option"] {
        width: 100% !important;
        max-width: none !important;
        white-space: normal !important;
        height: auto !important;
        min-height: 2.45rem !important;
        align-items: flex-start !important;
    }
    div[data-baseweb="popover"] [role="option"] div {
        width: 100% !important;
        max-width: none !important;
        white-space: normal !important;
        overflow: visible !important;
        text-overflow: clip !important;
        line-height: 1.28 !important;
    }
    div[data-testid="stSelectbox"] [data-baseweb="select"] span,
    div[data-testid="stSelectbox"] [data-baseweb="select"] div {
        color: inherit !important;
        -webkit-text-fill-color: currentColor !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }
    div[data-testid="stVerticalBlock"]:has(.option-color-political_structure) div[data-testid="stSelectbox"] [data-baseweb="select"] > div,
    div[data-testid="column"]:has(.option-color-political_structure) div[data-testid="stSelectbox"] [data-baseweb="select"] > div {
        background: #ef4444 !important;
        border-color: #ef4444 !important;
    }
    div[data-testid="stVerticalBlock"]:has(.option-color-territorial_arrangements) div[data-testid="stSelectbox"] [data-baseweb="select"] > div,
    div[data-testid="column"]:has(.option-color-territorial_arrangements) div[data-testid="stSelectbox"] [data-baseweb="select"] > div {
        background: #f59e0b !important;
        border-color: #f59e0b !important;
    }
    div[data-testid="stVerticalBlock"]:has(.option-color-compensation_property) div[data-testid="stSelectbox"] [data-baseweb="select"] > div,
    div[data-testid="column"]:has(.option-color-compensation_property) div[data-testid="stSelectbox"] [data-baseweb="select"] > div {
        background: #10b981 !important;
        border-color: #10b981 !important;
    }
    div[data-testid="stVerticalBlock"]:has(.option-color-security_guarantees) div[data-testid="stSelectbox"] [data-baseweb="select"] > div,
    div[data-testid="column"]:has(.option-color-security_guarantees) div[data-testid="stSelectbox"] [data-baseweb="select"] > div {
        background: #3b82f6 !important;
        border-color: #3b82f6 !important;
    }
    div[data-testid="stVerticalBlock"]:has(.option-color-judicial_system) div[data-testid="stSelectbox"] [data-baseweb="select"] > div,
    div[data-testid="column"]:has(.option-color-judicial_system) div[data-testid="stSelectbox"] [data-baseweb="select"] > div {
        background: #8b5cf6 !important;
        border-color: #8b5cf6 !important;
    }
    div[data-testid="stVerticalBlock"]:has(.option-color-energy_cooperation) div[data-testid="stSelectbox"] [data-baseweb="select"] > div,
    div[data-testid="column"]:has(.option-color-energy_cooperation) div[data-testid="stSelectbox"] [data-baseweb="select"] > div {
        background: #06b6d4 !important;
        border-color: #06b6d4 !important;
    }
    div[data-testid="stPopover"] {
        margin-bottom: 0.08rem;
    }
    div[data-testid="stPopover"] button {
        min-height: 2.45rem;
        height: 2.45rem;
        border-radius: 7px;
        padding: 0.05rem 0.45rem;
        font-size: 0.92rem;
        font-weight: 760;
        color: #334155 !important;
        background: #ffffff !important;
    }
    div[data-testid="stPopover"] button * {
        color: inherit !important;
        opacity: 1 !important;
        visibility: visible !important;
    }
    div[data-testid="stPopover"] button p,
    div[data-testid="stPopover"] button span,
    div[data-testid="stPopover"] button div {
        color: inherit !important;
        -webkit-text-fill-color: currentColor !important;
        opacity: 1 !important;
    }
    div[data-testid="stVerticalBlock"]:has(.option-color-political_structure) div[data-testid="stPopover"] button,
    div[data-testid="column"]:has(.option-color-political_structure) div[data-testid="stPopover"] button {
        background: #ef4444 !important;
        border-color: #ef4444 !important;
        color: #ffffff !important;
    }
    div[data-testid="stVerticalBlock"]:has(.option-color-territorial_arrangements) div[data-testid="stPopover"] button,
    div[data-testid="column"]:has(.option-color-territorial_arrangements) div[data-testid="stPopover"] button {
        background: #f59e0b !important;
        border-color: #f59e0b !important;
        color: #ffffff !important;
    }
    div[data-testid="stVerticalBlock"]:has(.option-color-compensation_property) div[data-testid="stPopover"] button,
    div[data-testid="column"]:has(.option-color-compensation_property) div[data-testid="stPopover"] button {
        background: #10b981 !important;
        border-color: #10b981 !important;
        color: #ffffff !important;
    }
    div[data-testid="stVerticalBlock"]:has(.option-color-security_guarantees) div[data-testid="stPopover"] button,
    div[data-testid="column"]:has(.option-color-security_guarantees) div[data-testid="stPopover"] button {
        background: #3b82f6 !important;
        border-color: #3b82f6 !important;
        color: #ffffff !important;
    }
    div[data-testid="stVerticalBlock"]:has(.option-color-judicial_system) div[data-testid="stPopover"] button,
    div[data-testid="column"]:has(.option-color-judicial_system) div[data-testid="stPopover"] button {
        background: #8b5cf6 !important;
        border-color: #8b5cf6 !important;
        color: #ffffff !important;
    }
    div[data-testid="stVerticalBlock"]:has(.option-color-energy_cooperation) div[data-testid="stPopover"] button,
    div[data-testid="column"]:has(.option-color-energy_cooperation) div[data-testid="stPopover"] button {
        background: #06b6d4 !important;
        border-color: #06b6d4 !important;
        color: #ffffff !important;
    }
    div[data-testid="stButton"] button[kind="secondary"] {
        background: #bbf7d0 !important;
        border-color: #86efac !important;
        color: #14532d !important;
        font-weight: 760;
    }
    .attribute-color-dot {
        width: 0.72rem;
        height: 0.72rem;
    }
    .acceptability-prompt {
        border: 1px solid #d8e2ef;
        border-radius: 8px;
        padding: 1rem 1rem;
        margin-top: 3.1rem;
        background: #f8fbff;
        min-height: 230px;
    }
    .acceptability-prompt-title {
        color: #17212b;
        font-size: 0.98rem;
        font-weight: 780;
        line-height: 1.25;
        margin-bottom: 0.35rem;
        overflow-wrap: anywhere;
    }
    .acceptability-prompt-body {
        color: #475569;
        font-size: 0.88rem;
        line-height: 1.45;
        margin-bottom: 0.9rem;
    }
    div[data-testid="stRadio"] label {
        border: 1px solid #d8dee4;
        border-radius: 8px;
        padding: 0.56rem 0.65rem;
        margin-bottom: 0.38rem;
        background: #ffffff;
    }
    div[data-testid="stRadio"] label p {
        font-size: 1rem;
        line-height: 1.32;
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
        grid-template-columns: auto minmax(170px, 1fr);
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
    .agreement-detail {
        color: #334155;
        font-size: 0.9rem;
        line-height: 1.45;
        margin-top: 0.55rem;
    }
    .agreement-badges {
        display: flex;
        flex-wrap: wrap;
        grid-column: 1 / -1;
        justify-content: flex-start;
        gap: 0.45rem;
    }
    .agreement-badge {
        border: 1px solid #d8dee4;
        border-radius: 999px;
        padding: 0.42rem 0.65rem;
        background: #ffffff;
        color: #334155;
        font-size: 0.82rem;
        font-weight: 700;
        line-height: 1.15;
        max-width: 100%;
        white-space: normal;
        word-break: normal;
        overflow-wrap: anywhere;
    }
    .agreement-badge-passed {
        border-color: #a9d7b8;
        color: #166534;
    }
    .agreement-badge-below_target {
        border-color: #f0cf83;
        color: #8a5b00;
    }
    .share-card {
        border: 1px solid #b7e4c7;
        border-left: 6px solid #22c55e;
        border-radius: 8px;
        padding: 1rem 1.15rem;
        margin: 0.7rem 0 0.55rem 0;
        background: #f0fdf4;
    }
    .share-title {
        color: #14532d;
        font-size: 1.06rem;
        font-weight: 820;
        line-height: 1.25;
    }
    .share-text {
        color: #334155;
        font-size: 0.96rem;
        line-height: 1.4;
        margin-top: 0.35rem;
    }
    .share-actions {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin-top: 0.75rem;
    }
    .share-actions a {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border-radius: 999px;
        padding: 0.45rem 0.72rem;
        background: #ffffff;
        border: 1px solid #86efac;
        color: #166534;
        font-weight: 760;
        text-decoration: none;
        font-size: 0.9rem;
    }
    .share-actions a:hover {
        background: #dcfce7;
        text-decoration: none;
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
    .culprit-community-row {
        border-top: 1px solid #eadfbd;
        padding-top: 0.62rem;
        margin-top: 0.62rem;
    }
    .culprit-community-row:first-child {
        border-top: 0;
        padding-top: 0;
        margin-top: 0;
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
    .team-section,
    .method-explainer {
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
    .team-section p,
    .method-explainer p {
        font-size: 1rem;
        line-height: 1.45;
        margin: 0 0 0.8rem 0;
    }
    .method-explainer {
        margin-top: 1.2rem;
        padding: 1.1rem 1.25rem;
        border: 1px solid #d8e2ef;
        border-radius: 8px;
        background: #f8fbff;
    }
    .method-explainer p {
        color: #334155;
        line-height: 1.58;
        margin-bottom: 0;
    }
    .method-explainer a {
        color: #0f766e;
        font-weight: 760;
        text-decoration: none;
    }
    .method-explainer a:hover {
        text-decoration: underline;
    }
    .team-section {
        margin-bottom: 2.5rem;
    }
    @media (max-width: 860px) {
        .attribute-options-panel {
            position: static;
            width: 100%;
            max-height: 280px;
            margin-top: 0.45rem;
            box-shadow: 0 10px 26px rgba(15, 23, 42, 0.14);
        }
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


render_logo_header()

title_col, language_col = st.columns([3, 1], gap="large")
with language_col:
    language = st.selectbox("Language / Γλώσσα / Dil", list(UI.keys()), label_visibility="collapsed")
text = UI[language]
enable_sounds = True
with language_col:
    st.caption(text_value(text, "language_hint", "Choose your language (English, Ελληνικά, Türkçe)"))

with title_col:
    st.title(text["title"])

package_col, feedback_col = st.columns([2.55, 0.55], gap="large")

with package_col:
    selected_levels = render_package_popovers(language)

all_attributes_selected = all(selected_levels.get(attribute) for attribute in ATTRIBUTES)
completed_package = (
    {attribute: selected_levels[attribute] for attribute in ATTRIBUTES}
    if all_attributes_selected
    else None
)
gc_support = predict("GC", "forced", completed_package) if completed_package else None
tc_support = predict("TC", "forced", completed_package) if completed_package else None
joint_support = min(gc_support, tc_support) if completed_package else None

with feedback_col:
    st.markdown(
        f"""
        <section class="acceptability-prompt">
            <div class="acceptability-prompt-title">{text_value(text, "ready_title", "Ready to test the package?")}</div>
            <div class="acceptability-prompt-body">{text_value(text, "ready_body", "When your selections are set, check whether the package reaches the 55% acceptability goal in both communities.")}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    check_clicked = st.button(
        text_value(text, "check_acceptability", "Check acceptability"),
        type="primary",
        use_container_width=True,
    )
    if check_clicked:
        if completed_package:
            st.session_state.acceptability_checked = True
            st.session_state.package_warning = False
        else:
            st.session_state.acceptability_checked = False
            st.session_state.package_warning = True

    if st.session_state.get("package_warning", False):
        st.warning(text_value(text, "select_all_warning", "Please select one option from each attribute before checking acceptability."))

st.markdown("<div style='height: 0.75rem;'></div>", unsafe_allow_html=True)
if st.session_state.get("acceptability_checked", False) and completed_package:
    st.subheader(text["results_title"])
    kpi_left, kpi_mid, kpi_right = st.columns([1, 1, 1], gap="small")

    with kpi_left:
        render_kpi_card(text["gc_support"], gc_support)

    with kpi_mid:
        render_kpi_card(text["joint_support"], joint_support)

    with kpi_right:
        render_kpi_card(text["tc_support"], tc_support)

    shared_success = render_agreement_status(text, gc_support, tc_support)
    current_agreement_state = "success" if shared_success else "failure"
    previous_agreement_state = st.session_state.get("agreement_sound_state")
    if enable_sounds and previous_agreement_state != current_agreement_state:
        play_agreement_tone(current_agreement_state)
    st.session_state.agreement_sound_state = current_agreement_state
    if not shared_success:
        render_culprit_feedback(language, completed_package, gc_support, tc_support)
        st.button(
            text_value(text, "try_again", "Try again"),
            use_container_width=True,
            on_click=reset_package_attempt,
        )
    else:
        render_success_share_panel(language, completed_package, gc_support, tc_support)

    left, right = st.columns([1, 1], gap="large")

    with left:
        render_result_card("GC", language, completed_package, gc_support)

    with right:
        render_result_card("TC", language, completed_package, tc_support)

    render_summary_table(text, gc_support, tc_support)
    render_extreme_narratives(language)
    render_viable_packages(language)
render_project_information(language)

st.markdown(f"<p class='method-note'>{text['method_note']}</p>", unsafe_allow_html=True)

