"""Seeded national-brand whitelist for the manufacturer extractor.

The list below is curated from the live DB on :8001 (2026-05-25,
~12k offers) and from the design doc's example tables. Every entry
lists the canonical lowercase ASCII-folded form on the left and the
known surface variants (Greek-script and ALL-CAPS variants) on the
right. The matcher folds the product name to the same lower/no-accent
ASCII-ish form and looks for any of these variants as a leading token.

Conventions:
  - Keys are lowercase ASCII, hyphens preserved (`coca-cola`, `head-shoulders`).
  - Aliases include both Greek and Latin spellings since chains differ:
      Sklavenitis        → UPPERCASE Latin (BARILLA, COCA-COLA)
      Masoutis           → Title-case Latin (Barilla, Coca Cola)
      My Market          → Title-case mixed (Coca-Cola)
      AB Vassilopoulos   → rarely prefixes brand at all
  - Single-token Greek brand names that look like common words
    (`ΑΒ` is also Greek alphabet letters) get a small allow-list of
    surrounding context — see `_AMBIGUOUS_BRANDS`.

Adding a brand: append to `BRANDS` with at least the canonical form and
any non-trivial alias. Re-run `crawler/scripts/canon_explore.py` to
verify the new brand is picked up across chains.
"""

from __future__ import annotations

