"""
Seed data for the rules table.

Every regex rule from notebooks 1.5 PopulatePropertyIds and 2.0 CategoriseFiles
is extracted here in execution order, organised by phase.

Phase order:  property -> category -> subcategory -> override
Within each phase: order_index determines first-match-wins precedence.
Override phase rules are unconditional (they overwrite earlier phases).
"""

import json

def _aw(*conditions):
    """Helper to build apply_when_json from condition dicts."""
    if len(conditions) == 1:
        return json.dumps(conditions[0])
    return json.dumps(list(conditions))


# ---------------------------------------------------------------------------
# PHASE 1: PROPERTY  (from 1.5)
# ---------------------------------------------------------------------------
# Sub-phase 1a: mortgage_map rules (only apply when effective_subcategory
#   matches DIRECTDEBIT|OTH|PAYMENT|Direct Debit|Other|Bill Payment)
MORTGAGE_SUBCAT_FILTER = {"field": "effective_subcategory", "regex": "DIRECTDEBIT|OTH|PAYMENT|Direct Debit|Other|Bill Payment"}

_mortgage_map_raw = [
    (r'^MORTGAGE EXPRESS\s*001872470.*$|^TOPAZ FIN ROSINCA.*131992707.*$', 'F1321LON'),
    (r'^BHAM MIDSHIRES.*20003649652.*$', 'F2321LON'),
    (r'^BHAM MIDSHIRES.*609204286200.*$', 'F2321LON'),
    (r'^BHAM MIDSHIRES.*020010557032.*$', 'F2321LON'),
    (r'^BHAM MIDSHIRES.*67921167200300.*$', 'F2321LON'),
    (r'^.*907371904.*$|^JASPER.*390255001.*$', 'F3321LON'),
    (r'^MORTGAGE EXPRESS\s*001703155.*$|^TOPAZ FIN ROSINCA.*131188407.*$', 'F4321LON'),
    (r'^MORTGAGE EXPRESS\s*001996624.*$|^TOPAZ FIN ROSINCA.*132514207.*$', 'F1169FAW'),
    (r'^.*907372200.*$|^JASPER.*390255110.*$', 'F2169FAW'),
    (r'^BHAM MIDSHIRES.*20000389757.*$', 'F3169FAW'),
    (r'^BHAM MIDSHIRES.*60920214910400.*$', 'F3169FAW'),
    (r'^BHAM MIDSHIRES.*020010556389.*$', 'F3169FAW'),
    (r'^BHAM MIDSHIRES.*67921167030300.*$', 'F3169FAW'),
    (r'^MORTGAGE EXPRESS\s*201648504.*$|^TOPAZ FIN ROSINCA.*137376006.*$', 'F1171FAW'),
    (r'^MORTGAGE EXPRESS\s*201648513.*$|^TOPAZ FIN ROSINCA.*137376104.*$', 'F2171FAW'),
    (r'^MORTGAGE EXPRESS\s*201648522.*$|^TOPAZ FIN.*191462710.*$', 'F3171FAW'),
    (r'^MORTGAGE EXPRESS\s*001647053.*$|^TOPAZ FIN ROSINCA.*130936210.*$', 'F2163FRA'),
    (r'^MORTGAGE EXPRESS\s*001586614.*$|^TOPAZ FIN ROSINCA.*130654303.*$', 'F3163FRA'),
    (r'^.*20002731371.*$', 'F4163FRA'),
    (r'^.*60920368370700.*$', 'F4163FRA'),
    (r'^.*KINGSTON SHOP.*$', 'SHOP196KIN'),
    (r'^BHAM MIDSHIRES.*20007882432.*$', '196AKIN'),
    (r'^BHAM MIDSHIRES.*60920762960200.*$', '196AKIN'),
    (r'^.*020007900597.*$', '196BKIN'),
    (r'^.*60920765020300.*$', '196BKIN'),
    (r'^.*20004110676.*$', '23BHAM'),
    (r'^.*60920454430500.*$', '23BHAM'),
    (r'^.*631516204.*$|^.*24935234.*$', '23CHAM'),
    (r'^.*002186317.*$', 'F58ALH'),
    (r'^PLATFORM FUNDING\s*01050228957650.*$', 'F68ALH'),
    (r'^PLATFORM FUNDING\s*01050228957685.*$', 'F78ALH'),
    (r'^AMBER HOMELOANS.*480441702.*$', 'F88ALH'),
    (r'^SKIPTON.*165905969.*$', 'F88ALH'),
    (r'^.*002186357.*$', 'F1746ALH'),
    (r'^.*002186356.*$', 'F1846ALH'),
    (r'^PLATFORM FUNDING\s*01050228979115.*$', 'F1946ALH'),
    (r'^PLATFORM FUNDING.*01050229961082.*$', 'F2046ALH'),
    (r'^.*480016104.*$', 'F2146ALH'),
    (r'^PLATFORM FUNDING\s*01050229961090.*$', 'F2246ALH'),
    (r'^PLATFORM FUNDING\s*01050228964703.*$', 'F2346ALH'),
    (r'^MORTGAGE EXPRESS\s*200633231.*$|^TOPAZ FIN.*190812705.*$', 'F31214ALH'),
    (r'^.*20009309942.*$', 'F41214ALH'),
    (r'^.*60920963520600.*$', 'F41214ALH'),
    (r'^MORTGAGE EXPRESS\s*200578729.*$|^TOPAZ FIN.*190778206.*$', 'F51214ALH'),
    (r'^.*002197389.*$', 'F71214ALH'),
    (r'^MORTGAGE EXPRESS\s*200637264.*$|^TOPAZ FIN ROSINCA.*134121904.*$', 'F111214ALH'),
    (r'^MORTGAGE EXPRESS\s*200754471.*$|^TOPAZ FIN.*190885105.*$', 'F101214ALH'),
    (r'^MORTGAGE EXPRESS\s*200754525.*$|^TOPAZ FIN ROSINCA.*134467209.*$', 'F141214ALH'),
    (r'^MORTGAGE EXPRESS\s*200754534.*$|^TOPAZ FIN.*190885203.*$', 'F161214ALH'),
    (r'^MORTGAGE EXPRESS\s*200709336.*$|^TOPAZ FIN ROSINCA.*134332909.*$', 'F11618ALH'),
    (r'^MORTGAGE EXPRESS\s*200709327.*$|^TOPAZ FIN.*190859005.*$', 'F31618ALH'),
    (r'^PLATFORM FUNDING.*01050230313307.*$', 'F61618ALH'),
    (r'^MORTGAGE EXPRESS\s*200710767.*$|^TOPAZ FIN.*190859506.*$', 'F71618ALH'),
    (r'^MORTGAGE EXPRESS\s*200709345.*$|^TOPAZ FIN ROSINCA.*134333009.*$', 'F111618ALH'),
    (r'^MORTGAGE EXPRESS\s*200878410.*$|^TOPAZ FIN.*190959705.*$', 'F121618ALH'),
    (r'^MORTGAGE EXPRESS\s*200710776.*$|^TOPAZ FIN ROSINCA.*134338410.*$', 'F131618ALH'),
    (r'^MORTGAGE EXPRESS\s*200766478.*$|^TOPAZ FIN.*190892600.*$', 'F161618ALH'),
]

