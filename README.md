# Codify - Aplikacja do konwersji kodu

Aplikacja webowa do konwersji i wyjaśniania kodu z wykorzystaniem AI.

## Funkcje

- 🔐 **System autoryzacji**: Rejestracja, logowanie, haszowanie hasła, odzyskiwanie hasła
- 📸 **Tłumaczenie ze zdjęcia**: Wczytaj kod ze zdjęcia i otrzymaj tłumaczenie/wyjaśnienie
- 📝 **Konwersja kodu między językami**: Wklej kod i skonwertuj go na inny język programowania
- 💬 **Chat z AI**: Rozmawiaj z AI głosem i tekstem
- 🎭 **Osobowości AI**: Wybierz spośród różnych osobowości (Sokrates, Nauczyciel, Ekspert, itp.)
- 🎤 **Wprowadzanie głosowe**: Transkrypcja audio do tekstu
- 🔊 **Wyjaśnienia głosowe**: Wyjaśnienia kodu za pomocą głosu
- 📊 **Dwa poziomy konwersji**: Prosty/ogólny i zaawansowany/rozbudowany
- 💰 **Śledzenie kosztów**: Monitoruj koszty prowadzonych rozmów
- 📜 **Historia**: Przechowuj historię konwersacji i konwersji kodu

## Wymagania

- Python 3.10 lub wyższy
- Klucz API OpenAI

## Instalacja

1. Zainstaluj zależności:
```bash
pip install -r requirements.txt
```

2. Utwórz plik `.env` w głównym katalogu projektu:
```
OPENAI_API_KEY=twoj_klucz_api_tutaj
```

3. Uruchom aplikację:
```bash
streamlit run app.py
```

Aplikacja będzie dostępna pod adresem: `http://localhost:8501`

## Struktura projektu

```
M_8/
├── app/
│   ├── data/          # Warstwa dostępu do danych
│   │   ├── db.py      # Połączenie z bazą danych
│   │   ├── schema.py  # Schemat bazy danych
│   │   ├── security.py # Funkcje bezpieczeństwa
│   │   └── users.py   # Operacje na użytkownikach
│   ├── services/      # Warstwa serwisów
│   │   ├── ai_service.py        # Serwis AI
│   │   ├── conversations.py     # Zarządzanie konwersacjami
│   │   ├── cost_tracking.py     # Śledzenie kosztów
│   │   ├── personalities.py     # Osobowości AI
│   │   └── socrates_handler.py  # Obsługa osobowości Sokrates
│   └── utils/         # Narzędzia pomocnicze
│       ├── auth.py    # Autoryzacja
│       └── navigation.py # Nawigacja
├── DATA/              # Baza danych SQLite
├── app.py             # Główny plik aplikacji
├── requirements.txt   # Zależności
└── README.md          # Ten plik
```

## Osobowości AI

- **Domyślna**: Standardowy asystent
- **Sokrates**: Nie udziela bezpośrednio odpowiedzi, zadaje pytania naprowadzające. Po trzykrotnym "nie wiem" udziela odpowiedzi.
- **Nauczyciel**: Cierpliwy nauczyciel wyjaśniający koncepcje krok po kroku
- **Ekspert**: Ekspert programistyczny z szczegółowymi, technicznymi wyjaśnieniami
- **Przyjazny dla początkujących**: Prosty język, bez żargonu technicznego

## Poziomy konwersji

- **Ogólny**: Podstawowa konwersja kodu bez dodatkowych wyjaśnień
- **Zaawansowany**: Szczegółowa konwersja z wyjaśnieniami każdej linii, różnic między językami i najlepszych praktyk

## Bezpieczeństwo

- Hasła są haszowane przy użyciu bcrypt
- Walidacja siły hasła
- Blokada konta po 3 nieudanych próbach logowania
- Kody odzyskiwania hasła
- Klucze licencyjne dla użytkowników

## Licencja

Projekt edukacyjny.

