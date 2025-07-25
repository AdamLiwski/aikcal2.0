import os
import json
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from core.models import Base, Product, Dish, DishIngredient
from core.schemas import ProductCreate, DishCreate, DishIngredientCreate, ProductState

# --- Konfiguracja ---
DATABASE_URL = "sqlite:///./aikcal.db"
INPUT_FILE = "master_dane_wzbogacone2.json"

def seed_database():
    print("--- Rozpoczynam proces zasilania bazy danych ---")

    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"Wczytano {len(data)} pozycji z pliku '{INPUT_FILE}'.")

        # Listy do przechowywania danych
        products_to_create = {}
        dishes_to_create = {}

        for item in data:
            item_name = item.get('name')
            if not item_name: continue
            
            if "deconstruction" in item:
                dishes_to_create[item_name.lower()] = item
            else:
                products_to_create[item_name.lower()] = item

        print(f"1/3: Zidentyfikowano {len(products_to_create)} produktów podstawowych i {len(dishes_to_create)} dań.")

        # --- Krok 1: Zapisz wszystkie unikalne produkty podstawowe ---
        print("2/3: Zapisywanie produktów podstawowych w bazie...")
        
        # Najpierw dodajmy te, które już mamy w plikach
        for product_data in products_to_create.values():
            nutrients = product_data.get('nutrients_per_100g') or product_data.get('nutrients_per_100ml')
            if not nutrients: continue
            
            new_product = Product(
                name=product_data['name'],
                aliases=product_data.get('aliases', []),
                nutrients=nutrients,
                state=product_data.get('state', 'solid'),
                average_weight_g=product_data.get('average_weight_g', 0)
            )
            db.merge(new_product) # Użyj merge, aby uniknąć błędów duplikatów
        
        # Następnie dodaj te, które są tylko w dekonstrukcjach
        for dish_data in dishes_to_create.values():
            for ingredient in dish_data.get("deconstruction", []):
                ing_name = ingredient['ingredient_name']
                if ing_name.lower() not in products_to_create:
                    existing = db.query(Product).filter_by(name=ing_name).first()
                    if not existing:
                        placeholder = Product(name=ing_name, nutrients={"calories": 0}, state=ProductState.SOLID)
                        db.add(placeholder)

        db.commit()
        print("-> Zapisano produkty podstawowe.")

        # --- Krok 2: Zapisz dania i ich relacje ---
        print("3/3: Zapisywanie dań i ich przepisów...")
        
        products_from_db = {p.name.lower(): p for p in db.query(Product).all()}

        for dish_data in dishes_to_create.values():
            # Sprawdź, czy danie już istnieje
            existing_dish = db.query(Dish).filter_by(name=dish_data['name']).first()
            if existing_dish: continue

            new_dish = Dish(name=dish_data['name'], category=dish_data.get('category'), aliases=dish_data.get('aliases', []))
            db.add(new_dish)
            
            for ingredient in dish_data.get("deconstruction", []):
                product = products_from_db.get(ingredient['ingredient_name'].lower())
                if product:
                    new_ingredient = DishIngredient(
                        dish=new_dish,
                        product_id=product.id,
                        weight_g=ingredient['weight_g']
                    )
                    db.add(new_ingredient)
        
        db.commit()
        print("-> Zapisano dania i przepisy.")
        print("\n--- Proces zakończony pomyślnie! Baza danych została zasilona. ---")

    except Exception as e:
        print(f"Wystąpił błąd krytyczny: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()