# (canonical_key, [aliases...])
# Aliases are matched case-insensitively against accent-folded text.
BRANDS: list[tuple[str, list[str]]] = [
    # --- Beverages ---------------------------------------------------------
    ("coca-cola",   ["coca-cola", "coca cola", "cocacola"]),
    ("pepsi",       ["pepsi"]),
    ("ivi",         ["ivi", "ηβη"]),
    ("loux",        ["loux", "λουξ"]),
    ("epsa",        ["epsa", "εψα"]),
    ("3ep",         ["3ep", "3εψ"]),
    ("amita",       ["amita"]),
    ("life",        ["life"]),
    ("schweppes",   ["schweppes"]),
    ("fanta",       ["fanta"]),
    ("sprite",      ["sprite"]),
    ("nestea",      ["nestea"]),
    ("lipton",      ["lipton"]),
    ("avra",        ["avra", "αβρα"]),
    ("zagori",      ["zagori", "ζαγορι"]),
    ("souroti",     ["souroti", "σουρωτη"]),
    ("redbull",     ["red bull", "redbull"]),
    ("monster",     ["monster"]),

    # --- Beer / Spirits ----------------------------------------------------
    ("mythos",      ["mythos", "μυθος"]),
    ("heineken",    ["heineken"]),
    ("alfa",        ["alfa", "αλφα"]),
    ("amstel",      ["amstel"]),
    ("fix",         ["fix"]),
    ("kaiser",      ["kaiser"]),
    ("vergina",     ["vergina", "βεργινα"]),
    ("corona",      ["corona"]),

    # --- Dairy / cheese ----------------------------------------------------
    ("delta",       ["delta", "δελτα"]),
    ("mevgal",      ["mevgal", "μεβγαλ"]),
    ("nounou",      ["nounou", "νουνου"]),
    ("dodoni",      ["dodoni", "δωδωνη"]),
    ("kri-kri",     ["kri-kri", "kri kri", "κρι-κρι", "κρι κρι"]),
    ("olympos",     ["olympos", "ολυμπος"]),
    ("ipiros",      ["ipiros", "ηπειρος"]),
    ("lurpak",      ["lurpak"]),
    ("philadelphia",["philadelphia"]),
    ("president",   ["president"]),
    ("arla",        ["arla"]),
    ("creta-farms", ["creta farms", "creta-farms"]),
    ("nikas",       ["nikas", "νικας"]),
    ("ifantis",     ["ifantis", "υφαντης"]),

    # --- Snacks / Chocolate ------------------------------------------------
    ("lacta",       ["lacta", "λακτα"]),
    ("ion",         ["ion", "ιον"]),
    ("nirvana",     ["nirvana"]),
    ("haagen-dazs", ["haagen-dazs", "haagen dazs", "häagen-dazs"]),
    ("magnum",      ["magnum"]),
    ("snickers",    ["snickers"]),
    ("mars",        ["mars"]),
    ("twix",        ["twix"]),
    ("bounty",      ["bounty"]),
    ("kitkat",      ["kitkat", "kit kat", "kit-kat"]),
    ("milka",       ["milka"]),
    ("nestle",      ["nestle", "nestlé"]),
    ("oreo",        ["oreo"]),
    ("papadopoulou",["papadopoulou", "παπαδοπουλου"]),
    ("allatini",    ["allatini", "αλλατινη"]),
    ("3ase",        ["3ase", "3ασε"]),
    ("lays",        ["lay's", "lays"]),
    ("doritos",     ["doritos"]),
    ("pringles",    ["pringles"]),
    ("tasty",       ["tasty"]),
    ("ruffles",     ["ruffles"]),
    ("tuc",         ["tuc"]),
    ("ferrero",     ["ferrero"]),
    ("kinder",      ["kinder"]),
    ("nutella",     ["nutella"]),
    ("merenda",     ["merenda", "μερεντα"]),
    ("3bs",         ["3bs"]),
    ("haribo",      ["haribo"]),

    # --- Coffee / Tea ------------------------------------------------------
    ("nescafe",     ["nescafe", "nescafé"]),
    ("nespresso",   ["nespresso"]),
    ("loumidis",    ["loumidis", "λουμιδης"]),
    ("bravo",       ["bravo", "μπραβο"]),
    ("jacobs",      ["jacobs"]),
    ("dolce-gusto", ["dolce gusto", "dolce-gusto"]),
    ("twinings",    ["twinings"]),

    # --- Pasta / Staples / Sauces -----------------------------------------
    ("barilla",     ["barilla"]),
    ("misko",       ["misko", "μισκο"]),
    ("melissa",     ["melissa"]),
    ("hellas",      ["hellas"]),
    ("3-elies",     ["3 elies", "3-elies", "3 ελιες"]),
    ("kalas",       ["kalas", "καλας"]),
    ("knorr",       ["knorr"]),
    ("maggi",       ["maggi"]),
    ("heinz",       ["heinz"]),
    ("hellmann's",  ["hellmann's", "hellmanns"]),
    ("kraft",       ["kraft"]),
    ("rio-mare",    ["rio mare", "rio-mare"]),
    ("yotis",       ["yotis", "γιωτης"]),
    ("agno",        ["agno", "αγνο"]),
    ("kydonia",     ["kydonia", "κυδωνια"]),

    # --- Cereals / Breakfast ----------------------------------------------
    ("kellogg's",   ["kellogg's", "kelloggs"]),
    ("quaker",      ["quaker"]),
    ("dei",         ["dei", "δει"]),

    # --- Baby / hygiene ----------------------------------------------------
    ("pampers",     ["pampers"]),
    ("babylino",    ["babylino", "μπεμπιλινο"]),
    ("huggies",     ["huggies"]),
    ("libero",      ["libero"]),
    ("tena",        ["tena"]),
    ("always",      ["always"]),
    ("o.b.",        ["o.b.", "ob"]),

    # --- Personal care -----------------------------------------------------
    ("nivea",       ["nivea"]),
    ("dove",        ["dove"]),
    ("pantene",     ["pantene"]),
    ("head-shoulders", ["head & shoulders", "head and shoulders", "head&shoulders"]),
    ("garnier",     ["garnier"]),
    ("l'oreal",     ["l'oreal", "loreal", "l oreal", "l'oréal"]),
    ("elvive",      ["elvive"]),
    ("gillette",    ["gillette"]),
    ("oral-b",      ["oral-b", "oral b"]),
    ("colgate",     ["colgate"]),
    ("sensodyne",   ["sensodyne"]),
    ("aquafresh",   ["aquafresh"]),
    ("syoss",       ["syoss"]),
    ("schwarzkopf", ["schwarzkopf"]),
    ("palette",     ["palette"]),
    ("koleston",    ["koleston"]),
    ("excellence",  ["excellence"]),
    ("bioten",      ["bioten"]),
    ("noxzema",     ["noxzema"]),
    ("septona",     ["septona"]),
    ("hansaplast",  ["hansaplast"]),
    ("carroten",    ["carroten"]),
    ("piz-buin",    ["piz buin", "piz-buin"]),
    ("ambre-solaire", ["ambre solaire", "ambre-solaire"]),
    ("diadermine",  ["diadermine"]),
    ("maybelline",  ["maybelline"]),
    ("mua",         ["mua"]),
    ("str8",        ["str8"]),
    ("old-spice",   ["old spice", "old-spice"]),
    ("axe",         ["axe"]),
    ("rexona",      ["rexona"]),
    ("fa",          ["fa"]),
    ("gliss",       ["gliss"]),
    ("luxurious",   ["luxurious"]),
    ("tesori-d'oriente", ["tesori d'oriente", "tesori d oriente"]),
    ("lactacyd",    ["lactacyd"]),

    # --- Household / cleaning ---------------------------------------------
    ("klinex",      ["klinex"]),
    ("ajax",        ["ajax"]),
    ("ariel",       ["ariel"]),
    ("skip",        ["skip"]),
    ("tide",        ["tide"]),
    ("persil",      ["persil"]),
    ("soflan",      ["soflan"]),
    ("comfort",     ["comfort"]),
    ("lenor",       ["lenor"]),
    ("vanish",      ["vanish"]),
    ("calgon",      ["calgon"]),
    ("finish",      ["finish"]),
    ("fairy",       ["fairy"]),
    ("aroxol",      ["aroxol"]),
    ("raid",        ["raid"]),
    ("airwick",     ["airwick", "air wick"]),
    ("glade",       ["glade"]),
    ("febreze",     ["febreze"]),
    ("mr-grand",    ["mr grand", "mrgrand", "mr-grand"]),
    ("mr-muscle",   ["mr muscle", "mr.muscle"]),
    ("dettol",      ["dettol"]),
    ("k2r",         ["k2r"]),

    # --- Pet ---------------------------------------------------------------
    ("whiskas",     ["whiskas"]),
    ("felix",       ["felix"]),
    ("friskies",    ["friskies"]),
    ("purina",      ["purina"]),
    ("pedigree",    ["pedigree"]),
    ("cesar",       ["cesar"]),
    ("sheba",       ["sheba"]),

    # --- Honey / sweets ---------------------------------------------------
    ("attiki",      ["attiki", "αττικη"]),
    ("aroma-melissas", ["aroma melissas", "aroma melissa"]),

    # --- Other --------------------------------------------------------------
    ("decorata",    ["decorata"]),
    ("diana",       ["diana"]),
    ("magic",       ["magic"]),
    ("zewa",        ["zewa"]),
    ("starbucks",   ["starbucks"]),
    ("johnson's",   ["johnson's", "johnsons"]),
    ("soupline",    ["soupline"]),
    ("cyclops",     ["cyclops"]),
    ("dalon",       ["dalon"]),
    ("hawaiian-tropic", ["hawaiian tropic", "hawaiian-tropic", "hawaiian"]),
    ("sarchio",     ["sarchio"]),
    ("biologos",    ["biologos", "βιολογος"]),
    ("le-petit",    ["le petit", "le-petit"]),
    ("orzo-bimbo",  ["orzo bimbo"]),
    ("activia",     ["activia"]),
    ("danone",      ["danone"]),
    ("milko",       ["milko"]),
    ("fage",        ["fage", "φαγε"]),
    ("vlachas",     ["vlachas", "βλαχας"]),
    ("trikalino",   ["trikalino", "τρικαλινο"]),
    ("apivita",     ["apivita"]),
    ("korres",      ["korres"]),
    ("frezyderm",   ["frezyderm"]),
    ("loreal-paris", ["l'oreal paris", "loreal paris"]),
    ("ble",         ["ble"]),
    ("3a",          ["3α", "3a"]),
    ("home",        []),  # too generic — keep empty so no false matches
]


