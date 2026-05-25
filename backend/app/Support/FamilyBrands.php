<?php

namespace App\Support;

/**
 * Seeded national-brand whitelist mirroring
 * `crawler/scraper/canonical/brands.py`.
 *
 * Sole source of truth on the PHP side: keep this file in sync with the
 * Python list when new brands land in the canonical pipeline. The
 * mirroring is intentional — family-browse is the read-time
 * counterpart of the canonical extractor pipeline and must derive the
 * exact same `manufacturer_brand` token from an identical name so two
 * products from different chains land in the same family.
 *
 * Each entry is `[canonical_key, [aliases...]]`. Canonical keys are
 * lowercase ASCII (hyphens preserved). Aliases match case-insensitively
 * against accent-folded text.
 *
 * Private-label brands deliberately return `null` from
 * {@see \App\Services\VariantDescriber::manufacturerBrand()} — see the
 * design doc §"Own-brand collisions": these never participate in
 * cross-chain family browse.
 */
class FamilyBrands
{
    /** @var array<int, array{0: string, 1: array<int, string>}> */
    public const BRANDS = [
        // --- Beverages ---------------------------------------------------------
        ['coca-cola',   ['coca-cola', 'coca cola', 'cocacola']],
        ['pepsi',       ['pepsi']],
        ['ivi',         ['ivi', 'ηβη']],
        ['loux',        ['loux', 'λουξ']],
        ['epsa',        ['epsa', 'εψα']],
        ['3ep',         ['3ep', '3εψ']],
        ['amita',       ['amita']],
        ['life',        ['life']],
        ['schweppes',   ['schweppes']],
        ['fanta',       ['fanta']],
        ['sprite',      ['sprite']],
        ['nestea',      ['nestea']],
        ['lipton',      ['lipton']],
        ['avra',        ['avra', 'αβρα']],
        ['zagori',      ['zagori', 'ζαγορι']],
        ['souroti',     ['souroti', 'σουρωτη']],
        ['redbull',     ['red bull', 'redbull']],
        ['monster',     ['monster']],

        // --- Beer / Spirits ----------------------------------------------------
        ['mythos',      ['mythos', 'μυθος']],
        ['heineken',    ['heineken']],
        ['alfa',        ['alfa', 'αλφα']],
        ['amstel',      ['amstel']],
        ['fix',         ['fix']],
        ['kaiser',      ['kaiser']],
        ['vergina',     ['vergina', 'βεργινα']],
        ['corona',      ['corona']],

        // --- Dairy / cheese ----------------------------------------------------
        ['delta',       ['delta', 'δελτα']],
        ['mevgal',      ['mevgal', 'μεβγαλ']],
        ['nounou',      ['nounou', 'νουνου']],
        ['dodoni',      ['dodoni', 'δωδωνη']],
        ['kri-kri',     ['kri-kri', 'kri kri', 'κρι-κρι', 'κρι κρι']],
        ['olympos',     ['olympos', 'ολυμπος']],
        ['ipiros',      ['ipiros', 'ηπειρος']],
        ['lurpak',      ['lurpak']],
        ['philadelphia',['philadelphia']],
        ['president',   ['president']],
        ['arla',        ['arla']],
        ['creta-farms', ['creta farms', 'creta-farms']],
        ['nikas',       ['nikas', 'νικας']],
        ['ifantis',     ['ifantis', 'υφαντης']],

        // --- Snacks / Chocolate ------------------------------------------------
        ['lacta',       ['lacta', 'λακτα']],
        ['ion',         ['ion', 'ιον']],
        ['nirvana',     ['nirvana']],
        ['haagen-dazs', ['haagen-dazs', 'haagen dazs', 'häagen-dazs']],
        ['magnum',      ['magnum']],
        ['snickers',    ['snickers']],
        ['mars',        ['mars']],
        ['twix',        ['twix']],
        ['bounty',      ['bounty']],
        ['kitkat',      ['kitkat', 'kit kat', 'kit-kat']],
        ['milka',       ['milka']],
        ['nestle',      ['nestle', 'nestlé']],
        ['oreo',        ['oreo']],
        ['papadopoulou',['papadopoulou', 'παπαδοπουλου']],
        ['allatini',    ['allatini', 'αλλατινη']],
        ['lays',        ["lay's", 'lays']],
        ['doritos',     ['doritos']],
        ['pringles',    ['pringles']],
        ['tasty',       ['tasty']],
        ['ruffles',     ['ruffles']],
        ['tuc',         ['tuc']],
        ['ferrero',     ['ferrero']],
        ['kinder',      ['kinder']],
        ['nutella',     ['nutella']],
        ['merenda',     ['merenda', 'μερεντα']],
        ['haribo',      ['haribo']],

        // --- Coffee / Tea ------------------------------------------------------
        ['nescafe',     ['nescafe', 'nescafé']],
        ['nespresso',   ['nespresso']],
        ['loumidis',    ['loumidis', 'λουμιδης']],
        ['bravo',       ['bravo', 'μπραβο']],
        ['jacobs',      ['jacobs']],
        ['dolce-gusto', ['dolce gusto', 'dolce-gusto']],
        ['twinings',    ['twinings']],

        // --- Pasta / Staples / Sauces -----------------------------------------
        ['barilla',     ['barilla']],
        ['misko',       ['misko', 'μισκο']],
        ['melissa',     ['melissa']],
        ['hellas',      ['hellas']],
        ['kalas',       ['kalas', 'καλας']],
        ['knorr',       ['knorr']],
        ['maggi',       ['maggi']],
        ['heinz',       ['heinz']],
        ['hellmann\'s', ["hellmann's", 'hellmanns']],
        ['kraft',       ['kraft']],
        ['rio-mare',    ['rio mare', 'rio-mare']],
        ['yotis',       ['yotis', 'γιωτης']],
        ['agno',        ['agno', 'αγνο']],
        ['kydonia',     ['kydonia', 'κυδωνια']],

        // --- Cereals / Breakfast ----------------------------------------------
        ['kellogg\'s',  ["kellogg's", 'kelloggs']],
        ['quaker',      ['quaker']],
        ['dei',         ['dei', 'δει']],

        // --- Baby / hygiene ----------------------------------------------------
        ['pampers',     ['pampers']],
        ['babylino',    ['babylino', 'μπεμπιλινο']],
        ['huggies',     ['huggies']],
        ['libero',      ['libero']],
        ['tena',        ['tena']],
        ['always',      ['always']],
        ['o.b.',        ['o.b.', 'ob']],

        // --- Personal care -----------------------------------------------------
        ['nivea',       ['nivea']],
        ['dove',        ['dove']],
        ['pantene',     ['pantene']],
        ['head-shoulders', ['head & shoulders', 'head and shoulders', 'head&shoulders']],
        ['garnier',     ['garnier']],
        ['l\'oreal',    ["l'oreal", 'loreal', 'l oreal', "l'oréal"]],
        ['elvive',      ['elvive']],
        ['gillette',    ['gillette']],
        ['oral-b',      ['oral-b', 'oral b']],
        ['colgate',     ['colgate']],
        ['sensodyne',   ['sensodyne']],
        ['aquafresh',   ['aquafresh']],
        ['syoss',       ['syoss']],
        ['schwarzkopf', ['schwarzkopf']],
        ['palette',     ['palette']],
        ['koleston',    ['koleston']],
        ['excellence',  ['excellence']],
        ['bioten',      ['bioten']],
        ['noxzema',     ['noxzema']],
        ['septona',     ['septona']],
        ['hansaplast',  ['hansaplast']],
        ['carroten',    ['carroten']],
        ['piz-buin',    ['piz buin', 'piz-buin']],
        ['ambre-solaire', ['ambre solaire', 'ambre-solaire']],
        ['diadermine',  ['diadermine']],
        ['maybelline',  ['maybelline']],
        ['mua',         ['mua']],
        ['str8',        ['str8']],
        ['old-spice',   ['old spice', 'old-spice']],
        ['axe',         ['axe']],
        ['rexona',      ['rexona']],
        ['fa',          ['fa']],
        ['gliss',       ['gliss']],
        ['luxurious',   ['luxurious']],
        ['tesori-d\'oriente', ["tesori d'oriente", 'tesori d oriente']],
        ['lactacyd',    ['lactacyd']],

        // --- Household / cleaning ---------------------------------------------
        ['klinex',      ['klinex']],
        ['ajax',        ['ajax']],
        ['ariel',       ['ariel']],
        ['skip',        ['skip']],
        ['tide',        ['tide']],
        ['persil',      ['persil']],
        ['soflan',      ['soflan']],
        ['comfort',     ['comfort']],
        ['lenor',       ['lenor']],
        ['vanish',      ['vanish']],
        ['calgon',      ['calgon']],
        ['finish',      ['finish']],
        ['fairy',       ['fairy']],
        ['aroxol',      ['aroxol']],
        ['raid',        ['raid']],
        ['airwick',     ['airwick', 'air wick']],
        ['glade',       ['glade']],
        ['febreze',     ['febreze']],
        ['mr-grand',    ['mr grand', 'mrgrand', 'mr-grand']],
        ['mr-muscle',   ['mr muscle', 'mr.muscle']],
        ['dettol',      ['dettol']],
        ['k2r',         ['k2r']],

        // --- Pet ---------------------------------------------------------------
        ['whiskas',     ['whiskas']],
        ['felix',       ['felix']],
        ['friskies',    ['friskies']],
        ['purina',      ['purina']],
        ['pedigree',    ['pedigree']],
        ['cesar',       ['cesar']],
        ['sheba',       ['sheba']],

        // --- Honey / sweets ---------------------------------------------------
        ['attiki',      ['attiki', 'αττικη']],
        ['aroma-melissas', ['aroma melissas', 'aroma melissa']],

        // --- Other --------------------------------------------------------------
        ['decorata',    ['decorata']],
        ['diana',       ['diana']],
        ['magic',       ['magic']],
        ['zewa',        ['zewa']],
        ['starbucks',   ['starbucks']],
        ['johnson\'s',  ["johnson's", 'johnsons']],
        ['soupline',    ['soupline']],
        ['cyclops',     ['cyclops']],
        ['dalon',       ['dalon']],
        ['hawaiian-tropic', ['hawaiian tropic', 'hawaiian-tropic', 'hawaiian']],
        ['sarchio',     ['sarchio']],
        ['biologos',    ['biologos', 'βιολογος']],
        ['le-petit',    ['le petit', 'le-petit']],
        ['orzo-bimbo',  ['orzo bimbo']],
        ['activia',     ['activia']],
        ['danone',      ['danone']],
        ['milko',       ['milko']],
        ['fage',        ['fage', 'φαγε']],
        ['vlachas',     ['vlachas', 'βλαχας']],
        ['trikalino',   ['trikalino', 'τρικαλινο']],
        ['apivita',     ['apivita']],
        ['korres',      ['korres']],
        ['frezyderm',   ['frezyderm']],
        ['ble',         ['ble']],
    ];

