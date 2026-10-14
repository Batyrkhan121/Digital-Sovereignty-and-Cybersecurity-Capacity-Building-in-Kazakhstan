"""Phase F13.2b - the institutions thesaurus as data: one decision for every Kazakhstan institution variant (normalised key, step 3)
that occurs in two or more records. 'merge: token ...' maps the variant to another institution's canonical name;
'keep: distinct institution' keeps the variant as an institution of its own under the canonical name given (its normalised form is
the variant itself). Variants in one record are not listed: they join a canonical name only when their normalised form equals it,
otherwise they stay as they are. Canonical names: the full current English name as the institution writes it (from the executor's
knowledge; no network lookup). confidence: high / medium / low."""

ENU = "L.N. Gumilyov Eurasian National University"
KAZNU = "Al-Farabi Kazakh National University"
NU = "Nazarbayev University"
AITU = "Astana IT University"
IITU = "International Information Technology University"
YU = "Yessenov University"
SU = "Satbayev University"
KBTU = "Kazakh-British Technical University"
IICT = "Institute of Information and Computational Technologies"
KAZNPU = "Abai Kazakh National Pedagogical University"
AUPET = "Almaty University of Power Engineering and Telecommunications named after Gumarbek Daukeyev"
SDU = "SDU University"
KATRU = "S. Seifullin Kazakh Agrotechnical Research University"
EKTU = "D. Serikbayev East Kazakhstan Technical University"
SKU = "M. Auezov South Kazakhstan University"
IEC = "International Educational Corporation"
IETU = "International Engineering Technological University"
ZARU = "K. Zhubanov Aktobe Regional University"
AMKU = "Abay Myrzakhmetov Kokshetau University"
AAMIA = "Almaty Academy of the Ministry of Internal Affairs of the Republic of Kazakhstan named after Makan Yesbulatov"
IDET = "Institute of Digital Engineering and Technology"
KBU = "Karaganda Buketov University"
KTU = "Abylkas Saginov Karaganda Technical University"
LEA = "Law Enforcement Academy under the Prosecutor General’s Office of the Republic of Kazakhstan"
DULATY = "M.Kh. Dulaty Taraz Regional University"
MNU = "Maqsut Narikbayev University"
TOR = "Toraighyrov University"
ZK = "Zhangir Khan West Kazakhstan Agrarian-Technical University"
ZHET = "Zhetysu University named after Ilyas Zhansugurov"

K = "keep: distinct institution"
UNIT = "unit or place without a parent institution in the string; parent unknown, kept as written"