# Private-label/own-brand prefixes — explicitly NEVER canonicalise these
# cross-chain. Detected by the same alias matching, but the resulting
# `manufacturer_brand` is returned as None so the caller treats them as
# unknown (skipped). See design doc §4 own-brand collisions.
PRIVATE_LABEL_BRANDS: list[tuple[str, list[str]]] = [
    ("my-gusto",    ["my gusto"]),
    ("ab",          ["ab vassilopoulos", "ab choice"]),
    ("pilos",       ["pilos"]),
    ("combino",     ["combino"]),
    ("milbona",     ["milbona"]),
    ("solevita",    ["solevita"]),
    ("w5",          ["w5"]),
    ("crusti-croc", ["crusti croc", "crusti-croc"]),
    ("freeway",     ["freeway"]),
    ("master-deal", ["master deal", "masterdeal"]),
    ("home-market", ["home market", "home masoutis"]),
    ("masoutis-pl", ["μασουτης"]),  # chain-own under their own name
    ("my-market-brand", ["my market"]),
]


def all_aliases() -> list[tuple[str, str]]:
    """Yield (alias_lower, canonical_key) pairs from the public brand list.

    Aliases are returned longest-first so the matcher can do greedy
    longest-prefix matching ("Coca-Cola" beats "Coca").
    """
    pairs: list[tuple[str, str]] = []
    for canonical, aliases in BRANDS:
        for alias in aliases:
            pairs.append((alias.lower().strip(), canonical))
    pairs.sort(key=lambda p: -len(p[0]))
    return pairs


def private_label_aliases() -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for canonical, aliases in PRIVATE_LABEL_BRANDS:
        for alias in aliases:
            pairs.append((alias.lower().strip(), canonical))
    pairs.sort(key=lambda p: -len(p[0]))
    return pairs
