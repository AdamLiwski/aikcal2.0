import os
import json
import time
import re
from dotenv import load_dotenv
import google.generativeai as genai

# --- Konfiguracja ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

INPUT_FILE = "master_dane.json"
OUTPUT_FILE = "master_dane_wzbogacone.json"

enrichment_prompt_template = """
Jesteś encyklopedią żywienia. Dla podanego produktu spożywczego, określ jego typowy stan skupienia oraz średnią wagę jednej sztuki.
Odpowiedz ZAWSZE i TYLKO w formacie obiektu JSON z kluczami: "state" ("solid" lub "liquid") oraz "average_weight_g" (liczba całkowita).
ZASADY:
1.  STAN SKUPIENIA: Dla produktów płynnych, zup, sosów użyj "liquid". Dla wszystkich innych użyj "solid".
2.  ŚREDNIA WAGA: Podaj typową wagę w gramach dla JEDNEJ SZTUKI produktu (np. dla jednego jabłka, jednego jajka). Jeśli produkt nie jest liczony na sztuki (np. mąka, ryż, sól), wpisz w to pole wartość 0.
Przeanalizuj produkt: "{product_name}"
"""

def clean_json_response(text: str) -> str:
    match = text.strip().find('{')
    if match != -1: text = text[match:]
    match = text.strip().rfind('}')
    if match != -1: text = text[:match+1]
    return text

def enrich_master_file():
    if not GEMINI_API_KEY:
        print("BŁĄD: Brak klucza GEMINI_API_KEY w pliku .env"); return

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash-latest')

    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            master_data = json.load(f)
        print(f"Wczytano {len(master_data)} pozycji z pliku '{INPUT_FILE}'.")
    except Exception as e:
        print(f"BŁĄD: Nie można wczytać pliku '{INPUT_FILE}'. Szczegóły: {e}"); return

    # --- NOWA LOGIKA: Inteligentne wznawianie ---
    enriched_data = []
    processed_names = set()
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            try:
                enriched_data = json.load(f)
                processed_names = {item.get('name') for item in enriched_data}
                print(f"Znaleziono istniejący plik wyjściowy. Wznowiono pracę. Przetworzono już {len(processed_names)} pozycji.")
            except json.JSONDecodeError:
                print("OSTRZEŻENIE: Plik wyjściowy jest uszkodzony. Zaczynam od nowa.")
    
    items_to_process = [item for item in master_data if item.get('name') not in processed_names]
    
    if not items_to_process:
        print("Wszystkie pozycje zostały już wzbogacone. Kończę pracę.")
        return

    print(f"Pozostało {len(items_to_process)} pozycji do przetworzenia.")

    for i, item in enumerate(items_to_process):
        product_name = item.get('name')
        print(f"-> Przetwarzam: '{product_name}' ({i+1}/{len(items_to_process)})...")
        
        try:
            prompt = enrichment_prompt_template.format(product_name=product_name)
            response = model.generate_content(prompt)
            enrichment_data = json.loads(clean_json_response(response.text))
            
            item['state'] = enrichment_data.get('state', 'solid')
            if "deconstruction" not in item:
                item['average_weight_g'] = enrichment_data.get('average_weight_g', 0)
            
            enriched_data.append(item)

        except Exception as e:
            # NOWA LOGIKA: Obsługa błędu limitu API
            if "429" in str(e): # Proste sprawdzenie, czy błąd to "Too Many Requests"
                print("  Osiągnięto limit zapytań API. Czekam 60 sekund...")
                time.sleep(60)
                # Spróbuj ponownie przetworzyć ten sam element (opcjonalne, można dodać)
            else:
                print(f"  BŁĄD przy przetwarzaniu '{product_name}'. Dodaję wpis bez wzbogacenia. Szczegóły: {e}")
                enriched_data.append(item)
        
        # Zapisuj postęp co 10 pozycji, aby był bezpieczny
        if (i + 1) % 10 == 0:
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(enriched_data, f, ensure_ascii=False, indent=2)

    # Zapis finalnego pliku na sam koniec
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(enriched_data, f, ensure_ascii=False, indent=2)

    print(f"\n--- Zakończono! Wzbogacone dane zostały zapisane w pliku '{OUTPUT_FILE}'. ---")

if __name__ == "__main__":
    enrich_master_file()