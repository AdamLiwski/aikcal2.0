import os
import json
from pathlib import Path

# --- Konfiguracja ---
DATA_FOLDER = "baza2"  # Nazwa folderu z Twoimi plikami JSON
OUTPUT_MASTER_FILE = "master_dane_wzbogacone2.json"
OUTPUT_MISSING_FILE = "master_dane_wzbogaconebez.json"

def create_master_file():
    print("--- Rozpoczynam proces tworzenia głównego pliku danych ---")

    if not os.path.isdir(DATA_FOLDER):
        print(f"BŁĄD: Folder '{DATA_FOLDER}' nie istnieje.")
        return

    all_dishes_dict = {}
    all_products_dict = {}

    # --- Krok 1: Wczytanie wszystkich plików i usunięcie duplikatów ---
    print(f"1/4: Wczytywanie danych z folderu '{DATA_FOLDER}'...")
    for filename in os.listdir(DATA_FOLDER):
        if filename.endswith('.json'):
            filepath = os.path.join(DATA_FOLDER, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                try:
                    content = json.load(f)
                    for item in content:
                        item_name = item.get('name')
                        if not item_name: continue
                        
                        # Rozdzielamy dania od produktów, od razu usuwając duplikaty
                        if "deconstruction" in item:
                            all_dishes_dict[item_name.lower()] = item
                        elif "nutrients_per_100g" in item or "nutrients_per_100ml" in item:
                            all_products_dict[item_name.lower()] = item
                except json.JSONDecodeError:
                    print(f"  OSTRZEŻENIE: Pominięto plik '{filename}' z powodu błędu składni JSON.")

    print(f"-> Wczytano {len(all_dishes_dict)} unikalnych dań i {len(all_products_dict)} unikalnych produktów.")

    # --- Krok 2: Weryfikacja - szukanie brakujących składników ---
    print("2/4: Weryfikowanie składników w przepisach...")
    product_names_set = set(all_products_dict.keys())
    missing_ingredients_set = set()

    for dish_data in all_dishes_dict.values():
        for ingredient in dish_data.get("deconstruction", []):
            ingredient_name = ingredient.get("ingredient_name")
            if ingredient_name and ingredient_name.lower() not in product_names_set:
                missing_ingredients_set.add(ingredient_name)

    # --- Krok 3: Generowanie pliku z brakującymi produktami ---
    if missing_ingredients_set:
        print(f"\n❗ UWAGA: Znaleziono {len(missing_ingredients_set)} brakujących produktów podstawowych!")
        print(f"3/4: Tworzenie pliku '{OUTPUT_MISSING_FILE}'...")
        
        missing_list = [{"name": name, "category": "Produkty Podstawowe"} for name in sorted(list(missing_ingredients_set))]
        with open(OUTPUT_MISSING_FILE, 'w', encoding='utf-8') as f:
            json.dump(missing_list, f, ensure_ascii=False, indent=2)
        print(f"-> Plik '{OUTPUT_MISSING_FILE}' został utworzony. Uzupełnij go i umieść w folderze z danymi.")
    else:
        print("\n✅ Weryfikacja zakończona pomyślnie! Nie znaleziono brakujących składników.")

    # --- Krok 4: Tworzenie jednego, głównego pliku z kompletnymi danymi ---
    print(f"4/4: Tworzenie głównego pliku '{OUTPUT_MASTER_FILE}'...")
    
    # Łączymy w jeden plik tylko te dane, które są kompletne
    consolidated_data = list(all_dishes_dict.values()) + list(all_products_dict.values())
    
    with open(OUTPUT_MASTER_FILE, 'w', encoding='utf-8') as f:
        json.dump(consolidated_data, f, ensure_ascii=False, indent=2)

    print(f"-> Utworzono plik '{OUTPUT_MASTER_FILE}' zawierający {len(consolidated_data)} pozycji.")
    print("\n--- Proces zakończony! ---")

if __name__ == "__main__":
    create_master_file()