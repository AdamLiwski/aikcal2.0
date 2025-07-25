from datetime import date, timedelta
from typing import Optional
from . import models

def calculate_goal_achievement_date(user: models.User) -> Optional[str]:
    """Oblicza szacowaną datę osiągnięcia celu wagowego."""
    # Sprawdza, czy wszystkie niezbędne dane są dostępne
    if not all([user.weight, user.target_weight, user.weekly_goal_kg]):
        return None

    # Unika dzielenia przez zero i nielogicznych celów
    if user.weekly_goal_kg == 0:
        return None

    weight_to_change = user.weight - user.target_weight
    
    # Sprawdza, czy kierunek celu jest zgodny z wymaganą zmianą wagi
    # Jeśli użytkownik chce schudnąć (cel < 0), różnica wagi musi być dodatnia
    if user.weekly_goal_kg < 0 and weight_to_change <= 0:
        return None
    # Jeśli użytkownik chce przytyć (cel > 0), różnica wagi musi być ujemna
    if user.weekly_goal_kg > 0 and weight_to_change >= 0:
        return None

    try:
        weeks_to_goal = abs(weight_to_change / user.weekly_goal_kg)
        days_to_goal = int(weeks_to_goal * 7)
        eta_date = date.today() + timedelta(days=days_to_goal)
        # Zwraca datę w ładnym formacie
        return eta_date.strftime("%d.%m.%Y")
    except (ValueError, TypeError):
        return None
