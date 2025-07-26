import google.generativeai as genai
import os
import json
import re
from typing import List, Dict, Any, Optional
from PIL import Image
import io
import base64
from datetime import date
from sqlalchemy.orm import Session
from fastapi import HTTPException

from . import crud, models, schemas, units
from .db import SessionLocal
from .enums import MealCategory, ProductState

# --- Konfiguracja ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY nie został ustawiony w zmiennych środowiskowych.")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash-latest')

# --- Funkcje Pomocnicze ---

def _clean_json_response(text: str) -> str:
    """Czysci odpowiedz AI, aby wyodrebnic czysty JSON."""
    match = re.search(r"```json\s*([\s\S]*?)\s*```", text)
    if match:
        return match.group(1).strip()
    return text.strip()

async def _get_ai_response(prompt: str, image: Optional[Image.Image] = None) -> str:
    """Wysyła zapytanie (tekst i/lub obraz) do modelu Gemini i zwraca odpowiedź tekstową."""
    try:
        content_to_send = [prompt, image] if image else [prompt]
        print(f"DEBUG: Wysyłanie zapytania do Gemini. Prompt: {prompt[:100]}...")
        response = await model.generate_content_async(content_to_send)
        print("DEBUG: Otrzymano odpowiedź z Gemini.")
        return response.text if response.text else ""
    except Exception as e:
        print(f"BŁĄD KRYTYCZNY podczas komunikacji z API Gemini: {e}")
        return ""

# --- NOWA, GŁÓWNA LOGIKA ANALIZY POSIŁKÓW ---

