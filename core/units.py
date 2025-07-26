"""
Moduł odpowiedzialny za standaryzację jednostek i nazw produktów.

Ten plik zawiera logikę do:
1.  Normalizacji nazw produktów (obsługa synonimów i częstych błędów).
2.  Konwersji różnych jednostek miar na podstawowe jednostki metryczne (gramy 'g' lub mililitry 'ml').
3.  Inteligentnego domyślania się wagi na podstawie średniej wagi produktu,
    gdy jednostka to "sztuka" lub nie jest standardową jednostką miary.
"""
from typing import Tuple, Union, Optional

# Zakładając, że ProductState jest w pliku enums.py w tym samym katalogu
try:
    from .enums import ProductState
except ImportError:
    from enum import Enum
    class ProductState(Enum):
        SOLID = "solid"
        LIQUID = "liquid"

# --- Słownik Synonimów i Częstych Błędów ---
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
}

# --- NOWA ZMIANA: Lista wszystkich znanych, standardowych jednostek ---
KNOWN_UNITS = [
    # Waga
    "g", "gram", "gramy",
    "dag", "dkg", "dekagram",
    "kg", "kilogram", "kilogramy",
    # Objętość
    "ml", "mililitr", "mililitry",
    "l", "litr", "litry",
    # Jednostki kuchenne i sztukowe
    "szklanka", "szklanki",
    "łyżka", "łyżki",
    "łyżeczka", "łyżeczki",
    "talerz", "miska", "plaster", "kromka", "garść",
    "sztuka", "sztuki", "szt.", "szt"
]

def normalize_name(name: str) -> str:
    """
    Normalizuje nazwę produktu: zamienia na małe litery i sprawdza w słowniku synonimów.
    """
    if not isinstance(name, str):
        return name
    
    name_lower = name.lower().strip()
    
    if name_lower.endswith(('i', 'y')):
        name_singular = name_lower[:-1]
        if name_singular in SYNONYM_MAP:
             return SYNONYM_MAP[name_singular]

    return SYNONYM_MAP.get(name_lower, name_lower)

# --- NOWA, ZMODYFIKOWANA FUNKCJA ---
def standardize_unit(
    amount: float,
    unit: str,
    state: ProductState,
    average_weight_g: Optional[float] = None
) -> Tuple[float, str]:
    """
    Standaryzuje jednostkę na gramy lub mililitry.

    Jeśli jednostka nie jest standardową miarą (np. 'jabłko') lub jest to 'sztuka',
    a produkt ma zdefiniowaną średnią wagę, używa tej wagi do konwersji.
    W przeciwnym razie stosuje standardowe przeliczniki dla znanych jednostek.
    """
    unit_lower = str(unit).lower().strip()

    # --- POCZĄTEK NOWEJ, INTELIGENTNEJ LOGIKI ---
    is_standard_unit = unit_lower in KNOWN_UNITS
    is_piece_unit = unit_lower in ["sztuka", "sztuki", "szt.", "szt"]

    # Jeśli jednostka nie jest standardowa (np. unit='jabłko') LUB jest to 'sztuka',
    # I mamy podaną średnią wagę, to używamy jej do konwersji.
    if (not is_standard_unit or is_piece_unit) and average_weight_g is not None and average_weight_g > 0:
        # Zakładamy, że użytkownik miał na myśli 'amount' sztuk produktu.
        return amount * average_weight_g, "g"
    # --- KONIEC NOWEJ LOGIKI ---

    # --- Obsługa standardowych jednostek (logika zachowana, ale w nowej formie) ---
    if state == ProductState.SOLID:
        if unit_lower in ["g", "gram", "gramy"]: return amount, "g"
        if unit_lower in ["dag", "dkg", "dekagram"]: return amount * 10, "g"
        if unit_lower in ["kg", "kilogram", "kilogramy"]: return amount * 1000, "g"
        if unit_lower in ["szklanka", "szklanki"]: return amount * 150.0, "g"
        if unit_lower in ["łyżka", "łyżki"]: return amount * 15.0, "g"
        if unit_lower in ["łyżeczka", "łyżeczki"]: return amount * 5.0, "g"
        if unit_lower == "talerz": return amount * 200.0, "g"
        if unit_lower == "miska": return amount * 180.0, "g"
        if unit_lower == "plaster": return amount * 20.0, "g"
        if unit_lower == "kromka": return amount * 35.0, "g"
        if unit_lower == "garść": return amount * 30.0, "g"

    elif state == ProductState.LIQUID:
        if unit_lower in ["ml", "mililitr", "mililitry"]: return amount, "ml"
        if unit_lower in ["l", "litr", "litry"]: return amount * 1000, "ml"
        if unit_lower in ["szklanka", "szklanki"]: return amount * 250.0, "ml"
        if unit_lower in ["łyżka", "łyżki"]: return amount * 15.0, "ml"
        if unit_lower in ["łyżeczka", "łyżeczki"]: return amount * 5.0, "ml"
        if unit_lower == "talerz": return amount * 300.0, "ml"
        if unit_lower == "miska": return amount * 400.0, "ml"

    # Jeśli nie udało się dopasować żadnej reguły, zgłaszamy błąd.
    # Dzieje się tak, gdy jednostka jest niestandardowa (np. "jabłko"),
    # ale nie podano dla niej average_weight_g.
    raise ValueError(
        f"Nie można przetworzyć jednostki '{unit}' dla produktu o stanie '{state.value}'. "
        f"Jednostka jest nieznana lub wymaga podania średniej wagi (average_weight_g)."
    )
