from sqlalchemy import (Column, Integer, String, Float, Date, Time, ForeignKey, JSON, Boolean, Text, DateTime, desc)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import Enum as SQLAlchemyEnum
from datetime import date as date_type, datetime
from typing import Optional

# Zaktualizowany import, dodajemy nowe Enumy, które zaraz zdefiniujemy
from .enums import (MealCategory, ActivityLevel, Gender, DietStyle, FriendshipStatus, 
                    ChallengeStatus, SubscriptionStatus, ProductState)
from .db import Base

def default_preferences():
    """Zwraca domyślną strukturę preferencji dla nowego użytkownika."""
    return {
        "proteins": ["Pierś z kurczaka", "Jajka", "Twaróg", "Łosoś", "Czerwona soczewica"],
        "carbs": ["Ryż brązowy", "Ziemniaki", "Makaron pełnoziarnisty", "Płatki owsiane", "Chleb żytni"],
        "fats": ["Awokado", "Oliwa z oliwek", "Orzechy włoskie", "Masło orzechowe", "Pestki dyni"]
    }

# --- NOWE, RELACYJNE MODELE DLA BAZY ŻYWNOŚCI ---

class Product(Base):
    """Tabela 'encyklopedii' - przechowuje wszystkie unikalne produkty podstawowe."""
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, index=True, nullable=False)
    # Przechowuje popularne, potoczne nazwy i błędy w pisowni, np. ["dewolaj", "kotlet po kijowsku"]
    aliases = Column(JSON, default=[]) 
    # Przechowuje wartości odżywcze dla 100g/ml produktu
    nutrients = Column(JSON, nullable=False) 
    # Kluczowe pole dla inteligentnego przelicznika miar
    state = Column(SQLAlchemyEnum(ProductState), default=ProductState.SOLID) 
    average_weight_g = Column(Float, nullable=True) # Przechowuje typową wagę jednej sztuki

class Dish(Base):
    """Tabela 'książki kucharskiej' - przechowuje nazwy dań złożonych."""
    __tablename__ = "dishes"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, index=True, nullable=False)
    category = Column(String, nullable=True)
    # Przechowuje popularne, potoczne nazwy i błędy w pisowni
    aliases = Column(JSON, default=[])
    
    # Relacja do tabeli z "przepisami"
    ingredients = relationship("DishIngredient", back_populates="dish", cascade="all, delete-orphan")

class DishIngredient(Base):
    """Tabela łącząca - przechowuje przepisy (składniki i ich wagi dla konkretnego dania)."""
    __tablename__ = "dish_ingredients"
    id = Column(Integer, primary_key=True)
    dish_id = Column(Integer, ForeignKey("dishes.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    weight_g = Column(Float, nullable=False) # Waga składnika w tym konkretnym daniu

    dish = relationship("Dish", back_populates="ingredients")
    product = relationship("Product")


# --- NOWE MODELE DLA WIELOWĄTKOWEGO CZATU ---

class Conversation(Base):
    """Tabela przechowująca osobne wątki rozmów z AI Trenerem."""
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, default="Nowy czat")
    created_at = Column(DateTime, default=datetime.utcnow)
    is_pinned = Column(Boolean, default=False)
    
    user = relationship("User", back_populates="conversations")
    messages = relationship("ChatMessage", back_populates="conversation", cascade="all, delete-orphan", order_by="ChatMessage.created_at")

class ChatMessage(Base):
    """Tabela przechowująca pojedyncze wiadomości w ramach konwersacji."""
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(String, nullable=False) # 'user' lub 'ai'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    conversation = relationship("Conversation", back_populates="messages")


# --- ZAKTUALIZOWANY MODEL UŻYTKOWNIKA ---

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True) 
    name = Column(String, default="Użytkownik")
    is_verified = Column(Boolean, default=False) # Pole do weryfikacji e-mail
    password_reset_token = Column(String, nullable=True, index=True) # Dodane pole: token resetowania hasła
    password_reset_expires = Column(DateTime, nullable=True) # Dodane pole: data wygaśnięcia tokenu
    
    # Dane profilowe
    gender = Column(SQLAlchemyEnum(Gender))
    date_of_birth = Column(Date)
    height = Column(Float)
    
    # Ustawienia
    target_weight = Column(Float)
    weekly_goal_kg = Column(Float, default=0.0)
    activity_level = Column(SQLAlchemyEnum(ActivityLevel), default=ActivityLevel.SEDENTARY)
    diet_style = Column(SQLAlchemyEnum(DietStyle), default=DietStyle.BALANCED)
    calorie_goal = Column(Integer, default=2000)
    protein_goal = Column(Integer, default=100)
    fat_goal = Column(Integer, default=70)
    carb_goal = Column(Integer, default=250)
    water_goal = Column(Integer, default=2500)
    add_workout_calories_to_goal = Column(Boolean, default=False)
    is_social_profile_active = Column(Boolean, default=True)
    
    # Dane AI (stare pole chat_history zostanie usunięte)
    diet_plan_requests = Column(Integer, default=0)
    last_request_date = Column(Date, default=lambda: date_type.today())
    last_diet_plan = Column(Text, nullable=True)
    last_weekly_analysis = Column(Text, nullable=True)
    last_analysis_generated_at = Column(DateTime, nullable=True) 
    preferences = Column(JSON, default=default_preferences)

    # NOWE: Fundament pod subskrypcje
    subscription_status = Column(SQLAlchemyEnum(SubscriptionStatus), default=SubscriptionStatus.FREE)
    subscription_expires_at = Column(DateTime, nullable=True)
    
    # Relacje
    weights = relationship("WeightEntry", back_populates="owner", cascade="all, delete-orphan", order_by="desc(WeightEntry.date), desc(WeightEntry.id)")
    meals = relationship("Meal", back_populates="owner", cascade="all, delete-orphan")
    water_entries = relationship("WaterEntry", back_populates="owner", cascade="all, delete-orphan")
    workouts = relationship("Workout", back_populates="owner", cascade="all, delete-orphan")
    user_challenges = relationship("UserChallenge", back_populates="user", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan") # Nowa relacja do rozmów

    @property
    def weight(self) -> Optional[float]:
        if self.weights:
            return self.weights[0].weight
        return None

# --- ISTNIEJĄCE MODELE (z drobnymi poprawkami) ---

class Challenge(Base):
    __tablename__ = "challenges"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, unique=True)
    description = Column(Text, nullable=False)
    duration_days = Column(Integer, nullable=False)
    category = Column(String, nullable=False)

