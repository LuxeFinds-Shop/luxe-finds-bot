# lager.py – minimale Lager-Verwaltung für LuxeFinds Bot

# Dummy-Daten – du kannst das später mit echter DB oder JSON ersetzen
_lager = {
    "Blueberry Raspberry Cherry Cola Ice": {"kategorie": "60K", "preis": 34.5, "menge": 78},
    "50K Vape": {"kategorie": "50K", "preis": 29.9, "menge": 120},
    # Füge hier deine echten Produkte hinzu, z. B.:
    # "Produkt Name": {"kategorie": "60K", "preis": 34.5, "menge": 50},
}

def alle():
    """Gibt alle Produkte zurück"""
    return _lager

def holen(produkt_name):
    """Gibt Infos zu einem Produkt zurück oder None"""
    return _lager.get(produkt_name)

def reduzieren(produkt_name, menge):
    """Reduziert die Lagermenge"""
    if produkt_name in _lager:
        if _lager[produkt_name]["menge"] >= menge:
            _lager[produkt_name]["menge"] -= menge
            print(f"[LAGER] Reduziert: {produkt_name} um {menge} → neu: {_lager[produkt_name]['menge']}")
        else:
            raise Exception(f"Nicht genug auf Lager: {produkt_name} (nur {_lager[produkt_name]['menge']} vorhanden)")
    else:
        raise Exception(f"Produkt nicht gefunden: {produkt_name}")

def erhoehen(produkt_name, menge):
    """Erhöht die Lagermenge (z. B. bei Storno/Abbruch)"""
    if produkt_name in _lager:
        _lager[produkt_name]["menge"] += menge
        print(f"[LAGER] Erhöht: {produkt_name} um {menge} → neu: {_lager[produkt_name]['menge']}")
    else:
        print(f"[WARNUNG] Produkt {produkt_name} nicht im Lager – ignoriere Erhöhung")
