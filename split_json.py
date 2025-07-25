import json
import math

# --- Konfiguracja ---
INPUT_FILE = "brakujace_produkty.json" # Nazwa Twojego dużego pliku
NUMBER_OF_FILES = 8                    # Na ile plików chcesz go podzielić

def split_json_file():
    """
    Dzieli duży plik JSON (zawierający listę) na mniejsze części.
    """
    try:
        # Wczytaj oryginalny, duży plik
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            print("BŁĄD: Plik wejściowy nie zawiera listy JSON.")
            return

        print(f"Wczytano {len(data)} produktów z pliku '{INPUT_FILE}'.")

        # Oblicz, ile produktów powinno znaleźć się w każdym mniejszym pliku
        items_per_file = math.ceil(len(data) / NUMBER_OF_FILES)
        
        # Pętla do tworzenia nowych plików
        for i in range(NUMBER_OF_FILES):
            start_index = i * items_per_file
            end_index = start_index + items_per_file
            chunk = data[start_index:end_index]
            
            # Jeśli "chunk" jest pusty, nie twórz pliku
            if not chunk:
                continue

            output_filename = f"part_{i+1}.json"
            
            # Zapisz "kawałek" danych do nowego pliku
            with open(output_filename, 'w', encoding='utf-8') as f:
                json.dump(chunk, f, ensure_ascii=False, indent=2)
            
            print(f"-> Utworzono plik '{output_filename}' z {len(chunk)} produktami.")
            
        print("\n--- Zakończono! Plik został pomyślnie podzielony. ---")

    except FileNotFoundError:
        print(f"BŁĄD: Nie znaleziono pliku '{INPUT_FILE}'. Upewnij się, że jest w tym samym folderze co skrypt.")
    except Exception as e:
        print(f"Wystąpił nieoczekiwany błąd: {e}")

if __name__ == "__main__":
    split_json_file()