# Sub-phase 1b: allocate_codes_for_rents_and_expenses (no subcategory filter)
# Memo-suffix rules first (code at end of memo): match before broader patterns
_rent_expense_map_raw = [
    (r'.*17\s+4-6.*', 'F1746ALH'),       # e.g. CLASSIC CARPETS ... 1586 17 4-6 carper
    (r'.*\s41214\s.*', 'F41214ALH'),    # e.g. A Beck ... 25658 41214 GS rem
    (r'.*\s31214\s.*', 'F31214ALH'),    # e.g. A Beck ... 25755 31214 GS
    (r'.*7\s+8\s.*', 'F78ALH'),         # e.g. Jijo George 99 7 8 bath repair
    (r'.*13\s+16-18.*', 'F131618ALH'),  # e.g. PCC ... flat 13 16-18 empty...
    (r'.*12\s+1618.*', 'F121618ALH'),   # e.g. Salvatore Mulara 12 1618 ref
    (r'.*1[ ]?321.*|.*Soumya.*|.*.Chowdhury.*', 'F1321LON'),
    (r'.*2[ ]?321.*|.*CIPRIAN.*', 'F2321LON'),
    (r'.*3[ ]?321.*|.*Ibiyemi.*|.*.Shubhi.*|.*Connacher.*', 'F3321LON'),
    (r'.*4[ ]?321.*|.*Kumar.*', 'F4321LON'),
    (r'.*169.*171.*', '169FAW'),
    (r'.*1[ ]?169.*|.*SUSAN.*PARKINSON.*|.*Dandekar.*', 'F1169FAW'),
    (r'.*2[ ]?169.*|.*HAJEK.*|.*Granil.*', 'F2169FAW'),
    (r'.*3[ ]?169.*|.*JOHN[ ]?A[ ]*RENT.*|.*SAIT.*', 'F3169FAW'),
    (r'.*1[ ]?171.*', 'F1171FAW'),
    (r'.*2[ ]?171.*|.*FLAT 2171 FAWCETT.*', 'F2171FAW'),
    (r'.*3[ ]?171.*|.*[ ]3171[ ].*|.*FULKER.*', 'F3171FAW'),
    (r'.*2[ ]?163[ ]?.*', 'F2163FRA'),
    (r'.*3[ ]?163[ ]?.*|.*BRETT.*', 'F3163FRA'),
    (r'.*4[ ]?163[ ]?.*|.*NATSO.*', 'F4163FRA'),
    (r'.*196[ ]*SHOP.*|.*SHOP[ ]*196.*', 'SHOP196KIN'),
    (r'.*196[ ]?A.*|.*196A KINGSTON ROAD.*|.*Saunyama.*', '196AKIN'),
    (r'.*196[ ]?B.*|.*Williams.*', '196BKIN'),
    (r'.*23[ ]?B.*|.*Bijumon.*', '23BHAM'),
    (r'.*23[ ]?C.*|.*Mohammad.*', '23CHAM'),
    (r'.*F17[ ]?4[-]?6.*|.*17[ ]?4[-]?6[ ]?ALH.*|.*FLAT[ ]?17.*|.*[ ]+1746[ ]+.*|.*Gregson.*|.*BULLOCK.*', 'F1746ALH'),
    (r'.* 18 4[-]?6.*|.*F18[ ]?4[-]?6.*|.*18[ ]?4[-]?6[ ]?ALH.*|.*PARSON.*|.*McGowan.*', 'F1846ALH'),
    (r'.* 19 4[-]?6.*|.*F19[ ]?4[-]?6.*|.*19[ ]?4[-]?6[ ]?ALH.*|.*Ingoldsby.*|.*Yilmaz.*|.*LINDFIELD.*', 'F1946ALH'),
    (r'.*F20[ ]?4[-]?6.*|.*20[ ]?4[-]?6[ ]?ALH.*|.*Lindemere.*|.*MANGATTU.*|.*McIntosh.*|.*UVAROV.*', 'F2046ALH'),
    (r'.* 21 4[-]?6.*|.*F21[ ]?4[-]?6.*|.*21[ ]?4[-]?6[ ]?ALH.*|.*Stukas.*|.*S PARKINSON.*|.*Cobley.*|.*cove.*', 'F2146ALH'),
    (r'.*F22[ ]?4[-]?6.*|.*22[ ]?4[-]?6[ ]?ALH.*|.*Pidduck.*|.*GONGORA.*|.*JOSE.*', 'F2246ALH'),
    (r'.* 23 4[-]?6.*|.*F23[ ]?4[-]?6.*|.*23[ ]?4[-]?6[ ]?ALH.*|.*MARIA C.*|.*FITZGERALD.*', 'F2346ALH'),
    (r'.*F5[ ]?8.*|.*5[ ]?8[ ]?ALH.*|.*FLAT 58 ALHAMBRA.*|.*BOTTLE.*', 'F58ALH'),
    (r'.*F6[ ]?8.*|.*6[ ]?8[ ]?ALH.*|.*FLAT 68 ALHAMBRA.*|.*M.*Bristow.*|.*Elliott.*', 'F68ALH'),
    (r'.*F7[ ]?8.*|.*7[ ]?7[ ]?ALH.*|.*FLAT 78 ALHAMBRA.*|.*[ ]7[ ]8ALHAMBRA.*|.*Lucinda.*', 'F78ALH'),
    (r'.*F8[ ]?8.*|.*8[ ]?8[ ]?ALH.*|.*FURCZYK.*|.*Marin.*|.*Ricketts.*', 'F88ALH'),
    (r'.*F10[ ]?12[-]?14.*|.*10[ ]?12[-]?14[ ]?ALH.*|.* 101214.*', 'F101214ALH'),
    (r'.* 11 12[-]?14.*|.*F11[ ]?12[-]?14.*|.*11[ ]?12[-]?14[ ]?ALH.*|.*[ ]+111214[ ]+.*|.*MORTON.*', 'F111214ALH'),
    (r'.* 14 12[-]?14.*|.*F14[ ]?12[-]?14.*|.*14[ ]?12[-]?14[ ]?ALH.*|.*Cowie.*', 'F141214ALH'),
    (r'.*F16[ ]?12[-]?14.*|.*16[ ]?12[-]?14.[ ]?ALH*|.*SINGH.*|.*SAMRAT.*', 'F161214ALH'),
    (r'.*F3[ ]?12[-]?14.*|.*3[ ]?12[-]?14[ ]?ALH.*|.*[ ]3[ ]12[-]?14.*|.*Moore.*', 'F31214ALH'),
    (r'.* 4 12[-]?14.*|.*F4[ ]?12[-]?14.*|.*4[ ]?12[-]?14[ ]?ALH.*|.*Ramos.*', 'F41214ALH'),
    (r'.*F5[ ]?12[-]?14.*|.*5[ ]?12[-]?14[ ]?ALH.*|.*Kirwin.*', 'F51214ALH'),
    (r'.*F7[ ]?12[-]?14.*|.*7[ ]?12[-]?14[ ]?ALH.*|.* 71214.*|.*Angel.*', 'F71214ALH'),
    (r'.* 11 16[-]?18.*|.*F11[ ]?16[-]?18.*|.*11[ ]?16[-]?18[ ]?ALH.*|.*[ ]+111214[ ]+.*|.*ZERDIN.*|.*Kuriakose.*', 'F111618ALH'),
    (r'.*F12[ ]?16[-]?18.*|.*12[ ]?16[-]?18[ ]?ALH.*|.*BARTON.*', 'F121618ALH'),
    (r'.*F13[ ]?16[-]?18.*|.*13[ ]?16[-]?18[ ]?ALH.*|.*IVANOV.*|.*Thornton.*|.*KAUNG.*', 'F131618ALH'),
    (r'.* 16 16[-]?18.*|.*F16[ ]?16[-]?18.*|.*16[ ]?16[-]?18[ ]?ALH.*|.*LEDGER.*|.*HUDSON.*', 'F161618ALH'),
    (r'.* 1 16[-]?18.*|.*F1[ ]?16[-]?18.*|.* 1[ ]?16[-]?18[ ]?ALH.*|.*FYLES.*|.*BECK.*11618', 'F11618ALH'),
    (r'.*F3[ ]?16[-]?18.*|.* 3[ ]?16[-]?18[ ]?ALH.*|.*[ ]3[ ]16[-]?18.*|.*BARBER.*|.*PACHIS.*', 'F31618ALH'),
    (r'.*F6[ ]?16[-]?18.*|.* 6[ ]?16[-]?18[ ]?ALH.*|.*Pcc.*Housing.*Benefi.*7489.*|.*Tap.*9470.*', 'F61618ALH'),
    (r'.*F7[ ]?16[-]?18.*|.* 7[ ]?16[-]?18[ ]?ALH.*|.*JACKSON.*|.*AYLIFFE.*|.*Byrne.*', 'F71618ALH'),
    (r'.*6882766014.*', '169FAW'),
    (r'.*ICE PROFESSIONALS.*|.*NRLA.*', 'RSA'),
    (r'.*20777805.*|.*321 London Road.*', '321LON'),
    (r'.*169 Fawcett Road.*', '169FAW'),
    (r'.*171[ ]?Faw.*', '171FAW'),
]


