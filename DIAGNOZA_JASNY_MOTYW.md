# Diagnoza trybu jasnego – Codify

## 1. Przepływ aplikacji i miejsce motywu

### Inicjalizacja
- **app.py** ok. 105–106: `st.session_state.theme` domyślnie `"dark"`.
- **Strony bez globalnego motywu** (własny CSS, bez sidebaru): `landing`, `login`, `register`, `forgot_password`.
- **Strony z globalnym motywem** (ciemny/jasny z app.py): po zalogowaniu – `dashboard`, `chat`, `image_translate`, `text_translate`, `costs`, `admin_users`.

### Gdzie stosowany jest globalny CSS
- **app.py** ok. 893–1082: po sprawdzeniu `authenticated` i `user` wywoływane jest `theme = st.session_state.get("theme", "dark")`, potem jeden z dwóch bloków `st.markdown("<style>...</style>")` (dark vs light). Ten sam blok obowiązuje na wszystkich stronach zalogowanych (dashboard, chat, tłumaczenie, koszty, admin).

### Nawigacja
- **navigation.py** ok. 54–60: kolory nagłówków sidebara zależą od `theme` (jasny: szary, ciemny: złoty).
- **navigation.py** ok. 189–204: radio MOTYW (Ciemny/Jasny) z `st.rerun()` po zmianie.

---

## 2. Wszystkie ścieżki zależne od motywu (app.py)

| Miejsce | Linie (approx) | Opis |
|--------|----------------|------|
| Global CSS dark/light | 901–1082 | Jeden z dwóch pełnych bloków CSS. |
| Rejestracja | 485–520 | Light: osobny CSS formularza i expandera. |
| Dashboard | 1097–1167 | Kolory tytułu, obramowania, welcome box. |
| Chat – sekcja głosu | 1614–1634 | Kolory kontenera głosu i ikony mikrofonu. |
| Chat – pole input | 1814–1828 | Tło i obramowanie chat input (light: białe/szare). |
| image_translate – bloki kodu / wyjaśnienie | 2220–2223, 2474–2477 | `_pre_bg`, `_pre_fg`, `_h4_color` dla HTML alternatyw i nagłówków. |
| Admin – zakładki | 2810–2878 | `_admin_tabs_css` – styl listy zakładek i aktywnych tabów (light vs dark). |

---

## 3. Zidentyfikowane problemy w trybie jasnym

### 3.1 Sidebar – nadpisanie kolorów komunikatów
- **Reguła:** `[data-testid="stSidebar"] * { color: var(--text-primary) !important; }` (light, ok. 984).
- **Efekt:** Wszystkie elementy w sidebarze dostają kolor `#111827`. Komunikaty `st.success`, `st.info`, `st.warning` w sidebarze (np. „Klucz API zapisany!”, „Nie wprowadzono klucza API”) mogą być wizualnie sprowadzone do jednego koloru, jeśli selektor typu `.stSuccess *` nie wygra (zależnie od struktury DOM i specyficzności).
- **Rekomendacja:** Dodać po tej regule jawne nadpisania kolorów dla alertów w sidebarze (np. `.stAlert`, `.stSuccess`, `.stInfo`, `.stWarning`, `.stError`), żeby zachować kolory semantyczne.

### 3.2 Ukrywanie podpowiedzi „Press Enter to submit”
- **Reguła:** `[data-testid="stInputHint"], ..., p[data-testid="stCaption"] { display: none !important; ... }` (dark i light).
- **Ryzyko:** Jeśli Streamlit używa `stCaption` lub podobnego testid gdzie indziej (np. pod innymi widgetami), tekst może być ukrywany globalnie.
- **Rekomendacja:** Zawęzić ukrywanie do sidebara: np. `[data-testid="stSidebar"] [data-testid="stInputHint"]`, `[data-testid="stSidebar"] p[data-testid="stCaption"]`, żeby nie wpływać na treść w main.

### 3.3 Biała karta / tło w trybie jasnym
- **Obszary:** Tłumaczenie kodu (image_translate), Zarządzanie użytkownikami (zakładki admin).
- **Obecne rozwiązanie:** Reguły typu `.main .block-container`, `.main .element-container`, `.main .stTabs ...`, `div:has([data-testid="stMarkdownContainer"])` z `background: transparent !important;`.
- **Uwaga:** Struktura DOM zakładek (`.stTabs > div > div:last-child`) może się różnić między wersjami Streamlit – wtedy „ostatni div” może być innym elementem niż panel treści. W razie problemów warto ograniczyć się do selektorów `[data-baseweb="tab-panel"]` / `div[role="tabpanel"]` i kontenerów wewnątrz `.main .stTabs`.