class UserChallenge(Base):
    __tablename__ = "user_challenges"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    # UWAGA: Poniżej może być konieczna zmiana, jeśli usuniemy tabelę 'challenges' i będziemy je trzymać w kodzie
    challenge_id = Column(Integer, nullable=False) # Usunięto ForeignKey, jeśli wyzwania będą statyczne
    start_date = Column(Date, nullable=False, default=date_type.today)
    end_date = Column(Date, nullable=False)
    status = Column(SQLAlchemyEnum(ChallengeStatus), nullable=False, default=ChallengeStatus.ACTIVE)
    
    user = relationship("User", back_populates="user_challenges")

class WeightEntry(Base):
    __tablename__ = "weight_entries"
    id = Column(Integer, primary_key=True, index=True)
    weight = Column(Float, nullable=False)
    date = Column(Date, default=date_type.today, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="weights")

class Friendship(Base):
    __tablename__ = "friendships"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    friend_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(SQLAlchemyEnum(FriendshipStatus), nullable=False, default=FriendshipStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", foreign_keys=[user_id])
    friend = relationship("User", foreign_keys=[friend_id])

class Meal(Base):
    __tablename__ = "meals"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False) 
    date = Column(Date, nullable=False, default=date_type.today)
    time = Column(Time, nullable=True, default=lambda: datetime.now().time())
    category = Column(SQLAlchemyEnum(MealCategory), nullable=False)
    
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="meals")
    
    entries = relationship("MealEntry", back_populates="meal", cascade="all, delete-orphan")

class MealEntry(Base):
    __tablename__ = "meal_entries"
    id = Column(Integer, primary_key=True, index=True)
    product_name = Column(String, nullable=False)
    
    calories = Column(Float, default=0.0)
    protein = Column(Float, default=0.0)
    fat = Column(Float, default=0.0)
    carbs = Column(Float, default=0.0)
    
    original_amount = Column(Float, nullable=False)
    original_unit = Column(String, nullable=False)
    display_quantity_text = Column(String, nullable=True)
    
    standardized_grams = Column(Float, nullable=False)
    
    # To pole będzie zawierać zmodyfikowany przez użytkownika przepis w momencie dodawania
    deconstruction_details = Column(JSON, nullable=True)
    is_default_quantity = Column(Boolean, nullable=False, default=False) 
    
    meal_id = Column(Integer, ForeignKey("meals.id"))
    meal = relationship("Meal", back_populates="entries") 

class WaterEntry(Base):
    __tablename__ = "water_entries"
    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Integer, nullable=False)
    date = Column(Date, nullable=False, default=date_type.today)
    time = Column(Time, nullable=False, default=lambda: datetime.now().time())
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="water_entries")

class Workout(Base):
    __tablename__ = "workouts"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    date = Column(Date, nullable=False, default=date_type.today)
    calories_burned = Column(Integer, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="workouts")

class CachedDish(Base):
    __tablename__ = "cached_dishes"
    query = Column(String, primary_key=True, index=True)
    composition = Column(JSON, nullable=False)

class CachedProduct(Base):
    __tablename__ = "cached_products"
    name = Column(String, primary_key=True, index=True)
    nutrients = Column(JSON, nullable=False)