# (variant, canonical, rule, confidence, reason)
ROWS = [
    ("gumilyov eurasian national university", ENU, K, "high", "canonical form of the Gumilyov / Gumilev group"),
    ("eurasian national university", ENU, "merge: token eurasian national", "high", "the only Eurasian National University in Kazakhstan is the Gumilyov one"),
    ("gumilyov eurasian national university (enu)", ENU, "merge: token gumilyov", "high", "same name with its abbreviation"),
    ("eurasian national university gumilyov", ENU, "merge: token gumilyov", "high", "'named after' word order"),
    ("gumilyev eurasian national university", ENU, "merge: token gumilyov / gumilyev", "high", "transliteration variant of Gumilyov"),
    ("al farabi kazakh national university", KAZNU, K, "high", "canonical form of the al-Farabi group"),
    ("kazakh national university al farabi", KAZNU, "merge: token farabi", "high", "'named after' word order"),
    ("kazakh national university al farabi (kaznu)", KAZNU, "merge: token farabi", "high", "'named after' word order with abbreviation KazNU"),
    ("al farabi kazakh nationl university", KAZNU, "merge: token farabi", "high", "misspelling 'Nationl'"),
    ("kazakh national university", KAZNU, "merge: kazakh national university without qualifier", "low",
     "unqualified 'Kazakh National University' is read as al-Farabi KazNU; other national universities carry a qualifier"),
    ("nazarbayev university", NU, K, "high", "canonical form; Nazarbayev Intellectual Schools are a different institution (one record, not merged)"),
    ("astana it university", AITU, K, "high", "canonical form of Astana IT University"),
    ("international information technology university", IITU, K, "high", "canonical form of the IITU group"),
    ("international it university", IITU, "merge: token international information technology", "high", "IITU's short English name"),
    ("international university of information technology", IITU, "merge: token international information technology", "high", "word-order variant of IITU"),
    ("international university of information technologies", IITU, "merge: token international information technology", "high", "word-order and plural variant of IITU"),
    ("international information technologies university", IITU, "merge: token international information technology", "high", "plural variant of IITU"),
    ("international it university (iitu)", IITU, "merge: token international information technology", "high", "IITU's short name with abbreviation"),
    ("yessenov university", YU, K, "high", "canonical form; current name of the Caspian University of Technology and Engineering"),
    ("caspian university of technology and engineering sh yessenov", YU, "merge: token yessenov", "high", "former full name of Yessenov University"),
    ("caspian state university of technologies and engineering sh yesenov", YU, "merge: token yessenov / yesenov", "high", "former name, transliteration Yesenov"),
    ("caspian state university of technology and engineering sh yessenov", YU, "merge: token yessenov", "high", "former name of Yessenov University"),
    ("caspian university of technology and engineering sh yesenova", YU, "merge: token yessenov / yesenova", "high", "former name, transliteration Yesenova"),
    ("sh yesenov caspian university of technology and engineering", YU, "merge: token yessenov / yesenov", "high", "former name, name first"),
    ("yessenov caspian state university of technologies and engineering", YU, "merge: token yessenov", "high", "former name, name first"),
    ("satbayev university", SU, K, "high", "canonical form; current name of the Kazakh National Research Technical University"),
    ("kazakh national technical university", SU, "merge: former name", "high", "KazNTU, former name of Satbayev University"),
    ("kazakh national technical university satpayev", SU, "merge: token satpayev", "high", "former name with Satpayev"),
    ("kazakh national research technical university", SU, "merge: former name", "high", "KazNRTU, former name of Satbayev University"),
    ("kazakh national research technical university satpayev", SU, "merge: token satpayev", "high", "former name with Satpayev"),
    ("satpayev kazakh national research technical university", SU, "merge: token satpayev", "high", "former name with Satpayev, name first"),
    ("kazakh british technical university", KBTU, K, "high", "canonical form of Kazakh-British Technical University"),
    ("business school of kazakh british technical university", KBTU, "merge: token kazakh british", "high", "a school of KBTU named as the whole part"),
    ("institute of information and computational technologies", IICT, K, "high", "canonical form of the IICT group"),
    ("institute of information and computational technologies cs mshe rk", IICT, "merge: token information and computational technologies", "high", "IICT with its ministry suffix"),
    ("institute of information and computational technologies of committee of science", IICT, "merge: token information and computational technologies", "high", "IICT with its parent body"),
    ("information and computational technologies institute", IICT, "merge: token information and computational technologies", "high", "word-order variant of IICT"),
    ("institute information and computational technologies almaty", IICT, "merge: token information and computational technologies", "high", "IICT without 'of', with city"),
    ("institute information and computational technologies cs mes rk", IICT, "merge: token information and computational technologies", "high", "IICT with ministry suffix"),
    ("institute of information and computational technologies cs mes rk", IICT, "merge: token information and computational technologies", "high", "IICT with ministry suffix"),
    ("institute of information and computational technologies of mes rk", IICT, "merge: token information and computational technologies", "high", "IICT with ministry suffix"),
    ("institute of information and computational technologies of rk mes cs", IICT, "merge: token information and computational technologies", "high", "IICT with ministry suffix"),
    ("laboratory of information security at institute of information and computational technologies", IICT, "merge: token information and computational technologies", "high",
     "a laboratory of IICT named as the whole part"),
    ("abai kazakh national pedagogical university", KAZNPU, K, "high", "canonical form of Abai KazNPU"),
    ("kazakh national pedagogical university abay", KAZNPU, "merge: token pedagogical + abai / abay", "high", "'named after' word order"),
    ("kazakh national university abai", KAZNPU, "merge: token abai", "medium", "the Abai-named national university is the pedagogical one"),
    ("abay university", KAZNPU, "merge: token abai / abay", "medium", "read as the 'Abai University' brand of KazNPU; Abay Myrzakhmetov Kokshetau University is kept apart"),
    ("almaty university of power engineering and telecommunications gumarbek daukeyev", AUPET, K, "high", "canonical form of the AUPET group"),
    ("almaty university of power engineering and telecommunications", AUPET, "merge: token power engineering and telecommunications", "high", "AUPET without the name"),
    ("almaty university of power engineering and telecommunication", AUPET, "merge: token power engineering and telecommunication", "high", "AUPET, singular"),
    ("almaty university of power engineering and telecommunications gumarbek daukeev", AUPET, "merge: token daukeev / daukeyev", "high", "transliteration Daukeev"),
    ("almaty university of power engineering and telecommunications name gumarbek daukeev", AUPET, "merge: token daukeev", "high", "'Name After' left after normalisation"),
    ("almaty university of energy and communications", AUPET, "merge: token energy and communications", "medium", "literal translation of AUPET's Russian name"),
    ("daukeev almaty university of energy and communications", AUPET, "merge: token daukeev", "high", "literal translation with the name"),
    ("almaty university of power energy and telecommunication", AUPET, "merge: token power ... telecommunication", "high", "misspelt AUPET"),
    ("almaty university of power engineering and telecommunications (aupet)", AUPET, "merge: token power engineering and telecommunications", "high", "AUPET with abbreviation"),
    ("gumarbek daukeev almaty university of power engineering and communications", AUPET, "merge: token daukeev", "high", "name-first variant"),
    ("university of power engineering and telecommunications (aupet) daukeev", AUPET, "merge: token daukeev", "high", "AUPET without 'Almaty'"),
    ("energo university", "Energo University", K, "low", "not identified with AUPET; kept as written"),
    ("turan university", "Turan University", K, "high", "Turan University, Almaty; Turan-Astana University (one record) is a different institution"),
    ("narxoz university", "Narxoz University", K, "high", "no other variant"),
    ("sdu university", SDU, K, "high", "canonical form; current name of Suleyman Demirel University"),
    ("suleyman demirel university", SDU, "merge: token demirel", "high", "former name of SDU University"),
    ("kazakh humanitarian juridical innovative university", "Kazakh Humanitarian Juridical Innovative University", K, "high", "no other variant in two or more records"),
    ("astana international university", "Astana International University", K, "high", "no other variant"),
    ("seifullin kazakh agrotechnical research university", KATRU, K, "high", "canonical form of the Seifullin group"),
    ("seifullin kazakh agro technical university", KATRU, "merge: token seifullin", "high", "former name, 'Agro Technical'"),
    ("seifullin kazakh agrotechnical university", KATRU, "merge: token seifullin", "high", "former name before 'Research'"),
    ("seifullin kazakh agro technical research university", KATRU, "merge: token seifullin", "high", "'Agro Technical' spelling"),
    ("kazakh agrotechnical university seifullina", KATRU, "merge: token seifullin", "high", "'named after' order, Russian genitive"),
    ("academy of public administration under president of republic of kazakhstan",
     "Academy of Public Administration under the President of the Republic of Kazakhstan", K, "high", "no other variant"),
    ("serikbayev east kazakhstan technical university", EKTU, K, "high", "canonical form of D. Serikbayev EKTU"),
    ("kazakh university of economics", "Kazakh University of Economics", K, "low", "parent unclear; possibly the University of Economics, Finance and International Trade; kept as written"),
    ("kazakh university of technology and business", "Kazakh University of Technology and Business", K, "medium", "kept as written; the Kulazhanov-named one-record variants were not merged"),
    ("national engineering academy of republic of kazakhstan", "National Engineering Academy of the Republic of Kazakhstan", K, "high", "no other variant"),
    ("almaty technological university", "Almaty Technological University", K, "high", "no other variant"),
    ("auezov south kazakhstan university", SKU, K, "high", "canonical form of M. Auezov South Kazakhstan University"),
    ("south kazakhstan state university", SKU, "merge: former name", "medium", "former name (South Kazakhstan State University named after M. Auezov)"),
    ("international education corporation", IEC, "merge: token international education corporation", "high", "'Education' for 'Educational'"),
    ("kobenkulova international education corporation", IEC, "merge: token international education corporation", "medium", "same corporation with a personal name prefix"),
    ("international engineering technological university", IETU, K, "high", "canonical form of IETU"),
    ("international engineering and technological university", IETU, "merge: token international engineering technological", "high", "'and' inserted"),
    ("zhubanov aktobe regional university", ZARU, K, "high", "canonical form of K. Zhubanov ARU"),
    ("zhubanov aktobe regional state university", ZARU, "merge: token zhubanov", "high", "former name with 'State'"),
    ("abay myrzakhmetov kokshetau university", AMKU, K, "high", "distinct from Abai KazNPU although it shares the token 'abay'"),
    ("myrzakhmetov kokshetau university", AMKU, "merge: token myrzakhmetov", "high", "without the first name"),
    ("almaty academy of ministry of internal affairs of republic of kazakhstan", AAMIA, "merge: token almaty academy of ministry of internal affairs", "high", "without the name"),
    ("almaty academy of ministry of internal affairs named esbulatov", AAMIA, "merge: token esbulatov / yesbulatov", "high", "transliteration Esbulatov"),
    ("almaty academy", "Almaty Academy", K, "low", "ambiguous short name; not merged"),
    ("almaty management university", "Almaty Management University", K, "high", "no other variant"),
    ("department of computer science", "Department of Computer Science", K, "low", UNIT),
    ("department of information security", "Department of Information Security", K, "low", UNIT),
    ("department of cybersecurity", "Department of Cybersecurity", K, "low", UNIT),
    ("department of information and communication technologies", "Department of Information and Communication Technologies", K, "low", UNIT),
    ("ece department", "ECE Department", K, "low", UNIT),
    ("school of information technology and engineering", "School of Information Technology and Engineering", K, "low", UNIT),
    ("higher school of information technology and engineering", "Higher School of Information Technology and Engineering", K, "low", UNIT),
    ("school of earth sciences", "School of Earth Sciences", K, "low", UNIT),
    ("astana", "Astana", K, "low", UNIT),
    ("institute of philosophy", "Institute of Philosophy", K, "medium", "kept as written"),
    ("jsc “institute of digital engineering and technology”", IDET, "merge: legal form and quotes dropped", "high", "same institute without 'JSC' and quotes"),
    ("karaganda buketov university", KBU, K, "high", "canonical form; current name of Buketov Karaganda State University"),
    ("ye buketov karaganda state university", KBU, "merge: token buketov", "high", "former name"),
    ("korkyt ata kyzylorda university", "Korkyt Ata Kyzylorda University", K, "high", "canonical form; the 'State' one-record variant was not merged"),
    ("abylkas saginov karaganda technical university", KTU, K, "high", "canonical form of Saginov KTU"),
    ("karaganda state technical university", KTU, "merge: former name", "high", "former name of Saginov Karaganda Technical University"),
    ("karaganda technical university", KTU, "merge: token karaganda technical", "high", "short name of Saginov KTU"),
    ("law enforcement academy under prosecutor general’s office of republic of kazakhstan", LEA, K, "high", "canonical form"),
    ("academy of law enforcement agencies under general prosecutor's office of republic of kazakhstan", LEA, "merge: token law enforcement + prosecutor", "high",
     "translation variant of the same academy"),
    ("akhmet baitursynuly kostanay regional university", "Akhmet Baitursynuly Kostanay Regional University", K, "high", "canonical form"),
    ("civil aviation academy", "Civil Aviation Academy", K, "high", "the one-record 'Academy of Civil Aviation' was not merged"),
    ("de montfort university", "De Montfort University", K, "medium", "the Kazakhstan campus of De Montfort University"),
    ("esil university", "Esil University", K, "high", "the one-record 'Institution Esil University' was not merged"),
    ("interdepartmental research institute", "Interdepartmental Research Institute", K, "low", "parent unknown; kept as written"),
    ("karaganda economic university of kazpotrebsoyuz", "Karaganda Economic University of Kazpotrebsoyuz", K, "high", "no other variant"),
    ("kazakh russian international university", "Kazakh-Russian International University", K, "high", "no other variant"),
    ("kazakh university ways of communications", "Kazakh University Ways of Communications", K, "high", "no other variant"),
    ("kh dulaty taraz state university", DULATY, "merge: token dulaty", "high", "former name of M.Kh. Dulaty Taraz Regional University"),
    ("khoja akhmet yassawi international kazakh turkish university", "Khoja Akhmet Yassawi International Kazakh-Turkish University", K, "high", "canonical form"),
    ("kimep university", "KIMEP University", K, "high", "no other variant"),
    ("narikbayev kazguu university", MNU, "merge: token narikbayev", "high", "former name (KAZGUU) of Maqsut Narikbayev University"),
    ("national research oncology center", "National Research Oncology Center", K, "high", "no other variant"),
    ("national scientific laboratory for collective use of information and space technologies (nslc ist)",
     "National Scientific Laboratory for the Collective Use of Information and Space Technologies (NSLC IST)", K, "medium",
     "a laboratory with its own name; not merged into its host university"),
    ("research & development systems llc", "Research & Development Systems LLC", K, "high", "a company"),
    ("sarsen amanzholov east kazakhstan university", "Sarsen Amanzholov East Kazakhstan University", K, "high", "canonical form"),
    ("sh ualikhanov kokshetau university", "Sh. Ualikhanov Kokshetau University", K, "high", "canonical form"),
    ("shakarim university", "Shakarim University", K, "high", "canonical form; the one-record 'Semey' variants were not merged"),
    ("t&t security llp", "T&T Security LLP", K, "high", "a company"),
    ("toraighyrov pavlodar state university", TOR, "merge: token toraighyrov", "high", "former name of Toraighyrov University"),
    ("zhangir khan west kazakhstan agrarian technical university", ZK, K, "high", "canonical form"),
    ("zhangir khan university", ZK, "merge: token zhangir khan", "high", "short name of the same university"),
    ("zhetysu university zhansugurov", ZHET, "merge: token zhansugurov", "high", "without the first name"),
]