### 3.4 Konfiguracja bazowa Streamlit (config.toml)
- **.streamlit/config.toml:** `base = "dark"`, złote kolory, ciemne tła.
- **Efekt:** Streamlit ładuje domyślnie motyw ciemny. Nasz własny CSS w app.py nadpisuje wygląd w obu trybach, ale pierwsze renderowanie lub elementy poza naszymi selektorami mogą chwilowo lub lokalnie używać kolorów z config.toml. W trybie jasnym może to dawać mieszankę (np. białe tło z config vs nasz `--bg`).

### 3.5 Strony bez uwzględnienia motywu
- **Login:** Zawsze ciemny złoty styl (bez sprawdzania `theme`).
- **Register:** Sprawdza `_reg_theme == "light"` i stosuje jasny CSS.
- **Forgot password:** Własny ciemny styl, bez warunku na `theme`.

Efekt: użytkownik z ustawionym motywem „Jasny” po wejściu na login/forgot_password zobaczy ciemny interfejs; po zalogowaniu – jasny. Może to odbierane być jako niespójność.

### 3.6 Możliwe konflikty specyficzności
- W bloku light wiele reguł używa `!important`. Kolejność w jednym bloku `<style>` decyduje o wygranej. Ogólne reguły typu `p, span, li, div[data-testid="stMarkdownContainer"] * { color: var(--text-primary) }` mogą kolidować z `.stSuccess *`, `.stInfo *` itd. – w sidebarze już jest ryzyko z p. 3.1.

---

## 4. Rekomendowane zmiany (kolejność priorytetu)

1. **Sidebar – kolory alertów (light):**  
   Dodać po regule `[data-testid="stSidebar"] *` jawne reguły dla alertów, np.  
   `[data-testid="stSidebar"] .stAlert, [data-testid="stSidebar"] .stSuccess, [data-testid="stSidebar"] .stSuccess *` (kolor zielony/niebieski/żółty/czerwony), i analogicznie dla `.stInfo`, `.stWarning`, `.stError`, żeby komunikaty w sidebarze były czytelne i semantyczne.

2. **Ukrywanie podpowiedzi:**  
   Zawęzić do sidebara (np. prefiks `[data-testid="stSidebar"]` dla selektorów hint/caption), żeby nie ukrywać ewentualnych podpisów w głównej treści.

3. **Strony login / forgot_password:**  
   Opcjonalnie: dodać warunek na `theme == "light"` i osobny, prosty zestaw stylów jasnych (tło, przyciski, pola), żeby przejście z rejestracji (gdzie light jest) na login było spójne.

4. **Zakładki (admin / ogólnie):**  
   W razie dalszych problemów z „białą kartą” w trybie jasnym: usuwać z zestawu reguł selektor `.main .stTabs > div > div:last-child` i polegać na `[data-baseweb="tab-panel"]`, `div[role="tabpanel"]` oraz `.main .stTabs .element-container` / `.main .stTabs [data-testid="stVerticalBlock"]`.

5. **Dokumentacja / utrzymanie:**  
   W komentarzu przy bloku light w app.py krótko opisać, że kolory sidebara są nadpisywane, a alerty w sidebarze mają osobne reguły dla czytelności.

---

## 5. Podsumowanie

- Tryb jasny jest w pełni obsługiwany tylko **po zalogowaniu** (jedna gałąź CSS w app.py + style per strona).
- **Login / forgot_password** nie respektują wyboru motywu.
- W trybie jasnym **sidebar** wymusza jeden kolor dla wszystkich elementów; **komunikaty success/info/warning** mogą tracić kolory – warto dodać dla nich jawne reguły w sidebarze.
- **Ukrywanie podpowiedzi** przy kluczu API jest globalne; bezpieczniej ograniczyć je do sidebara.
- **Biała karta** na tłumaczeniu i w zakładkach admin jest łagodzona przez transparentne tła; ewentualne dalsze problemy warto rozwiązywać zawężeniem selektorów do tab-panel/role="tabpanel" i kontenerów treści.

Po wdrożeniu punktów 1 i 2 (alerty w sidebarze + zawężenie ukrywania hintów) tryb jasny powinien być bardziej przewidywalny i spójny; punkty 3–5 można wdrażać stopniowo w zależności od potrzeb.