def _build_property_rules():
    rules = []
    idx = 0

    for pattern, prop_code in _mortgage_map_raw:
        idx += 1
        rules.append({
            "rule_id": f"prop_mort_{prop_code}_{idx}",
            "order_index": idx,
            "phase": "property",
            "pattern": pattern,
            "outputs_json": json.dumps({"property_code": prop_code}),
            "strength": "strong",
            "apply_when_json": json.dumps(MORTGAGE_SUBCAT_FILTER),
            "banks_json": None,
            "accounts_json": None,
            "enabled": 1,
        })

    for pattern, prop_code in _rent_expense_map_raw:
        idx += 1
        rules.append({
            "rule_id": f"prop_rent_{prop_code}_{idx}",
            "order_index": idx,
            "phase": "property",
            "pattern": pattern,
            "outputs_json": json.dumps({"property_code": prop_code}),
            "strength": "strong",
            "apply_when_json": None,
            "banks_json": None,
            "accounts_json": None,
            "enabled": 1,
        })

    return rules


# ---------------------------------------------------------------------------
# PHASE 2: CATEGORY  (from 2.0 categorise_new_data)
# We use the "new" rules (post rsaCapitalDate = 2022-08-01)
# ---------------------------------------------------------------------------

def _build_category_rules():
    rules = []
    idx = 0

    def _add(pattern, cat, strength="strong", apply_when=None, desc=None):
        nonlocal idx
        idx += 1
        outputs = {"category": cat}
        if desc:
            outputs["description"] = desc
        rules.append({
            "rule_id": f"cat_{cat.lower()}_{idx}",
            "order_index": idx,
            "phase": "category",
            "pattern": pattern,
            "outputs_json": json.dumps(outputs),
            "strength": strength,
            "apply_when_json": json.dumps(apply_when) if apply_when else None,
            "banks_json": None,
            "accounts_json": None,
            "enabled": 1,
        })

    # Mortgages
    _add(r'JASPER|TOPAZ|SIBERITE|SKIPTON|MORTGAGE EXPRESS|NRAM|PLATFORM|AMBER|BHAM|CAPITAL|CHL|MORTGAGE TRUST|PARAGON|HESSONITE', 'Mortgage')
    _add(r'.*M TUCKER.*STO.*', 'Mortgage', apply_when=[{"field": "amount", "min": -200, "max": -190}])

    # Rents
    _add(r'^BEALS[ ]?ESTATE[ ]?AGENT.*$', 'BealsRent')
    _add(r'.*DEPOSIT.*|.*TDS.*', 'Deposit', apply_when=[{"field": "description", "regex": ".*DEPOSIT.*|.*TDS.*"}])
    _add(r'.*TDS.*', 'Deposit')
    _add(r'.*DEPOSIT.*|.*HampTerr Dep.*', 'Deposit', apply_when={"field": "effective_subcategory", "regex": "REVENUE|Funds Transfer|Counter Credit|Standing Order|Bill Payment"})
    _add(r'__PROPERTY_NOT_EMPTY__', 'OurRent', apply_when={"field": "effective_subcategory", "regex": "REVENUE"})
    _add(r'.*RENT.*|.*KUMAR.*|.*LINDEMERE.*|.*SEQUENCE UK.*|.*SOPHIE.*|.*BETTS.*|.*RAMOS.*', 'OurRent', apply_when={"field": "effective_subcategory", "regex": "Funds Transfer|Counter Credit|Standing Order|Bill Payment"})

    # Property Expenses
    _add(r'.*PORTSEA.*|.*BECK.*|.*COURT FEE.*|.*ROGERS.*|.*ICE PROFESSIONAL.*|.*SOUTHERN ELEC.*|.*Just Answer.*|.*SSE.*|.*OVO.*', 'PropertyExpense', apply_when={"field": "effective_subcategory", "regex": "WORKPLACE|Bill Payment|Funds Transfer|Standing Order"})
    _add(r'__SUBCAT_ADMIN__', 'PropertyExpense', apply_when={"field": "effective_subcategory", "regex": "^ADMIN$"})

    # Service Charges and Transfers
    _add(r'23 HAMPSHIRE.*STO|4-6 ALHAMBRA RD CS|12-14 ALHAMBRA RD|16-18 ALHAMBRA RD|ALHAMBRA ROAD MANA|Alhambra Road M Tucker SC|ALHHAMBRA ROAD M Tucker SC|Lordswood Estates M Tucker SC', 'ServiceCharge')
    _add(r'.*30728691.*', 'Funds3072')
    _add(r'.*40406538 .*', 'Funds4040')
    _add(r'.*60458872.*', 'Funds6045')
    _add(r'.*Mortgages.*', 'MortgageRefund', apply_when={"field": "effective_subcategory", "regex": "Standing Order|INTEREST_PAYMENTS"})
    _add(r'__SUBCAT_DIRECTORS_WAGES__', 'PersonalExpense', apply_when={"field": "effective_subcategory", "regex": "DIRECTORS_WAGES|directors wages"})
    _add(r'RSA CAPITAL', 'OurRent', apply_when=[{"field": "effective_subcategory", "regex": "^Bill Payment$"}, {"field": "amount", "min": -999999, "max": 0}])
    _add(r'.*FRATTON SC.*|.*FRATTON ROAD.*|.*FRATTON RD.*|.*CREST.*', 'FrattonRoad', apply_when={"field": "effective_subcategory", "regex": "Funds Transfer"})
    _add(r'__SUBCAT_REPAIRS__', 'PropertyExpense', apply_when={"field": "effective_subcategory", "regex": "REPAIRS_AND_MAINTENANCE"})

    # School, Hilltop, HMRC
    _add(r'.*HARPUR TRUST.*|.*BEDFORD SCHOOL.*', 'SchoolFee')
    _add(r'G[ ]?[&+][ ]?F[ ]?VALENTINO.*', 'Hilltop')
    _add(r'.*HMRC*.', 'HMRC', apply_when={"field": "effective_subcategory", "regex": "^Bill Payment$"})
    _add(r'.*HMRC*.', 'HMRCDD', apply_when={"field": "effective_subcategory", "regex": "^Direct Debit$"})

    # Car, Regular
    _add(r'.*LAND ROVER.*', 'Car')
    _add(r'NATIONWIDE|KINGSTON UNITY', 'RegularPayment', apply_when={"field": "effective_subcategory", "regex": "Standing Order|Direct Debit"})
    _add(r'Spotify', 'RegularPayment')
    _add(r'__SUBCAT_DD__', 'RegularPayment', apply_when={"field": "effective_subcategory", "regex": "^Direct Debit$"})
    _add(r'.*M TUCKER.*STO.*', 'RegularPayment', apply_when=[{"field": "effective_subcategory", "regex": "^Standing Order$"}, {"field": "amount", "min": -100, "max": 0}])
    _add(r'.*Amazon Prime*', 'RegularPayment', apply_when=[{"field": "effective_subcategory", "regex": "^Card Purchase$"}, {"field": "amount", "min": -7.99, "max": -7.99}])

    # Personal expenses by subcategory
    _add(r'__SUBCAT_CARD__', 'PersonalExpense', apply_when={"field": "effective_subcategory", "regex": ".*Card Purchase.*|.*Card Refund.*"})
    _add(r'__SUBCAT_CASH_WITHDRAWAL__', 'PersonalExpense', apply_when={"field": "effective_subcategory", "regex": "^Cash Withdrawal$"})
    _add(r'__SUBCAT_BILL_PAYMENT__', 'PersonalExpense', apply_when={"field": "effective_subcategory", "regex": "^Bill Payment$"}, strength="weak")
    _add(r'__SUBCAT_PERSONAL__', 'PersonalExpense', apply_when={"field": "effective_subcategory", "regex": "^PERSONAL$"})

    # Catch-all
    _add(r'__AMOUNT_POSITIVE__', 'OtherIncome', strength="catch_all")
    _add(r'__AMOUNT_NEGATIVE__', 'OtherExpense', strength="catch_all")

    return rules