# Distinctive tokens used for grouping (step 3) and, for the sensitivity check only, to count one-record variants that share a
# token with a canonical name but were left as they are (the brief merges one-record variants only by equality).
TOKENS = [
    ("farabi", KAZNU), ("gumil", ENU), ("satbayev", SU), ("satpayev", SU), ("satpaev", SU), ("satbavev", SU), ("kazntu", SU), ("kaznrtu", SU),
    ("yessenov", YU), ("yesenov", YU), ("esenov", YU), ("essenov", YU), ("seifullin", KATRU), ("daukeev", AUPET), ("daukeyev", AUPET),
    ("power engineering", AUPET), ("information and computational technolog", IICT), ("iict", IICT), ("kazakh british", KBTU),
    ("buketov", KBU), ("zhubanov", ZARU), ("shakarim", "Shakarim University"), ("serikba", EKTU), ("auezov", SKU), ("dulat", DULATY),
    ("baitursyn", "Akhmet Baitursynuly Kostanay Regional University"), ("baytursyn", "Akhmet Baitursynuly Kostanay Regional University"),
    ("ualikhanov", "Sh. Ualikhanov Kokshetau University"), ("ualijhanov", "Sh. Ualikhanov Kokshetau University"), ("myrzakhmetov", AMKU),
    ("toraighyrov", TOR), ("zhangir khan", ZK), ("zhansugurov", ZHET), ("nazarbayev university", NU), ("astana it", AITU),
    ("kazakh national pedagogical", KAZNPU), ("international information tech", IITU), ("international it", IITU), ("demirel", SDU),
    ("kozybayev", "Manash Kozybayev North Kazakhstan University"), ("korkyt", "Korkyt Ata Kyzylorda University"),
    ("yassawi", "Khoja Akhmet Yassawi International Kazakh-Turkish University"), ("narikbayev", MNU),
    ("almaty academy of ministry", AAMIA), ("prosecutor", LEA), ("digital engineering and technology", IDET),
]
