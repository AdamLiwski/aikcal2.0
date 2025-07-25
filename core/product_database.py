import httpx
from typing import List, Dict, Optional, Any

BASE_URL = "https://world.openfoodfacts.org/api/v2"

async def search_product_by_barcode(barcode: str) -> Optional[Dict[str, Any]]:
    """
    Wyszukuje produkt w Open Food Facts po kodzie kreskowym.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/product/{barcode}.json")
            response.raise_for_status()
            data = response.json()
            if data.get("status") == 1 and "product" in data:
                product = data["product"]
                nutriments = product.get("nutriments", {})
                return {
                    "name": product.get("product_name", "Nieznany produkt"),
                    "calories": nutriments.get("energy-kcal_100g", 0),
                    "protein": nutriments.get("proteins_100g", 0),
                    "fat": nutriments.get("fat_100g", 0),
                    "carbs": nutriments.get("carbohydrates_100g", 0),
                    "source": "Open Food Facts (Barcode)"
                }
        except httpx.HTTPStatusError as e:
            print(f"Błąd API Open Food Facts: {e}")
            return None
        except Exception as e:
            print(f"Nieoczekiwany błąd podczas wyszukiwania kodu kreskowego: {e}")
            return None
    return None
