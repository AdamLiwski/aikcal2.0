from enum import Enum

class MealCategory(str, Enum):
    SNIADANIE = "Śniadanie"
    DRUGIE_SNIADANIE = "II Śniadanie"
    OBIAD = "Obiad"
    KOLACJA = "Kolacja"
    PRZEKASKA = "Przekąska"

class Gender(str, Enum):
    MALE = "Mężczyzna"
    FEMALE = "Kobieta"

class ActivityLevel(str, Enum):
    BMR = "BMR"
    SEDENTARY = "Siedzący"
    LIGHT = "Lekka aktywność"
    MODERATE = "Umiarkowana aktywność"
    ACTIVE = "Aktywny"
    VERY_ACTIVE = "Bardzo aktywny"

class DietStyle(str, Enum):
    BALANCED = "Zbilansowana"
    KETO = "Ketogeniczna"
    VEGE = "Wegetariańska"
    LOW_CARB = "Niskowęglowodanowa"
    HIGH_PROTEIN = "Wysokobiałkowa"

class FriendshipStatus(str, Enum):
    """Status relacji między użytkownikami."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    BLOCKED = "blocked"

# NOWA KLASA ENUM
class ChallengeStatus(str, Enum):
    """Status wyzwania podjętego przez użytkownika."""
    ACTIVE = "aktywne"
    COMPLETED = "ukończone"
    FAILED = "nieudane"
# --- NOWE ENUMY ---
class SubscriptionStatus(str, Enum):
    FREE = "free"
    PREMIUM = "premium"

class ProductState(str, Enum):
    SOLID = "solid"
    LIQUID = "liquid"