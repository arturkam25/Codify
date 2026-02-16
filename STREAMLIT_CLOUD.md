# Wdrożenie na Streamlit Cloud z trwałą historią użytkowników

Na Streamlit Cloud **dysk w kontenerze jest tymczasowy**. Przy każdym redeployu lub restarcie aplikacji plik bazy SQLite (`DATA/codify.db`) znika, więc użytkownicy i historia konwersacji się nie zapisują.

Żeby na Cloud miała być **trwała historia użytkowników** (konta, konwersacje, koszty), trzeba użyć **zewnętrznej bazy PostgreSQL** i podać jej adres w **Secrets** aplikacji.

---

## Co zrobić krok po kroku

### 1. Załóż zewnętrzną bazę PostgreSQL (darmowy plan)

Wybierz **jedną** z opcji:

- **[Supabase](https://supabase.com)** – darmowy plan, po rejestracji: Project → Settings → Database → "Connection string" (URI).
- **[Neon](https://neon.tech)** – darmowy plan, po utworzeniu projektu: Connection string (np. `postgresql://user:pass@ep-xxx.region.aws.neon.tech/neondb?sslmode=require`).
- **[ElephantSQL](https://www.elephantsql.com)** – darmowy plan, po utworzeniu instance: Details → URL.

Skopiuj **pełny URL** w formacie:
```text
postgresql://USER:HASLO@HOST:PORT/NAZWA_BAZY
```
(lub `postgres://...` – aplikacja obsługuje oba).

### 2. Ustaw Secrets w Streamlit Cloud

1. Wejdź na [share.streamlit.io](https://share.streamlit.io), zaloguj się, wybierz swoją aplikację.
2. **Settings** (ikona zębatki) → **Secrets**.
3. Wklej konfigurację w formacie TOML:

```toml
[database]
url = "postgresql://USER:HASLO@HOST:PORT/NAZWA_BAZY"
```

Zamień `USER`, `HASLO`, `HOST`, `PORT`, `NAZWA_BAZY` na wartości z panelu Supabase/Neon/ElephantSQL. W hasle nie używaj znaków `"`, `#`, `'` – albo zamień je na odpowiednie znaki w URL, albo ustaw hasło bez tych znaków.

4. Zapisz (**Save**).

### 3. Redeploy aplikacji

W Streamlit Cloud: **Manage app** → **Reboot app** (albo wypchnij nowy commit do repozytorium, żeby zrobił się deploy). Po restarcie aplikacja odczyta Secrets i połączy się z PostgreSQL zamiast z lokalnym SQLite.

---

## Co się zmienia w działaniu

| Środowisko | Baza danych | Efekt |
|------------|-------------|--------|
| **Lokalnie** (bez ustawionego Secrets / `DATABASE_URL`) | SQLite w pliku `DATA/codify.db` | Jak dotąd – dane lokalne, bez Cloud. |
| **Streamlit Cloud** (z ustawionym `[database] url` w Secrets) | PostgreSQL (Supabase/Neon/itd.) | Użytkownicy, konwersacje i koszty są **trwale** zapisane w zewnętrznej bazie; po każdym redeployu dane zostają. |

---

## Opcjonalnie: zmienna środowiska zamiast Secrets

Zamiast Secrets możesz ustawić w Streamlit Cloud zmienną środowiska **`DATABASE_URL`** (w ustawieniach aplikacji), z tym samym URL-em PostgreSQL. Aplikacja najpierw sprawdza `st.secrets["database"]["url"]`, a jeśli go nie ma – używa `os.environ.get("DATABASE_URL")`.

---

## Uwagi

- **Plik bazy (`*.db`) nie trafia do Gita** – i nie powinien. Trwałość na Cloud zapewnia **tylko** zewnętrzna baza (PostgreSQL) i jej adres w Secrets (lub `DATABASE_URL`).
- Przy **pierwszym** uruchomieniu z nową bazą PostgreSQL aplikacja sama utworzy tabele (użytkownicy, konwersacje, wiadomości, koszty itd.). Potem trzeba się zarejestrować lub utworzyć konto admina tak jak lokalnie.
- Jeśli w Supabase/Neon masz włączone **SSL**, w URL często dodaje się `?sslmode=require` (np. Neon to wymaga). Przykład:  
  `postgresql://user:pass@host/db?sslmode=require`