# ---------------------------------------------------------------------------
# PHASE 3: SUBCATEGORY  (from 2.0 categorise_personal_spending, subcat-only)
# Only applies when Cat == PersonalExpense and Subcat is null
# ---------------------------------------------------------------------------

def _build_subcategory_rules():
    rules = []
    idx = 0

    def _add(pattern, subcat, strength="medium", apply_when_cat="PersonalExpense", apply_when_extra=None):
        nonlocal idx
        idx += 1
        aw = [{"field": "category", "regex": f"^{apply_when_cat}$"}]
        if apply_when_extra:
            aw.append(apply_when_extra)
        rules.append({
            "rule_id": f"subcat_{subcat.lower().replace('/', '_').replace(' ', '_')}_{idx}",
            "order_index": idx,
            "phase": "subcategory",
            "pattern": pattern,
            "outputs_json": json.dumps({"subcategory": subcat}),
            "strength": strength,
            "apply_when_json": json.dumps(aw[0] if len(aw) == 1 else aw),
            "banks_json": None,
            "accounts_json": None,
            "enabled": 1,
        })

    # Garage
    _add(r'^BP[ ].*|.*NEW COUNTY SERVICE.*|.*THE GARAGE.*|.*SHELL.*|.*MFG CHILDS WAY.*|.*MORRISONS PETRO.*', 'Garage')

    # Food
    _add(r'.*TESCO.*', 'Tesco')
    _add(r'.*MARKS&SPENCER.*|.*SIMPLY[ ]?FOOD.*', 'M&S')
    _add(r'.*WAITROSE.*', 'Waitrose')
    _add(r'.*W[ ]?M[ ]?MORRISON.*', 'Morrisons')
    _add(r'.*LIDL.*|.*ALDI.*', 'LIDL')
    _add(r'.*CO[-]?OP.*|.*CO[ ]?OP.*', 'COOP')
    _add(r'.*BUDGENS.*|.*COSTCUTTER.*', 'Budgens')
    _add(r'.*COSTCO.*', 'Costco')
    _add(r'.*A1[ ]?Foods.*', 'A1 Foods')
    _add(r'.*SAINSBURY.*', 'Sainsburys')
    _add(r'.*ASDA.*', 'ASDA')

    # Chemist/Pharmacy
    _add(r'.*BOOTS.*|.*SUPERDRUG.*|.*PHARMACY.*|.*THE HIGHLANDS PHAR.*|.*HOLLAND.*|.*Real Health.*|.*SPECSAVERS.*|.*DENTAL.*|.*selectspecs.*|.*VISION DIRECT.*|.*ISHADE OPTI.*', 'Pharmacy/Opticians/Dental')

    # Beauty
    _add(r'.*HARVEY NICHOLS.*|.*LIBERTY.*|.*HARRODS.*|.*Penhaligons.*|.*SELFRIDGES.*|.*LOOKFANTASTIC.*|.*SALLYSALONSERVICES.*|.*RICHY.*|.*C D 4 U.*|.*NAILS.*|.*PHELANS.*', 'Beauty')

    # Eating out
    _add(r'.*MCDONALDS.*|.*BURGER.*|.*FIVE GUYS.*|.*BUBBLE.*|.*CHURROS.*|.*NANDOS.*|.*WAGAMAMA.*|.*BBTEA.*|.*tandoori.*|.*PRET.*|.*MILLIES COOKIES.*|.*GREGGS.*|.*PIZZA.*|.*PRETZELS.*|.*KOKORO.*|.*Whippy.*|.*CHICKEN[ ]?GEORGE.*|.*KFC.*|.*MILTON KEYNES FOOD.*|.*SHAKEAWAY.*|.*KINGS ARMS.*|.*FRANKIE.*BENNYS.*|.*FOURTH.*FIFTH.*|.*FROSTS.*|.*GREGGS.*|.*CHIQUITO.*|.*CHIMICHANGA.*|.*CHOPSTIX.*|.*LAKESIDE FISH.*|.*JUST-EAT.*|.*FOXY[ ]?WINGS.*', 'EatingOut')

    # Coffee
    _add(r'.*Costa.*|.*PAVILION.*|.*Air-Serv.*|.*STARBUCKS.*|.*MILTON_KEYNES_PARK.*|.*SUBWAY.*|.*COFFEE.*|.*Espresso.*|.*D.*PARYS.*|.*Express Vend.*|.*MILTON KEYNES PARK.*', 'Coffee')

    # Clothing
    _add(r'.*NEXT.*|.*SPORTSDIRECT.*|.*T K MAXX.*|.*CLARKS.*|.*FOOT LOCKER.*|.*MATALAN.*|.*AMBROSE.*|.*MOTELROCKS.*|.*ACCESSORI.*|.*BOUX AVENUE.*|.*URBANOUTFITTERS.*|.*HOLLISTER.*|.*KAREN MILLEN.*|.*ETSY.*|.*NO LIMITZ.*|.*wbys.*|.*RIVER[ ]?ISLAND.*|.*HUGO[ ]?BOSS.*|.*FOOT LOCKER.*|.*OUTFIT.*|.*SCHOOLBLAZER.*|.*FASHION.*|.*PRIMARK.*|.*Schuh.*|.*Superdry.*|.*Zara.*|.*Nike.*|.*Cupshe.*|.*Moss.*|.*OH POLLY.*|.*Good Belly.*|.*MINT VELV.*|.*Vestiaire.*|.*ASOS.*|.*Trutex.*|.*SchoolUniform.*', 'Clothing')

    # Household
    _add(r'.*WILKO.*|.*B&M.*|.*CURRYS.*|.*THE RANGE.*|.*PETS.*|.*Hobbycraft.*|.*HOME BARGAINS.*|.*WH SMITH.*|.*VETERINARY.*|.*WICKES.*|.*HOMESENSE.*|.*ARGOS.*|.*POUNDLAND.*|.*JOHN[ ]?LEWIS.*|.*TIMPSON.*|.*DUNELM.*|.*HOMEBASE.*|.*IKEA.*|.*B[ ]?&[ ]?Q.*', 'Household')

    # Car
    _add(r'.*HALFORDS.*|.*MILLENNIUM.*|.*MERCEDE.*|.*INSURANCE.*|.*TYRE STORE.*|.*VEHICLE.*|.*A AND F MOTORS.*|.*JOHN R FORD.*', 'Car')

    # Amazon/Entertainment
    _add(r'.*Amazon[ ]?Prime.*|.*cinema.*|.*vue.*|.*Microsoft.*|.*Spotify.*|.*NOW.*|.*GAME.*', 'Amazon')
    _add(r'.*Amazon.*|.*AMZNMktplace.*|.*AMZ.*', 'Amazon')

    # Cash (match on effective_subcategory e.g. Cash Withdrawal)
    _add(r'.*', 'Cash', apply_when_cat="PersonalExpense", apply_when_extra={"field": "effective_subcategory", "regex": ".*CASH.*"})

    # Catch-all: Other for PersonalExpense
    _add(r'__CATCHALL_PERSONAL__', 'Other', strength="catch_all")

    return rules


