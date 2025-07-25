import random
from datetime import datetime

# Duża, statyczna lista wszystkich możliwych wyzwań w aplikacji
ALL_CHALLENGES = [
  {
    "id": 1,
    "title": "Tydzień bez słodyczy",
    "description": "Nie dodawaj do swoich posiłków żadnych kupnych słodyczy, ciast, ciastek ani cukierków.",
    "duration_days": 7,
    "category": "dieta"
  },
  {
    "id": 2,
    "title": "5 porcji warzyw dziennie",
    "description": "Dodaj przynajmniej jedną porcję warzyw do każdego z pięciu posiłków w ciągu dnia.",
    "duration_days": 7,
    "category": "dieta"
  },
  {
    "id": 3,
    "title": "Białkowe śniadanie",
    "description": "Zadbaj o to, aby Twoje śniadanie każdego dnia zawierało co najmniej 20g białka.",
    "duration_days": 7,
    "category": "dieta"
  },
  {
    "id": 4,
    "title": "Tydzień bez smażenia",
    "description": "Przygotowuj posiłki metodą gotowania, pieczenia lub duszenia, unikając smażenia na głębokim tłuszczu.",
    "duration_days": 7,
    "category": "dieta"
  },
  {
    "id": 5,
    "title": "Kolorowy talerz",
    "description": "Każdego dnia skomponuj co najmniej jeden główny posiłek z produktów w 3 różnych kolorach.",
    "duration_days": 7,
    "category": "dieta"
  },
  {
    "id": 6,
    "title": "Tydzień z rybą",
    "description": "Włącz do swojego jadłospisu rybę co najmniej dwa razy w ciągu tego tygodnia.",
    "duration_days": 7,
    "category": "dieta"
  },
  {
    "id": 7,
    "title": "Zero słodkich napojów",
    "description": "Zastąp wszystkie słodzone napoje gazowane i niegazowane wodą, herbatą lub kawą bez cukru.",
    "duration_days": 7,
    "category": "dieta"
  },
  {
    "id": 8,
    "title": "Domowy lunchbox",
    "description": "Przygotuj i zapisz w aplikacji posiłki do pracy lub szkoły na co najmniej 4 dni w tygodniu.",
    "duration_days": 7,
    "category": "dieta"
  },
  {
    "id": 9,
    "title": "Pełnoziarnisty wybór",
    "description": "Wybieraj wyłącznie pełnoziarniste wersje pieczywa i makaronów przez cały tydzień.",
    "duration_days": 7,
    "category": "dieta"
  },
  {
    "id": 10,
    "title": "Zdrowe tłuszcze na start",
    "description": "Dodaj do co najmniej jednego posiłku dziennie źródło zdrowych tłuszczów, takie jak awokado, orzechy czy oliwa.",
    "duration_days": 7,
    "category": "dieta"
  },
  {
    "id": 11,
    "title": "Tydzień bez czerwonego mięsa",
    "description": "Zastąp czerwone mięso w swoich posiłkach drobiem, rybami lub roślinami strączkowymi.",
    "duration_days": 7,
    "category": "dieta"
  },
  {
    "id": 12,
    "title": "Mistrz planowania posiłków",
    "description": "Zaplanuj i zapisz w aplikacji jadłospis na cały nadchodzący tydzień z góry.",
    "duration_days": 7,
    "category": "dieta"
  },
  {
    "id": 13,
    "title": "Ziołowa rewolucja",
    "description": "Zamiast soli, do przyprawiania potraw używaj świeżych lub suszonych ziół przez cały tydzień.",
    "duration_days": 7,
    "category": "dieta"
  },
  {
    "id": 14,
    "title": "Owocowa przekąska",
    "description": "Każdego dnia zjedz co najmniej dwie porcje różnych owoców w ramach przekąsek.",
    "duration_days": 7,
    "category": "dieta"
  },
  {
    "id": 15,
    "title": "Tydzień z kaszą",
    "description": "Dodaj do co najmniej trzech głównych posiłków w tygodniu dowolny rodzaj kaszy.",
    "duration_days": 7,
    "category": "dieta"
  },
  {
    "id": 16,
    "title": "Zero fast foodów",
    "description": "Unikaj zamawiania i spożywania gotowych dań typu fast food przez cały tydzień.",
    "duration_days": 7,
    "category": "dieta"
  },
  {
    "id": 17,
    "title": "Strączkowy zawrót głowy",
    "description": "Włącz do swojego jadłospisu dania z nasionami roślin strączkowych (ciecierzyca, soczewica, fasola) minimum 3 razy.",
    "duration_days": 7,
    "category": "dieta"
  },
  {
    "id": 18,
    "title": "Lekka kolacja",
    "description": "Zadbaj o to, by Twoja kolacja każdego dnia była posiłkiem bez węglowodanów prostych.",
    "duration_days": 7,
    "category": "dieta"
  },
  {
    "id": 19,
    "title": "Tydzień bez alkoholu",
    "description": "Całkowicie zrezygnuj ze spożywania napojów alkoholowych przez 7 dni.",
    "duration_days": 7,
    "category": "dieta"
  },
  {
    "id": 20,
    "title": "Moc fermentacji",
    "description": "Dodaj do swojego jadłospisu produkty fermentowane (kiszonki, jogurty, kefiry) przynajmniej 4 razy w tygodniu.",
    "duration_days": 7,
    "category": "dieta"
  },
  {
    "id": 21,
    "title": "Nowy smak tygodnia",
    "description": "Wypróbuj i dodaj do jadłospisu przynajmniej jedno warzywo lub owoc, którego nigdy wcześniej nie jadłeś.",
    "duration_days": 7,
    "category": "dieta"
  },
  {
    "id": 22,
    "title": "Tydzień bez białego cukru",
    "description": "Eliminuj produkty zawierające dodany biały cukier, czytając etykiety w sklepie.",
    "duration_days": 7,
    "category": "dieta"
  },
  {
    "id": 23,
    "title": "Zupa mocy",
    "description": "Przygotuj i zjedz co najmniej 3 porcje zupy warzywnej w ciągu tygodnia.",
    "duration_days": 7,
    "category": "dieta"
  },
  {
    "id": 24,
    "title": "Śniadanie na słono",
    "description": "Przez cały tydzień jedz wyłącznie wytrawne śniadania, unikając dżemów, miodu i słodkich płatków.",
    "duration_days": 7,
    "category": "dieta"
  },
  {
    "id": 25,
    "title": "Bez sosów z tubki",
    "description": "Zastąp gotowe sosy (ketchup, majonez) własnoręcznie przygotowanymi na bazie jogurtu, ziół lub warzyw.",
    "duration_days": 7,
    "category": "dieta"
  },
  {
    "id": 26,
    "title": "Zielono mi",
    "description": "Dodaj do co najmniej jednego posiłku dziennie porcję zielonych warzyw liściastych (szpinak, sałata, jarmuż).",
    "duration_days": 7,
    "category": "dieta"
  },
  {
    "id": 27,
    "title": "Chrupiąca alternatywa",
    "description": "Zamiast chipsów i słonych paluszków, jako przekąskę wybieraj surowe warzywa lub orzechy.",
    "duration_days": 7,
    "category": "dieta"
  },
  {
    "id": 28,
    "title": "Domowe wypieki",
    "description": "Jeśli masz ochotę na coś słodkiego, przygotuj zdrową wersję deseru lub ciasta w domu.",
    "duration_days": 7,
    "category": "dieta"
  },
  {
    "id": 29,
    "title": "Tydzień wegetariański",
    "description": "Spróbuj przez 7 dni komponować swoje posiłki wyłącznie z produktów pochodzenia roślinnego.",
    "duration_days": 7,
    "category": "dieta"
  },
  {
    "id": 30,
    "title": "Pełna kontrola kalorii",
    "description": "Codziennie zapisuj wszystkie spożyte posiłki, starając się nie przekraczać swojego celu kalorycznego.",
    "duration_days": 7,
    "category": "dieta"
  },
  {
    "id": 31,
    "title": "Codzienny spacer 30 min",
    "description": "Zarejestruj w aplikacji co najmniej 30 minutowy spacer każdego dnia tygodnia.",
    "duration_days": 7,
    "category": "aktywność"
  },
  {
    "id": 32,
    "title": "3x trening siłowy",
    "description": "Wykonaj i zapisz trzy dowolne treningi siłowe w ciągu tego tygodnia.",
    "duration_days": 7,
    "category": "aktywność"
  },
  {
    "id": 33,
    "title": "Tydzień z jogą",
    "description": "Zarejestruj co najmniej 4 sesje jogi po minimum 15 minut każda.",
    "duration_days": 7,
    "category": "aktywność"
  },
  {
    "id": 34,
    "title": "Aktywny poranek",
    "description": "Wykonaj i zapisz dowolną 15-minutową aktywność fizyczną przed godziną 9:00 rano.",
    "duration_days": 7,
    "category": "aktywność"
  },
  {
    "id": 35,
    "title": "Rowerowy zawrót głowy",
    "description": "Zarejestruj w sumie co najmniej 60 minut jazdy na rowerze w ciągu tygodnia.",
    "duration_days": 7,
    "category": "aktywność"
  },
  {
    "id": 36,
    "title": "Wyzwanie cardio",
    "description": "Wykonaj i zapisz 3 treningi cardio (bieganie, orbitrek, rowerek stacjonarny) po 30 minut.",
    "duration_days": 7,
    "category": "aktywność"
  },
  {
    "id": 37,
    "title": "Mocne plecy",
    "description": "Zarejestruj dwa treningi w tygodniu, które zawierają co najmniej jedno ćwiczenie na mięśnie pleców.",
    "duration_days": 7,
    "category": "aktywność"
  },
  {
    "id": 38,
    "title": "Wieczorne rozciąganie",
    "description": "Zapisz 10-minutową sesję rozciągania każdego wieczoru przed snem.",
    "duration_days": 7,
    "category": "aktywność"
  },
  {
    "id": 39,
    "title": "Aktywny weekend",
    "description": "Zarejestruj co najmniej 60 minut dowolnej aktywności fizycznej w sobotę i niedzielę.",
    "duration_days": 7,
    "category": "aktywność"
  },
  {
    "id": 40,
    "title": "Nowa forma ruchu",
    "description": "Spróbuj i zapisz jedną nową dla siebie formę aktywności fizycznej (np. taniec, pływanie, wspinaczka).",
    "duration_days": 7,
    "category": "aktywność"
  },
  {
    "id": 41,
    "title": "Trening interwałowy",
    "description": "Wykonaj i zapisz dwa 20-minutowe treningi interwałowe (HIIT) w ciągu tygodnia.",
    "duration_days": 7,
    "category": "aktywność"
  },
  {
    "id": 42,
    "title": "Wyzwanie na schodach",
    "description": "Zarejestruj co najmniej 3 razy w tygodniu 10-minutową aktywność 'wchodzenie po schodach'.",
    "duration_days": 7,
    "category": "aktywność"
  },
  {
    "id": 43,
    "title": "Core stability",
    "description": "Wykonaj i zapisz 4 razy w tygodniu trening zawierający ćwiczenie 'plank' (deska).",
    "duration_days": 7,
    "category": "aktywność"
  },
  {
    "id": 44,
    "title": "Biegacz na 5 km",
    "description": "Zarejestruj w sumie 5 kilometrów biegu, rozłożone na dowolną liczbę treningów w tygodniu.",
    "duration_days": 7,
    "category": "aktywność"
  },
  {
    "id": 45,
    "title": "Aktywna przerwa w pracy",
    "description": "Zapisz codziennie 15-minutowy spacer lub proste ćwiczenia w trakcie dnia pracy.",
    "duration_days": 7,
    "category": "aktywność"
  },
  {
    "id": 46,
    "title": "Pływacki tydzień",
    "description": "Zarejestruj dwie wizyty na basenie, każda trwająca co najmniej 30 minut.",
    "duration_days": 7,
    "category": "aktywność"
  },
  {
    "id": 47,
    "title": "Trening całego ciała (FBW)",
    "description": "Wykonaj i zapisz dwa treningi typu Full Body Workout w ciągu tygodnia.",
    "duration_days": 7,
    "category": "aktywność"
  },
  {
    "id": 48,
    "title": "Mocne nogi",
    "description": "Zarejestruj dwa treningi w tygodniu zawierające co najmniej jedno ćwiczenie na nogi (np. przysiady).",
    "duration_days": 7,
    "category": "aktywność"
  },
  {
    "id": 49,
    "title": "10 000 kroków dziennie",
    "description": "Zarejestruj w aplikacji osiągnięcie celu 10 000 kroków przez 5 dni w tygodniu.",
    "duration_days": 7,
    "category": "aktywność"
  },
  {
    "id": 50,
    "title": "Tydzień z pilatesem",
    "description": "Zapisz trzy sesje pilatesu, każda trwająca co najmniej 20 minut.",
    "duration_days": 7,
    "category": "aktywność"
  },
  {
    "id": 51,
    "title": "Wyzwanie na skakance",
    "description": "Zarejestruj w sumie 30 minut skakania na skakance w ciągu całego tygodnia.",
    "duration_days": 7,
    "category": "aktywność"
  },
  {
    "id": 52,
    "title": "Trening z gumami oporowymi",
    "description": "Wykonaj i zapisz 3 treningi z użyciem gum oporowych w ciągu tygodnia.",
    "duration_days": 7,
    "category": "aktywność"
  },
  {
    "id": 53,
    "title": "Rodzinna aktywność",
    "description": "Zapisz jedną co najmniej 45-minutową aktywność wykonaną z rodziną lub przyjaciółmi (np. gra w piłkę, wycieczka).",
    "duration_days": 7,
    "category": "aktywność"
  },
  {
    "id": 54,
    "title": "Wędrówka w terenie",
    "description": "Zarejestruj co najmniej jedną 60-minutową wędrówkę lub trekking w ciągu tygodnia.",
    "duration_days": 7,
    "category": "aktywność"
  },
  {
    "id": 55,
    "title": "Trening z masą własnego ciała",
    "description": "Wykonaj i zapisz 4 treningi w tygodniu, używając wyłącznie ciężaru własnego ciała.",
    "duration_days": 7,
    "category": "aktywność"
  },
  {
    "id": 56,
    "title": "Taneczny tydzień",
    "description": "Zarejestruj łącznie 60 minut tańca (np. zumba, zajęcia taneczne, taniec w domu) w ciągu tygodnia.",
    "duration_days": 7,
    "category": "aktywność"
  },
  {
    "id": 57,
    "title": "Aktywny dojazd",
    "description": "Zarejestruj dojazd do pracy lub szkoły rowerem lub pieszo co najmniej 3 razy.",
    "duration_days": 7,
    "category": "aktywność"
  },
  {
    "id": 58,
    "title": "Poranna gimnastyka",
    "description": "Zarejestruj codziennie 10-minutową poranną gimnastykę zaraz po przebudzeniu.",
    "duration_days": 7,
    "category": "aktywność"
  },
  {
    "id": 59,
    "title": "Wyzwanie pompki",
    "description": "Zarejestruj treningi, w których łącznie wykonasz 50 pompek w ciągu tygodnia.",
    "duration_days": 7,
    "category": "aktywność"
  },
  {
    "id": 60,
    "title": "Mistrz regularności",
    "description": "Zarejestruj dowolną formę aktywności fizycznej trwającą min. 20 minut każdego dnia.",
    "duration_days": 7,
    "category": "aktywność"
  }
]

def get_challenge_by_id(challenge_id: int):
    """
    Wyszukuje i zwraca jedno wyzwanie z listy na podstawie jego ID.
    """
    for challenge in ALL_CHALLENGES:
        if challenge['id'] == challenge_id:
            return challenge
    return None

def get_all_challenges():
    """
    Zwraca 3 losowe wyzwania. Wybór jest stały dla danego tygodnia kalendarzowego.
    """
    # Używamy numeru roku i tygodnia jako "ziarna" dla generatora liczb losowych.
    # To gwarantuje, że przez cały tydzień wyniki losowania będą takie same.
    today = datetime.today()
    year, week, _ = today.isocalendar()
    
    # Ustawiamy ziarno na podstawie roku i tygodnia
    random.seed(f"{year}-{week}")
    
    # Jeśli z jakiegoś powodu mamy mniej niż 3 wyzwania, zwróćmy wszystkie.
    if len(ALL_CHALLENGES) < 3:
        return ALL_CHALLENGES
        
    # Losujemy 3 unikalne wyzwania z całej puli
    return random.sample(ALL_CHALLENGES, 3)