async def analyze_meal_entry(text: Optional[str] = None, image_base64: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Główna, wieloetapowa funkcja do analizy posiłku, działająca w logice "Cache-First".
    """
    if not text and not image_base64:
        return None

    db = SessionLocal()
    try:
        # KROK 1: Inteligentne parsowanie zapytania
        parsed_query = await _parse_user_query(text, image_base64)
        if not parsed_query or not parsed_query.get("name"):
            return None

        product_name = parsed_query["name"]
        quantity = parsed_query["quantity"]
        unit = parsed_query["unit"]

        # KROK 2: Wyszukiwanie w lokalnej bazie (Cache-First)
        # Najpierw szukamy dania złożonego
        db_dish = crud.get_dish_by_name(db, name=product_name)
        if db_dish:
            print(f"DEBUG: Cache HIT (Dish)! Znaleziono '{product_name}' w bazie dań.")
            return await _calculate_nutrients_for_dish(db, db_dish, quantity, unit)
        
        # Jeśli nie ma dania, szukamy produktu podstawowego
        db_product = crud.get_product_by_name(db, name=product_name)
        if db_product:
            print(f"DEBUG: Cache HIT (Product)! Znaleziono '{product_name}' w bazie produktów.")
            return _calculate_nutrients_for_product(db_product, quantity, unit)

        # KROK 3: Jeśli nie ma w cache (Cache Miss) - uruchom mechanizm "uczenia się"
        print(f"DEBUG: Cache MISS! Uruchamiam mechanizm uczenia dla '{product_name}'.")
        return await _learn_new_dish(db, product_name, quantity, unit)

    finally:
        db.close()

async def _parse_user_query(text: Optional[str], image_base64: Optional[str]) -> Dict[str, Any]:
    """Przetwarza zapytanie użytkownika (tekst lub obraz) na ustrukturyzowane dane."""
    quantity = 1.0
    unit = "szt."
    product_name = text.strip() if text else ""

    if image_base64:
        image_prompt = """
        Przeanalizuj to zdjęcie. Odpowiedz TYLKO w formacie JSON z kluczami: "name" (nazwa potrawy), "quantity" (oszacowana waga lub objętość) i "unit" (jednostka, "g" dla ciał stałych lub "ml" dla płynów).

        Przykład dla ciała stałego: {"name": "Jajecznica na boczku", "quantity": 180, "unit": "g"}
        Przykład dla płynu: {"name": "Zupa pomidorowa", "quantity": 300, "unit": "ml"}
        """
        try:
            image_data = base64.b64decode(image_base64.split(',')[1])
            image = Image.open(io.BytesIO(image_data))
            response_text = await _get_ai_response(image_prompt, image)
            parsed_image = json.loads(_clean_json_response(response_text))
            
            product_name = parsed_image.get("name", "Produkt ze zdjęcia")
            quantity = parsed_image.get("quantity", 100.0)
            unit = parsed_image.get("unit", "g")
            
            # Jeśli jest też tekst, użyj go zamiast nazwy z AI
            if text:
                product_name = text.strip()

        except Exception as e:
            print(f"BŁĄD: Podczas analizy obrazu: {e}")
            return {} if not text else {"quantity": 1.0, "unit": "szt.", "name": text.strip()}

    if not product_name:
        return {}
    
    # Dalsze parsowanie tekstu (jeśli nie było obrazu lub był podany tekst)
    if not image_base64 or text:
        match = re.match(r"^\s*(\d+[\.,]?\d*)\s*([a-zA-ZżźćńółęąśŻŹĆŃÓŁĘĄŚ\.]+)\s*(.*)", product_name)
        if match:
            try:
                quantity = float(match.group(1).replace(',', '.'))
                unit = match.group(2)
                product_name = match.group(3).strip() if match.group(3) else unit
            except (ValueError, IndexError):
                pass
    
    normalized_name = units.normalize_name(product_name)
    return {"quantity": quantity, "unit": unit, "name": normalized_name, "original_text": product_name}


async def _calculate_nutrients_for_dish(db: Session, dish: models.Dish, quantity: float, unit: str):
    """Oblicza wartości odżywcze dla istniejącego dania na podstawie jego przepisu."""
    total_base_weight = sum(ing.weight_g for ing in dish.ingredients)
    
    # Określ stan skupienia dania na podstawie jego składników (np. jeśli dominują płyny)
    # Prosta heurystyka: jeśli więcej niż 50% wagi to płyny, całe danie jest płynne
    liquid_weight = sum(ing.weight_g for ing in dish.ingredients if ing.product.state == ProductState.LIQUID)
    dish_state = ProductState.LIQUID if total_base_weight > 0 and (liquid_weight / total_base_weight) > 0.5 else ProductState.SOLID

    # Użyj naszego inteligentnego przelicznika, aby uzyskać wagę porcji użytkownika w gramach
    user_portion_grams, _ = units.standardize_unit(quantity, unit, dish_state)

    scaling_factor = user_portion_grams / total_base_weight if total_base_weight > 0 else 0
    
    total_nutrients = {"calories": 0.0, "protein": 0.0, "fat": 0.0, "carbs": 0.0}
    for ingredient in dish.ingredients:
        if ingredient.product and ingredient.product.nutrients:
            factor = ingredient.weight_g / 100.0
            total_nutrients["calories"] += ingredient.product.nutrients.get("calories", 0) * factor
            total_nutrients["protein"] += ingredient.product.nutrients.get("protein", 0) * factor
            total_nutrients["fat"] += ingredient.product.nutrients.get("fat", 0) * factor
            total_nutrients["carbs"] += ingredient.product.nutrients.get("carbs", 0) * factor

    final_nutrients = {key: round(val * scaling_factor, 1) for key, val in total_nutrients.items()}
    final_nutrients['calories'] = round(final_nutrients['calories'])

    deconstruction_details = [{
        "name": ing.product.name,
        "quantity_grams": round(ing.weight_g * scaling_factor),
        "calories": round(ing.product.nutrients.get("calories", 0) * (ing.weight_g * scaling_factor / 100.0)) if ing.product.nutrients else 0,
    } for ing in dish.ingredients]

    aggregated_meal = {
        "name": f"{dish.name}",
        "quantity_grams": round(user_portion_grams),
        "display_quantity_text": f"{quantity} {unit}",
        **final_nutrients
    }
    return {"aggregated_meal": aggregated_meal, "deconstruction_details": deconstruction_details}


def _calculate_nutrients_for_product(product: models.Product, quantity: float, unit: str):
    """Oblicza wartości dla produktu podstawowego na podstawie porcji użytkownika."""
    # POPRAWKA: Usunięto błędny, czwarty argument `db` z wywołania funkcji
    standardized_grams, _ = units.standardize_unit(quantity, unit, product.state)
    factor = standardized_grams / 100.0
    
    nutrients = {
        "calories": round(product.nutrients.get("calories", 0) * factor),
        "protein": round(product.nutrients.get("protein", 0) * factor, 1),
        "fat": round(product.nutrients.get("fat", 0) * factor, 1),
        "carbs": round(product.nutrients.get("carbs", 0) * factor, 1)
    }
    
    aggregated_meal = {
        "name": f"{product.name} ({quantity} {unit})",
        "quantity_grams": round(standardized_grams),
        "display_quantity_text": f"{quantity} {unit}",
        **nutrients
    }
    return {"aggregated_meal": aggregated_meal, "deconstruction_details": []}


async def _learn_new_dish(db: Session, dish_name: str, quantity: float, unit: str) -> Optional[Dict[str, Any]]:
    """
    Uruchamia proces uczenia się nowego dania.
    NOWA LOGIKA: Najpierw prosi o zagregowane dane. Jeśli AI uzna, że to danie złożone,
    dopiero wtedy prosi o dekonstrukcję.
    """
    # Krok 1: Poproś AI o dane zagregowane i o informację, czy to danie złożone.
    first_pass_prompt = f"""
    Jesteś dietetykiem. Przeanalizuj produkt: "{dish_name}".
    Odpowiedz ZAWSZE w formacie JSON z kluczami: "is_complex" (boolean: true, jeśli to danie wieloskładnikowe; false, jeśli to produkt prosty),
    "name" (poprawna nazwa), "quantity" (typowa waga w gramach), "unit" (zawsze "g"), "calories", "protein", "fat", "carbs".
    """
    response_text = await _get_ai_response(first_pass_prompt)
    try:
        parsed = json.loads(_clean_json_response(response_text))
        if not all(k in parsed for k in ["name", "calories", "is_complex"]):
            return None # Odpowiedź AI jest niekompletna
    except (json.JSONDecodeError, TypeError):
        return None

    is_complex_dish = parsed.get("is_complex", False)
    deconstruction_details = []

    # Krok 2: Jeśli AI oznaczyło to jako danie złożone, poproś o dekonstrukcję.
    if is_complex_dish:
        decon_prompt = f"""
        Podaj przepis dla potrawy "{parsed['name']}" jako listę składników i ich wag w gramach dla porcji {parsed['quantity']}g.
        Odpowiedz TYLKO w formacie tablicy JSON `[]` z obiektami o kluczach "ingredient_name" i "weight_g".
        """
        decon_response_text = await _get_ai_response(decon_prompt)
        try:
            deconstruction_details = json.loads(_clean_json_response(decon_response_text))
            # Sprawdź i doucz się brakujących składników
            for ingredient in deconstruction_details:
                product_name = ingredient.get("ingredient_name")
                if product_name and not crud.get_product_by_name(db, name=product_name):
                    await _learn_new_product(db, product_name) # Douczanie się składników
        except (json.JSONDecodeError, TypeError):
            deconstruction_details = [] # W razie błędu, zapisz bez dekonstrukcji

    # Krok 3: Zapisz nowe danie/produkt w bazie.
    # Użyjemy tabeli Products jako uniwersalnego cache'u
    product_schema = schemas.ProductCreate(
        name=parsed['name'],
        nutrients={"calories": parsed["calories"], "protein": parsed["protein"], "fat": parsed["fat"], "carbs": parsed["carbs"]},
        state=schemas.ProductState.LIQUID if "zupa" in parsed['name'].lower() else schemas.ProductState.SOLID,
        average_weight_g=parsed.get("quantity") if not is_complex_dish else 0
    )
    new_db_product = crud.create_product(db, product=product_schema)

    if is_complex_dish:
        # Zapisz również w tabeli Dishes, aby przechowywać przepis
        dish_schema = schemas.DishCreate(
            name=parsed['name'],
            aliases=[parsed['name']],
            ingredients=[schemas.DishIngredientCreate(product_name=ing["ingredient_name"], weight_g=ing["weight_g"]) for ing in deconstruction_details]
        )
        crud.create_dish_with_ingredients(db, dish=dish_schema)

    # Krok 4: Zwróć wynik przeskalowany do porcji użytkownika.
    final_quantity_grams, _ = units.standardize_unit(quantity, unit, new_db_product.state, new_db_product.average_weight_g)
    factor = final_quantity_grams / 100.0

    final_nutrients = {
        "calories": round(new_db_product.nutrients.get("calories", 0) * factor),
        "protein": round(new_db_product.nutrients.get("protein", 0) * factor, 1),
        "fat": round(new_db_product.nutrients.get("fat", 0) * factor, 1),
        "carbs": round(new_db_product.nutrients.get("carbs", 0) * factor, 1)
    }

    aggregated_meal = {
        "name": f"{parsed['name']} ({quantity} {unit})",
        "quantity_grams": round(final_quantity_grams),
        "display_quantity_text": f"{quantity} {unit}",
        **final_nutrients
    }
    return {"aggregated_meal": aggregated_meal, "deconstruction_details": deconstruction_details}


async def _learn_new_product(db: Session, product_name: str):
    """Pyta AI o dane dla nowego produktu podstawowego i zapisuje go w bazie."""
    product_prompt = f"""
    Jesteś encyklopedią żywienia. Podaj kompletne dane dla produktu: '{product_name}'.
    Odpowiedz ZAWSZE i TYLKO w formacie JSON z kluczami:
    - "state": "solid" lub "liquid",
    - "average_weight_g": typowa waga jednej sztuki w gramach (lub 0, jeśli produkt nie jest sztukowy),
    - "nutrients": obiekt z kluczami "calories", "protein", "fat", "carbs" dla 100g lub 100ml.
    """
    response_text = await _get_ai_response(product_prompt)
    try:
        data = json.loads(_clean_json_response(response_text))
        product_schema = schemas.ProductCreate(
            name=product_name,
            nutrients=data.get("nutrients", {}),
            state=data.get("state", "solid"),
            average_weight_g=data.get("average_weight_g", 0)
        )
        crud.create_product(db, product=product_schema)
        print(f"DEBUG: Cache WRITE! Nauczono się nowego produktu: '{product_name}'.")
    except (json.JSONDecodeError, TypeError) as e:
        print(f"BŁĄD: Nie udało się nauczyć nowego produktu '{product_name}'. {e}")

# --- POZOSTAŁE FUNKCJE (z drobnymi adaptacjami) ---

async def get_chat_response(db: Session, user: models.User, conversation: models.Conversation, new_message: str) -> str:
    # W przyszłości tutaj zaimplementujemy Tool Calling
    
    # Na razie prosty kontekst z dzisiejszego dnia
    summary = crud.get_meals_by_date(db, user.id, date.today())
    summary_text = f"Dzisiejsze posiłki użytkownika: {', '.join([e.product_name for m in summary for e in m.entries])}."
    
    system_prompt = f"Jesteś AIKcal, osobistym trenerem AI. Rozmawiasz z {user.name}. Jego cel kaloryczny to {user.calorie_goal} kcal. {summary_text} Bądź przyjazny i odpowiadaj po polsku."
    
    history_for_model = [{"role": "user", "parts": [{"text": system_prompt}]}]
    for msg in conversation.messages[-15:]: # Ograniczamy kontekst do ostatnich 15 wiadomości
        role = 'model' if msg.role == 'ai' else 'user'
        history_for_model.append({"role": role, "parts": [{"text": msg.content}]})

    response = await model.generate_content_async(history_for_model)
    return response.text if response.text else "Przepraszam, mam problem z odpowiedzią."


async def analyze_workout(text: str, weight: float) -> Dict[str, Any]:
    """Analizuje opis treningu i szacuje spalone kalorie, odrzucając nierealne aktywności."""
    prompt = f"""
    Jesteś surowym trenerem personalnym. Oszacuj spalone kalorie dla osoby ważącej {weight} kg, która wykonała aktywność: "{text}".
    ZASADY KRYTYCZNE:
    1. Jeśli podana aktywność to PRAWDZIWY trening lub ćwiczenie fizyczne (np. bieganie, pompki, spacer, joga), odpowiedz w JSON z kluczami "name" (nazwa treningu) i "calories_burned".
    2. Jeśli podana aktywność NIE JEST realnym ćwiczeniem (np. "trening jabłko", "jedzenie pizzy", "myślenie"), odpowiedz w JSON z "name" ustawionym na "Nierozpoznana aktywność" i "calories_burned" ZAWSZE ustawionym na 0. Nie próbuj być kreatywny.
    
    Przeanalizuj: "{text}"
    """
    response_text = await _get_ai_response(prompt)
    try:
        return json.loads(_clean_json_response(response_text))
    except (json.JSONDecodeError, TypeError):
        return {"name": "Błąd analizy treningu", "calories_burned": 0}

async def verify_challenge_completion(challenge_title: str, challenge_description: str, user_logs: List[str], category: str) -> bool:
    """Weryfikuje, czy użytkownik ukończył wyzwanie na podstawie logów."""
    if not user_logs: return False
    logs_str = "\n- ".join(user_logs)
    prompt = ""
    if category == 'dieta':
        prompt = f"""Jesteś sędzią w wyzwaniu dietetycznym: "{challenge_title}" (Zasady: {challenge_description}). Dziennik użytkownika:\n- {logs_str}\nCzy użytkownik ZŁAMAŁ zasady? Odpowiedz TYLKO "TAK" lub "NIE"."""
        response_text = await _get_ai_response(prompt)
        return "NIE" in response_text.upper()
    elif category == 'aktywność':
        prompt = f"""Jesteś trenerem sprawdzającym wykonanie zadania: "{challenge_title}" (Zasady: {challenge_description}). Dziennik aktywności:\n- {logs_str}\nCzy użytkownik WYKONAŁ zadanie? Odpowiedz TYLKO "TAK" lub "NIE"."""
        response_text = await _get_ai_response(prompt)
        return "TAK" in response_text.upper()
    return False

async def suggest_tdee_and_macros(req: schemas.GoalSuggestionRequest) -> Dict[str, float]:
    """Oblicza TDEE i sugeruje makroskładniki na podstawie danych użytkownika."""
    age = (date.today() - req.date_of_birth).days / 365.25
    if req.gender == schemas.Gender.MALE: bmr = (10 * req.weight) + (6.25 * req.height) - (5 * age) + 5
    else: bmr = (10 * req.weight) + (6.25 * req.height) - (5 * age) - 161
    multipliers = {
        schemas.ActivityLevel.BMR: 1.0, schemas.ActivityLevel.SEDENTARY: 1.2, 
        schemas.ActivityLevel.LIGHT: 1.375, schemas.ActivityLevel.MODERATE: 1.55, 
        schemas.ActivityLevel.ACTIVE: 1.725, schemas.ActivityLevel.VERY_ACTIVE: 1.9
    }
    tdee = bmr * multipliers.get(req.activity_level, 1.2)
    calorie_modifier = req.weekly_goal_kg * 1100
    adjusted_calories = tdee + calorie_modifier
    macro_ratios = {
        schemas.DietStyle.BALANCED: {"p": 0.25, "f": 0.30, "c": 0.45}, 
        schemas.DietStyle.KETO: {"p": 0.25, "f": 0.70, "c": 0.05}, 
        schemas.DietStyle.VEGE: {"p": 0.20, "f": 0.30, "c": 0.50}, 
        schemas.DietStyle.LOW_CARB: {"p": 0.35, "f": 0.45, "c": 0.20}, 
        schemas.DietStyle.HIGH_PROTEIN: {"p": 0.40, "f": 0.30, "c": 0.30}
    }
    ratios = macro_ratios.get(req.diet_style, macro_ratios[schemas.DietStyle.BALANCED])
    return {
        "calorie_goal": round(adjusted_calories), 
        "protein_goal": round((adjusted_calories * ratios['p']) / 4), 
        "fat_goal": round((adjusted_calories * ratios['f']) / 9), 
        "carb_goal": round((adjusted_calories * ratios['c']) / 4)
    }

async def generate_weekly_analysis(user_data: Dict[str, Any], user: models.User, start_date: date, end_date: date) -> str:
    """Generuje tekstowe podsumowanie tygodnia dla AI Trenera."""
    # Konwersja danych na serializowalny format JSON
    serializable_user_data = {
        "meals": [
            {"name": m.name, "date": m.date.isoformat(), "entries": [{"product_name": e.product_name, "calories": e.calories} for e in m.entries]} 
            for m in user_data.get("meals", [])
        ],
        "workouts": [
            {"name": w.name, "calories_burned": w.calories_burned, "date": w.date.isoformat()} 
            for w in user_data.get("workouts", [])
        ],
        "weight_history": [
            {"weight": wh.weight, "date": wh.date.isoformat()} 
            for wh in user_data.get("weight_history", [])
        ]
    }
    prompt = f"""Jesteś trenerem AI. Przeanalizuj dane użytkownika {user.name} od {start_date.strftime('%d.%m')} do {end_date.strftime('%d.%m')}. Dane: {json.dumps(serializable_user_data)}. Cele: {user.calorie_goal} kcal. Napisz krótkie, motywujące podsumowanie po polsku: co poszło dobrze, co poprawić i daj jedną sugestię."""
    return await _get_ai_response(prompt)

async def suggest_diet_plan(preferences: dict, macros: dict) -> Optional[List[Dict[str, Any]]]:
    """Generuje całodniowy plan posiłków dla AI Chefa."""
    allowed_categories = ", ".join([f"'{e.value}'" for e in MealCategory])
    prompt = f"""
    Jesteś AI Chefem. Twoim zadaniem jest stworzenie spersonalizowanego, całodniowego planu posiłków.
    Odpowiedz ZAWSZE i TYLKO w formacie listy JSON. Każdy element listy to obiekt posiłku.

    ZASADY:
    1.  Dopasuj do makro: Plan musi w przybliżeniu pasować do celów: {macros}.
    2.  Użyj preferencji: Wykorzystaj ulubione produkty użytkownika: {preferences}.
    3.  KATEGORIE: Wartość klucza "category" MUSI być jedną z tych wartości: {allowed_categories}.
    4.  Struktura obiektu posiłku: "meal_name", "category", "recipe", "products" (lista).
    5.  Struktura obiektu składnika: "name", "quantity_grams", "calories", "protein", "fat", "carbs".

    Stwórz kompletny plan na jeden dzień.
    """
    response_text = await _get_ai_response(prompt)
    try:
        plan = json.loads(_clean_json_response(response_text))
        return plan if isinstance(plan, list) and len(plan) > 0 else None
    except (json.JSONDecodeError, TypeError):
        return None