# ---------------------------------------------------------------------------
# PHASE 4: OVERRIDE  (from 2.0 categorise_personal_spending unconditional overrides)
# These run last and overwrite Cat/Subcat regardless of prior values
# ---------------------------------------------------------------------------

def _build_override_rules():
    rules = []
    idx = 0

    def _add(pattern, cat=None, subcat=None, strength="strong"):
        nonlocal idx
        idx += 1
        outputs = {}
        if cat:
            outputs["category"] = cat
        if subcat:
            outputs["subcategory"] = subcat
        rules.append({
            "rule_id": f"override_{idx}",
            "order_index": idx,
            "phase": "override",
            "pattern": pattern,
            "outputs_json": json.dumps(outputs),
            "strength": strength,
            "apply_when_json": None,
            "banks_json": None,
            "accounts_json": None,
            "enabled": 1,
        })

    _add(r'.*SEQUENCE.*', cat='PropertyExpense')
    _add(r'.*MARKS&SPENCER.*', cat='PersonalExpense', subcat='M&S')
    _add(r'.*Chiropractic.*', cat='PersonalExpense', subcat='Rocco')
    _add(r'.*Thameslink.*|.*TSGN.*', cat='PersonalExpense', subcat='Rocco')
    _add(r'.*New County.*', cat='PersonalExpense', subcat='Garage')
    _add(r'.*Rocco.*', cat='PersonalExpense', subcat='Rocco')
    _add(r'.*Alessio.*', cat='PersonalExpense', subcat='Alessio')
    _add(r'.*Sofia.*', cat='PersonalExpense', subcat='Sofia')
    _add(r'.*Tesco.*', cat='PersonalExpense', subcat='Tesco')
    _add(r'.*Shell.*', cat='PersonalExpense', subcat='Garage')
    _add(r'.*Lidl.*', cat='PersonalExpense', subcat='LIDL')
    _add(r'.*HOME BARGAINS.*', cat='PersonalExpense', subcat='Household')
    _add(r'.*JD Sports.*', cat='PersonalExpense', subcat='Clothing')
    _add(r'.*Sports Direct.*', cat='PersonalExpense', subcat='Clothing')
    _add(r'.*BOOTS.*', cat='PersonalExpense', subcat='Pharmacy/Opticians/Dental')
    _add(r'.*Sainsbury.*', cat='PersonalExpense', subcat='Sainsburys')
    _add(r'.*INTEREST CHARGED.*', cat='OtherExpense')
    _add(r'.*BEDFORD EXPRESS.*', cat='PersonalExpense', subcat='Garage')
    _add(r'.*UNITY MUTUAL.*', cat='RegularPayment')
    _add(r'.*ALDI .*', cat='PersonalExpense', subcat='ALDI')
    _add(r'.*THE HUB DENTAL.*', cat='PersonalExpense', subcat='Pharmacy/Opticians/Dental')
    _add(r'.*HIGHLANDS PHARMACY.*', cat='PersonalExpense', subcat='Pharmacy/Opticians/Dental')
    _add(r'.*HOMESENSE.*', cat='PersonalExpense', subcat='Household')
    _add(r'.*NEXT RETAIL.*', cat='PersonalExpense', subcat='Clothing')
    _add(r'.*TK Maxx.*', cat='PersonalExpense', subcat='Clothing')
    _add(r'.*PAY AT PUMP.*', cat='PersonalExpense', subcat='Garage')
    _add(r'.*OPERATIVE FOOD.*', cat='PersonalExpense', subcat='COOP')
    _add(r'.*BP BP.*', cat='PersonalExpense', subcat='Garage')
    _add(r'.*Velvet.*|.*Mango.*|.*Primark.*', cat='PersonalExpense', subcat='Clothing')
    _add(r'.*MK COUNCIL.*', cat='PersonalExpense', subcat='Other')
    _add(r'.*SPECSAVERS.*', cat='PersonalExpense', subcat='Pharmacy/Opticians/Dental')
    _add(r'.*ATM.*', cat='PersonalExpense', subcat='Cash')
    _add(r'.*Wagamama.*|.*Costa.*', cat='PersonalExpense', subcat='EatingOut')
    _add(r'.*WAITROSE.*', cat='PersonalExpense', subcat='Waitrose')
    _add(r'.*BUDGENS.*', cat='PersonalExpense', subcat='Budgens')
    _add(r'.*MORRISONS.*', cat='PersonalExpense', subcat='Morrisons')
    _add(r'.*Ivana Valentino car.*', cat='RegularPayment', subcat='IVCar')
    _add(r'.*Bedford Hospital.*', cat='PersonalExpense', subcat='Other')
    _add(r'.*Ivana.*VALENTINO.*food.*|.*Ivana.*VALENTINO.*trf.*', cat='PersonalExpense', subcat='Ivana')
    _add(r'.*Rsa Capital Limite.*', cat='Interbank')
    _add(r'.*M Tucker.*BGC.*', cat='MTPayment')
    _add(r'.*TOGETHER COMMERCIA.*', cat='RegularPayment', subcat='SFLoan')
    _add(r'.*Ivana VALENTINO.*', subcat='Ivana')  # subcat-only override for Ivana

    return rules


