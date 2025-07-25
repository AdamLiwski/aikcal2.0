"""
Moduł odpowiedzialny za standaryzację jednostek i nazw produktów.

Ten plik zawiera logikę do:
1.  Normalizacji nazw produktów (obsługa synonimów i częstych błędów).
2.  Konwersji różnych jednostek miar na podstawowe jednostki metryczne (gramy 'g' lub mililitry 'ml').
3.  Kontekstowej interpretacji jednostek (np. "talerz" inaczej dla zupy, inaczej dla ziemniaków).
"""
from typing import Tuple, Union
from .enums import ProductState

# --- Słownik Synonimów i Częstych Błędów ---
# Klucz: fraza wpisana przez użytkownika (lub jej część)
# Wartość: kanoniczna, poprawna nazwa, której będziemy szukać w bazie
SYNONYM_MAP = {
    "dewolaj": "kotlet de volaille",
    "devolay": "kotlet de volaille",
    "kotlet po kijowsku": "kotlet de volaille",
    "pałka z kurczaka": "podudzie z kurczaka",
    "nóżka z kurczaka": "podudzie z kurczaka",
    "schabowy": "kotlet schabowy",
    "mielony": "kotlet mielony",
    "talez": "talerz",
    "plasterek": "plaster",
    # ... w przyszłości można tu dodawać więcej synonimów
}

# --- NOWY, KONTEKSTOWY Słownik Konwersji Jednostek ---
# Struktura: { jednostka: { stan_skupienia: (jednostka_bazowa, mnożnik_gram/ml) } }
UNIT_CONVERSIONS = {
    # Jednostki wagowe (niezależne od stanu)
    "g": {"solid": ("g", 1.0), "liquid": ("g", 1.0)},
    "gram": {"solid": ("g", 1.0), "liquid": ("g", 1.0)},
    "kg": {"solid": ("g", 1000.0), "liquid": ("g", 1000.0)},
    "kilogram": {"solid": ("g", 1000.0), "liquid": ("g", 1000.0)},
    "dag": {"solid": ("g", 10.0), "liquid": ("g", 10.0)},

    # Jednostki objętościowe (niezależne od stanu)
    "ml": {"solid": ("ml", 1.0), "liquid": ("ml", 1.0)},
    "l": {"solid": ("ml", 1000.0), "liquid": ("ml", 1000.0)},
    "litr": {"solid": ("ml", 1000.0), "liquid": ("ml", 1000.0)},
    
    # Jednostki kuchenne (zależne od stanu)
    "szklanka": {"solid": ("g", 150.0), "liquid": ("ml", 250.0)}, # 150g dla mąki/cukru, 250ml dla płynów
    "łyżka": {"solid": ("g", 15.0), "liquid": ("ml", 15.0)},
    "łyżeczka": {"solid": ("g", 5.0), "liquid": ("ml", 5.0)},
    
    # NOWOŚĆ: Jednostki kontekstowe
    "talerz": {"solid": ("g", 200.0), "liquid": ("ml", 300.0)},
    "miska": {"solid": ("g", 180.0), "liquid": ("ml", 400.0)},

    # Jednostki "sztukowe" (traktowane jako waga)
    "sztuka": {"solid": ("g", 120.0), "liquid": ("g", 120.0)}, # Domyślna waga dla 1 sztuki (np. owoc)
    "szt.": {"solid": ("g", 120.0), "liquid": ("g", 120.0)},
    "jajko": {"solid": ("g", 55.0), "liquid": ("g", 55.0)},
    "plaster": {"solid": ("g", 20.0), "liquid": ("g", 20.0)},
    "kromka": {"solid": ("g", 35.0), "liquid": ("g", 35.0)},
    "garść": {"solid": ("g", 30.0), "liquid": ("g", 30.0)}, # Np. garść orzechów
}

def normalize_name(name: str) -> str:
    """
    Normalizuje nazwę produktu: zamienia na małe litery i sprawdza w słowniku synonimów.
    """
    if not isinstance(name, str):
        return name
    
    name_lower = name.lower().strip()
    
    # Prosta normalizacja liczby mnogiej (można rozbudować)
    if name_lower.endswith(('i', 'y')):
        name_singular = name_lower[:-1]
        if name_singular in SYNONYM_MAP:
             return SYNONYM_MAP[name_singular]

    return SYNONYM_MAP.get(name_lower, name_lower)


def standardize_unit(amount: float, unit: str, state: ProductState) -> Tuple[float, str]:
    """
    Standaryzuje podaną ilość i jednostkę do jednostki bazowej (g lub ml),
    uwzględniając stan skupienia produktu (solid/liquid).
    """
    if not isinstance(unit, str):
        return amount, str(unit)

    unit_lower = unit.lower().strip()
    
    # Normalizacja liczby mnogiej (prosta wersja)
    if unit_lower.endswith(('i', 'y', 'ek')):
        unit_singular = unit_lower[:-1]
        if unit_singular in UNIT_CONVERSIONS:
            unit_lower = unit_singular
    if unit_lower.endswith('ka'):
        unit_singular = unit_lower[:-2]
        if unit_singular in UNIT_CONVERSIONS:
            unit_lower = unit_singular

    conversion_rules = UNIT_CONVERSIONS.get(unit_lower)
    
    if conversion_rules:
        # Wybierz przelicznik na podstawie stanu skupienia
        if state == ProductState.LIQUID and 'liquid' in conversion_rules:
            base_unit, multiplier = conversion_rules['liquid']
        else: # Domyślnie lub dla ProductState.SOLID
            base_unit, multiplier = conversion_rules.get('solid', ('g', 1.0))
        
        standardized_amount = amount * multiplier
        return standardized_amount, base_unit
    else:
        print(f"Ostrzeżenie: Nieznana jednostka '{unit}'. Nie dokonano standaryzacji.")
        return amount, unit_lower