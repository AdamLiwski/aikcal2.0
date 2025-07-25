import os
import json
from pathlib import Path

# --- Konfiguracja ---
DATA_FOLDER = "baza" # Nazwa folderu z Twoimi plikami JSON
OUTPUT_MISSING_FILE = "brakujace_produkty.json"

def main():
    print("--- ETAP 1: Konsolidacja i Weryfikacja Danych ---")

    if not os.path.isdir(DATA_FOLDER):
        print(f"BŁĄD: Folder '{DATA_FOLDER}' nie istnieje. Upewnij się, że jest w tym samym miejscu co skrypt.")
        return

    all_dishes_dict = {}
    all_products_dict = {}

    # --- Krok 1: Wczytanie wszystkich plików i wstępna deduplikacja ---
    print(f"1/3: Wczytywanie i segregowanie danych z folderu '{DATA_FOLDER}'...")
    for filename in os.listdir(DATA_FOLDER):
        if filename.endswith('.json'):
            filepath = os.path.join(DATA_FOLDER, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                try:
                    content = json.load(f)
                    for item in content:
                        item_name = item.get('name')
                        if not item_name: continue
                        
                        if "deconstruction" in item:
                            all_dishes_dict[item_name.lower()] = item
                        elif "nutrients_per_100g" in item:
                            all_products_dict[item_name.lower()] = item
                except json.JSONDecodeError:
                    print(f"  OSTRZEŻENIE: Plik '{filename}' zawiera błąd składni JSON i został pominięty.")

    print(f"-> Wczytano {len(all_dishes_dict)} unikalnych dań i {len(all_products_dict)} unikalnych produktów podstawowych.")

    # --- Krok 2: Weryfikacja spójności - szukanie brakujących składników ---
    print("2/3: Weryfikowanie składników w przepisach...")
    
    product_names_set = set(all_products_dict.keys())
    missing_ingredients_set = set()

    for dish_data in all_dishes_dict.values():
        for ingredient in dish_data.get("deconstruction", []):
            ingredient_name = ingredient.get("ingredient_name")
            if ingredient_name and ingredient_name.lower() not in product_names_set:
                missing_ingredients_set.add(ingredient_name)

    # --- Krok 3: Generowanie raportu i pliku z brakującymi produktami ---
    if not missing_ingredients_set:
        print("\n✅ Weryfikacja zakończona pomyślnie! Wszystkie składniki dań istnieją na liście produktów podstawowych.")
    else:
        print(f"\n❗ UWAGA: Znaleziono {len(missing_ingredients_set)} brakujących produktów podstawowych!")
        print(f"3/3: Tworzenie pliku '{OUTPUT_MISSING_FILE}' z listą brakujących produktów...")
        
        missing_list = [{"name": name, "category": "Produkty Podstawowe", "nutrients_per_100g": {}} for name in sorted(list(missing_ingredients_set))]
        
        with open(OUTPUT_MISSING_FILE, 'w', encoding='utf-8') as f:
            json.dump(missing_list, f, ensure_ascii=False, indent=2)
            
        print(f"-> Plik '{OUTPUT_MISSING_FILE}' został pomyślnie utworzony.")
        print("-> Twoje zadanie: uzupełnij ten plik o wartości odżywcze, a następnie umieść go w folderze z danymi.")

if __name__ == "__main__":
    main()