    /**
     * Private-label aliases. Matched first; matches return `null` from
     * the manufacturer extractor so own-brand SKUs never participate
     * in cross-chain family browse.
     *
     * @var array<int, array{0: string, 1: array<int, string>}>
     */
    public const PRIVATE_LABEL_BRANDS = [
        ['my-gusto',    ['my gusto']],
        ['ab',          ['ab vassilopoulos', 'ab choice']],
        ['pilos',       ['pilos']],
        ['combino',     ['combino']],
        ['milbona',     ['milbona']],
        ['solevita',    ['solevita']],
        ['w5',          ['w5']],
        ['crusti-croc', ['crusti croc', 'crusti-croc']],
        ['freeway',     ['freeway']],
        ['master-deal', ['master deal', 'masterdeal']],
        ['home-market', ['home market', 'home masoutis']],
        ['masoutis-pl', ['μασουτης']],
        ['my-market-brand', ['my market']],
    ];

    /**
     * Yield (alias_lower, canonical_key) pairs from the public brand list,
     * longest first so the matcher can do greedy longest-prefix matching.
     *
     * @return array<int, array{0: string, 1: string}>
     */
    public static function allAliases(): array
    {
        $pairs = [];
        foreach (self::BRANDS as [$canonical, $aliases]) {
            foreach ($aliases as $alias) {
                $pairs[] = [mb_strtolower(trim($alias), 'UTF-8'), $canonical];
            }
        }
        usort($pairs, fn (array $a, array $b) => mb_strlen($b[0], 'UTF-8') <=> mb_strlen($a[0], 'UTF-8'));

        return $pairs;
    }

    /**
     * @return array<int, array{0: string, 1: string}>
     */
    public static function privateLabelAliases(): array
    {
        $pairs = [];
        foreach (self::PRIVATE_LABEL_BRANDS as [$canonical, $aliases]) {
            foreach ($aliases as $alias) {
                $pairs[] = [mb_strtolower(trim($alias), 'UTF-8'), $canonical];
            }
        }
        usort($pairs, fn (array $a, array $b) => mb_strlen($b[0], 'UTF-8') <=> mb_strlen($a[0], 'UTF-8'));

        return $pairs;
    }
}