# ---------------------------------------------------------------------------
# Properties seed data (from propertyidmap in 1.5)
# ---------------------------------------------------------------------------

PROPERTIES_SEED = [
    {"property_code": "321LON", "property_id": 2, "address": "321 London Road", "block": None, "freehold_entity": "V.T. Estates Ltd"},
    {"property_code": "F1321LON", "property_id": 1, "address": "Flat 1, 321 London Road", "block": "321 London Road", "freehold_entity": "V.T. Estates Ltd"},
    {"property_code": "F2321LON", "property_id": 14, "address": "Flat 2, 321 London Road", "block": "321 London Road", "freehold_entity": "V.T. Estates Ltd"},
    {"property_code": "F3321LON", "property_id": 3, "address": "Flat 3, 321 London Road", "block": "321 London Road", "freehold_entity": "V.T. Estates Ltd"},
    {"property_code": "F4321LON", "property_id": 4, "address": "Flat 4, 321 London Road", "block": "321 London Road", "freehold_entity": "V.T. Estates Ltd"},
    {"property_code": "169FAW", "property_id": 7, "address": "169 Fawcett Road", "block": "169 Fawcett Road", "freehold_entity": "V.T. Estates Ltd"},
    {"property_code": "F1169FAW", "property_id": 5, "address": "Flat 1, 169 Fawcett Road", "block": "169 Fawcett Road", "freehold_entity": "V.T. Estates Ltd"},
    {"property_code": "F2169FAW", "property_id": 6, "address": "Flat 2, 169 Fawcett Road", "block": "169 Fawcett Road", "freehold_entity": "V.T. Estates Ltd"},
    {"property_code": "F3169FAW", "property_id": 8, "address": "Flat 3, 169 Fawcett Road", "block": "169 Fawcett Road", "freehold_entity": "V.T. Estates Ltd"},
    {"property_code": "F1171FAW", "property_id": 73, "address": "Flat 1, 171 Fawcett Road", "block": "171 Fawcett Road", "freehold_entity": "V.T. Estates Ltd"},
    {"property_code": "F2171FAW", "property_id": 74, "address": "Flat 2, 171 Fawcett Road", "block": "171 Fawcett Road", "freehold_entity": "V.T. Estates Ltd"},
    {"property_code": "F3171FAW", "property_id": 75, "address": "Flat 3, 171 Fawcett Road", "block": "171 Fawcett Road", "freehold_entity": "V.T. Estates Ltd"},
    {"property_code": "163FRA", "property_id": 12, "address": "163 Fratton Road", "block": "163 Fratton Road", "freehold_entity": "Fratton Road Ltd"},
    {"property_code": "F2163FRA", "property_id": 9, "address": "Flat 2, 163 Fratton Road", "block": "163 Fratton Road", "freehold_entity": "Fratton Road Ltd"},
    {"property_code": "F3163FRA", "property_id": 10, "address": "Flat 3, 163 Fratton Road", "block": "163 Fratton Road", "freehold_entity": "Fratton Road Ltd"},
    {"property_code": "F4163FRA", "property_id": 11, "address": "Flat 4, 163 Fratton Road", "block": "163 Fratton Road", "freehold_entity": "Fratton Road Ltd"},
    {"property_code": "SHOP196KIN", "property_id": 17, "address": "Shop, 196 Kingston Road", "block": None, "freehold_entity": None},
    {"property_code": "196AKIN", "property_id": 15, "address": "196A Kingston Road", "block": None, "freehold_entity": None},
    {"property_code": "196BKIN", "property_id": 16, "address": "196B Kingston Road", "block": None, "freehold_entity": None},
    {"property_code": "23BHAM", "property_id": 19, "address": "23B Hampshire Terrace", "block": "23 Hampshire Terrace", "freehold_entity": "Lordswood Estates Ltd"},
    {"property_code": "23CHAM", "property_id": 34, "address": "23C Hampshire Terrace", "block": "23 Hampshire Terrace", "freehold_entity": "Lordswood Estates Ltd"},
    {"property_code": "23HAM", "property_id": 18, "address": "23 Hampshire Terrace", "block": "23 Hampshire Terrace", "freehold_entity": "Lordswood Estates Ltd"},
    {"property_code": "F58ALH", "property_id": 31, "address": "Flat 5, 8 Alhambra Road", "block": "8 Alhambra Road", "freehold_entity": "Alhambra Road Management Ltd"},
    {"property_code": "F68ALH", "property_id": 30, "address": "Flat 6, 8 Alhambra Road", "block": "8 Alhambra Road", "freehold_entity": "Alhambra Road Management Ltd"},
    {"property_code": "F78ALH", "property_id": 33, "address": "Flat 7, 8 Alhambra Road", "block": "8 Alhambra Road", "freehold_entity": "Alhambra Road Management Ltd"},
    {"property_code": "F88ALH", "property_id": 32, "address": "Flat 8, 8 Alhambra Road", "block": "8 Alhambra Road", "freehold_entity": "Alhambra Road Management Ltd"},
    {"property_code": "F1746ALH", "property_id": 26, "address": "Flat 17, 4-6 Alhambra Road", "block": "4-6 Alhambra Road", "freehold_entity": "Alhambra Road Management Ltd"},
    {"property_code": "F1846ALH", "property_id": 22, "address": "Flat 18, 4-6 Alhambra Road", "block": "4-6 Alhambra Road", "freehold_entity": "Alhambra Road Management Ltd"},
    {"property_code": "F1946ALH", "property_id": 21, "address": "Flat 19, 4-6 Alhambra Road", "block": "4-6 Alhambra Road", "freehold_entity": "Alhambra Road Management Ltd"},
    {"property_code": "F2046ALH", "property_id": 25, "address": "Flat 20, 4-6 Alhambra Road", "block": "4-6 Alhambra Road", "freehold_entity": "Alhambra Road Management Ltd"},
    {"property_code": "F2146ALH", "property_id": 28, "address": "Flat 21, 4-6 Alhambra Road", "block": "4-6 Alhambra Road", "freehold_entity": "Alhambra Road Management Ltd"},
    {"property_code": "F2246ALH", "property_id": 23, "address": "Flat 22, 4-6 Alhambra Road", "block": "4-6 Alhambra Road", "freehold_entity": "Alhambra Road Management Ltd"},
    {"property_code": "F2346ALH", "property_id": 27, "address": "Flat 23, 4-6 Alhambra Road", "block": "4-6 Alhambra Road", "freehold_entity": "Alhambra Road Management Ltd"},
    {"property_code": "F31214ALH", "property_id": 46, "address": "Flat 3, 12-14 Alhambra Road", "block": "12-14 Alhambra Road", "freehold_entity": "Alhambra Road Management Ltd"},
    {"property_code": "F41214ALH", "property_id": 52, "address": "Flat 4, 12-14 Alhambra Road", "block": "12-14 Alhambra Road", "freehold_entity": "Alhambra Road Management Ltd"},
    {"property_code": "F51214ALH", "property_id": 47, "address": "Flat 5, 12-14 Alhambra Road", "block": "12-14 Alhambra Road", "freehold_entity": "Alhambra Road Management Ltd"},
    {"property_code": "F71214ALH", "property_id": 48, "address": "Flat 7, 12-14 Alhambra Road", "block": "12-14 Alhambra Road", "freehold_entity": "Alhambra Road Management Ltd"},
    {"property_code": "F111214ALH", "property_id": 49, "address": "Flat 11, 12-14 Alhambra Road", "block": "12-14 Alhambra Road", "freehold_entity": "Alhambra Road Management Ltd"},
    {"property_code": "F101214ALH", "property_id": 53, "address": "Flat 10, 12-14 Alhambra Road", "block": "12-14 Alhambra Road", "freehold_entity": "Alhambra Road Management Ltd"},
    {"property_code": "F141214ALH", "property_id": 54, "address": "Flat 14, 12-14 Alhambra Road", "block": "12-14 Alhambra Road", "freehold_entity": "Alhambra Road Management Ltd"},
    {"property_code": "F161214ALH", "property_id": 55, "address": "Flat 16, 12-14 Alhambra Road", "block": "12-14 Alhambra Road", "freehold_entity": "Alhambra Road Management Ltd"},
    {"property_code": "F11618ALH", "property_id": 66, "address": "Flat 1, 16-18 Alhambra Road", "block": "16-18 Alhambra Road", "freehold_entity": "Alhambra Road Management Ltd"},
    {"property_code": "F31618ALH", "property_id": 67, "address": "Flat 3, 16-18 Alhambra Road", "block": "16-18 Alhambra Road", "freehold_entity": "Alhambra Road Management Ltd"},
    {"property_code": "F61618ALH", "property_id": 63, "address": "Flat 6, 16-18 Alhambra Road", "block": "16-18 Alhambra Road", "freehold_entity": "Alhambra Road Management Ltd"},
    {"property_code": "F71618ALH", "property_id": 68, "address": "Flat 7, 16-18 Alhambra Road", "block": "16-18 Alhambra Road", "freehold_entity": "Alhambra Road Management Ltd"},
    {"property_code": "F111618ALH", "property_id": 64, "address": "Flat 11, 16-18 Alhambra Road", "block": "16-18 Alhambra Road", "freehold_entity": "Alhambra Road Management Ltd"},
    {"property_code": "F121618ALH", "property_id": 71, "address": "Flat 12, 16-18 Alhambra Road", "block": "16-18 Alhambra Road", "freehold_entity": "Alhambra Road Management Ltd"},
    {"property_code": "F131618ALH", "property_id": 70, "address": "Flat 13, 16-18 Alhambra Road", "block": "16-18 Alhambra Road", "freehold_entity": "Alhambra Road Management Ltd"},
    {"property_code": "F161618ALH", "property_id": 65, "address": "Flat 16, 16-18 Alhambra Road", "block": "16-18 Alhambra Road", "freehold_entity": "Alhambra Road Management Ltd"},
    {"property_code": "RSA", "property_id": 81, "address": "RSA Capital Ltd (company costs)", "block": None, "freehold_entity": None},
    {"property_code": "171FAW", "property_id": None, "address": "171 Fawcett Road", "block": "171 Fawcett Road", "freehold_entity": "V.T. Estates Ltd"},
]


def get_all_rules():
    """Return all rules from all phases in a flat list."""
    return (
        _build_property_rules()
        + _build_category_rules()
        + _build_subcategory_rules()
        + _build_override_rules()
    )


def get_categories_and_subcategories():
    """Return (sorted list of category names, sorted list of subcategory names) from all rules.

    Used to populate Excel validation dropdowns; users can add new values in the Lists sheet.
    """
    categories = set()
    subcategories = set()
    for r in get_all_rules():
        try:
            out = json.loads(r.get("outputs_json") or "{}")
            if out.get("category"):
                categories.add(out["category"])
            if out.get("subcategory"):
                subcategories.add(out["subcategory"])
        except (json.JSONDecodeError, TypeError):
            pass
    return (sorted(categories), sorted(subcategories))
