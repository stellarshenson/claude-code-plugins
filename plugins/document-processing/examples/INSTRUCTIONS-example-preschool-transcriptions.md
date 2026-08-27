# Instrukcje Przetwarzania Transkrypcji Rozmów z Przedszkola

## Kontekst

Przetwarzanie transkrypcji rozmów alienowanego ojca Konrada Jelenia z pracownikami przedszkola dotyczących rozwoju 4-letniego syna Henryka Kabzy do formatu dziennika rozwojowego. Transkrypcje mogą być złej jakości pod kątem określenia rozmówcy, może być potrzebne rozumowanie odpowiednio przytaczające słowa odpowiedniej osobie na podstawie kontektstu.

## Struktura Katalogów

**MANDATORY**: Wszystkie operacje MUSZĄ używać ścieżek względnych od katalogu głównego projektu (`/home/lab/workspace/private/henryk/henryk-transcriptions/`).

```
henryk-transcriptions/           <- KATALOG GŁÓWNY PROJEKTU
├── 1-input/                     <- transkrypcje do przetworzenia
├── 2-work-in-progress/          <- pliki robocze (założenia, checklisty)
│   └── <nazwa-notatki>/         <- podkatalog per transkrypcja
├── 3-output/                    <- finalne notatki
├── 4-examples/                  <- przykłady notatek (nie modyfikować)
├── 5-archive/                   <- archiwum Parquet
├── assistants/                  <- szablony przetwarzania (nie modyfikować)
├── src/                         <- narzędzia Python
└── INSTRUCTIONS.md              <- ten plik
```

**Zasady**:
- Pliki robocze ZAWSZE w `2-work-in-progress/<nazwa-notatki>/` (od katalogu głównego projektu)
- Finalne notatki ZAWSZE w `3-output/` (od katalogu głównego projektu)
- NIE tworzyć katalogów poza strukturą projektu
- Przed utworzeniem katalogu zweryfikować że `pwd` wskazuje na katalog główny projektu

## Reguły Uniformizacji

Finalna notatka MUSI spełniać następujące kryteria:

### R1: Długość Notatki
- **Zakres**: 350-500 słów (sekcja notatki, bez sekcji Kluczowe Wydarzenia/Wyzwania/Postępy)
- **Preferowane**: Krótsze notatki - celuj w dolną granicę (350-400 słów)
- **Górna granica (500 słów)**: TYLKO gdy treść rozmowy tego wymaga
- **Zasada**: Zawsze wybieraj krótszą notatkę zamiast dłuższej - zwięzłość jest priorytetem
- **Wyjątek**: Notatki 500-600 słów TYLKO w wyjątkowych przypadkach złożonych rozmów z wyraźnym uzasadnieniem
- **Krótka transkrypcja**: Jeśli źródło jest na tyle krótkie że uczciwe osiągnięcie 350 słów wymagałoby dopisywania treści bez wartości, dopuszczalna jest notatka 320-350 słów. Lepsza krótsza notatka z samą substancją niż dłuższa z wypełniaczem

### R0: Brak Wypełniacza (no-fluff)
Notatka zawiera zdania nośne (load-bearing) - fakty, obserwacje, konkretne wydarzenia - oraz minimalną ilość "miękkości" potrzebną do płynności narracji. NIE zawiera zdań które nic nie wnoszą:
- **Brak metapreambuły**: Nie zaczynaj od zdań typu "Rozmawiałem dziś z Panią X" (tytuł notatki już to mówi) ani "Rozmowa dotyczyła przede wszystkim A, B oraz C" (spis treści - czytelnik sam przeczyta treść). Zacznij od pierwszego faktu nośnego
- **Brak pustych zdań podsumowujących**: Nie pisz "To istotny krok" / "To ważny sygnał" / "Sytuacja jest poważna" jako samodzielnych zdań bez nowej informacji - jeśli komentarz nie dodaje treści, usuń go; jeśli dodaje, połącz z faktem
- **Test**: Każde zdanie musi zmieniać to, co czytelnik wie. Jeśli usunięcie zdania nie zmienia stanu wiedzy czytelnika - usuń je

### R2: Skupienie na Dziecku
Notatka ma dokumentować rozwój dziecka, NIE doświadczenia ojca. Usuń:
- Wyrażanie uczuć ojca: "Najboleśniejszym dla mnie...", "Ucieszyło mnie...", "Martwię się..."
- Osobiste nadzieje: "Mam nadzieję że...", "Być może w końcu..."
- Osobiste wyjaśnienia: "Nie mam skąd uzyskać informacji...", "Nie wiedziałem gdzie..."
- Prośby ojca: "Poprosiłem o...", "Zasugerowałem żeby..."
- Kontekst sytuacji ojca/dziadków: "Moi rodzice również nie mogli..."

**Zachowaj TYLKO**:
- Fakty o rozwoju Henryka
- Obserwacje nauczycieli o Henryku
- Kontekst wydarzeń wpływających na Henryka (np. "Sąd skierował na terapię rodzinną")

### R3: Format Tekstu
- **Paragrafy**: Jedna pusta linia między paragrafami (NIE dwie)
- **Hiperlinki**: Brak (http://, https://, www., [tekst](link))
- **Encoding**: UTF-8

### R4: Sekcje Wyzwania/Postępy
- Format: Lista faktów, nie osobiste spostrzeżenia
- Długość punktu: 15-30 słów
- Liczba punktów: 1-5 w każdej sekcji (Kluczowe Wydarzenia, Wyzwania, Postępy)

## Workflow Przetwarzania

Dla podanej transkrypcji wykonaj następujące kroki:

### 1. Odczyt Transkrypcji
- Przeczytaj wskazany plik transkrypcji z katalogu `1-input/`
- Zidentyfikuj datę, uczestników rozmowy i główne tematy

### 2. Generowanie Notatki
- Przetworz transkrypcję używając instrukcji z `assistants/PRZEDSZKOLE-NOTATKI.md`
- Wygeneruj notatkę w pierwszej osobie (perspektywa Konrada)
- Długość: celuj w 350-400 słów, maksymalnie 500 słów gdy treść tego wymaga (priorytet: zwięzłość)
- Format: markdown z paragrafami oddzielonymi pojedynczymi pustymi liniami
- Nie wolno umieszczać żadnych linków w dokumencie końcowym, trzymaj się formatu z przykładów
- **Zacznij od pierwszego faktu nośnego** - bez metapreambuły ("Rozmawiałem dziś z...", "Rozmowa dotyczyła A, B, C"). Tytuł notatki już identyfikuje rozmowę. Pisz zdania nośne plus minimum miękkości dla płynności; unikaj wypełniacza (patrz R0 w Regułach Uniformizacji)

### 3. Weryfikacja Notatki
- Utwórz katalog `2-work-in-progress/<nazwa-notatki>/`
- Wygeneruj plik `<nazwa-notatki>-assumptions.md` zawierający:
  - Kluczowe założenia i twierdzenia z notatki
  - Źródłowe fragmenty transkrypcji potwierdzające każde twierdzenie
  - Zidentyfikowane nieścisłości lub brakujące potwierdzenia

### 4. Korekta Nieścisłości
- Przeanalizuj plik assumptions.md
- Nanieś poprawki do notatki aby wszystkie twierdzenia miały potwierdzenie w transkrypcji
- Zapisz poprawioną notatkę w katalogu roboczym

### 5. Generowanie Wyzwań i Postępów
- Przetworz zweryfikowaną notatkę używając `assistants/PRZEDSZKOLE-WYZWANIA.md`
- Wygeneruj trzy sekcje:
  - **Kluczowe Wydarzenia** (1-5 punktów, 15-30 słów każdy)
  - **Wyzwania** (1-5 punktów, 15-30 słów każdy)
  - **Postępy** (1-5 punktów, 15-30 słów każdy)

### 6. Weryfikacja Wyzwań i Postępów
- W katalogu roboczym utwórz plik `<nazwa-notatki>-challenges-verification.md`
- Sprawdź czy każdy punkt znajduje potwierdzenie w notatce
- Nanieś poprawki jeśli potrzeba

### 7. Finalna Kompilacja
- Połącz notatkę z sekcjami wyzwań i postępów
- Zapisz finalny dokument w katalogu `3-output/`
- Nazwa pliku: `<data>-<krótki-opis>.md` (np. `2025-07-11-henryk-nie-nosi-pieluszki.md`)
- Format końcowy: notatka + trzy sekcje na końcu

### 8. Uniformizacja

**A. Utwórz Checklistę Weryfikacyjną**
- W katalogu roboczym `2-work-in-progress/<nazwa-notatki>/` utwórz plik `<nazwa-notatki>-uniformization-checklist.md`
- Sprawdź zgodność z każdą regułą z sekcji "Reguły Uniformizacji"
- Dla każdej reguły: podaj status (✓/❌), liczby/cytaty, i akcje do wykonania

**Format checklisty:**
```markdown
# Checklist Uniformizacji

## R0: Brak Wypełniacza
- [ ] Metapreambuła ("Rozmawiałem dziś z...", "Rozmowa dotyczyła A, B, C"): [cytat lub BRAK]
- [ ] Puste zdania podsumowujące ("To istotny krok", "Sytuacja jest poważna" bez nowej treści): [lista lub BRAK]
- [ ] Test "czy zdanie zmienia stan wiedzy czytelnika" przeszedł dla wszystkich zdań: TAK/NIE
- [ ] Akcja: [usunąć/połączyć X zdań / OK]

## R1: Długość Notatki
- [ ] Liczba słów w notatce: XXX
- [ ] W zakresie 350-500: TAK/NIE
- [ ] Preferowana długość (350-400 słów): TAK/NIE
- [ ] Jeśli krótka transkrypcja i 320-350 słów: czy dopisywanie do 350 wymagałoby wypełniacza? (jeśli tak - 320-350 OK)
- [ ] Jeśli > 400: Czy treść wymaga większej długości?
- [ ] Jeśli > 500: Uzasadnienie złożoności
- [ ] Akcja: [skrócić do 350-400 słów / OK]

## R2: Skupienie na Dziecku
- [ ] Wyrażanie uczuć ojca: [lista cytatów lub BRAK]
- [ ] Osobiste nadzieje: [lista cytatów lub BRAK]
- [ ] Osobiste wyjaśnienia: [lista cytatów lub BRAK]
- [ ] Prośby ojca: [lista cytatów lub BRAK]
- [ ] Kontekst ojca/dziadków: [lista cytatów lub BRAK]
- [ ] Akcja: [usunąć X fragmentów / OK]

## R3: Format Tekstu
- [ ] Paragrafy - jedna pusta linia: TAK/NIE
- [ ] Hiperlinki: [liczba znalezionych lub BRAK]
- [ ] Encoding UTF-8: TAK/NIE
- [ ] Akcja: [poprawić formatowanie / OK]

## R4: Sekcje Wyzwania/Postępy
- [ ] Format: fakty vs osobiste (liczba naruszeń: X)
- [ ] Długość punktów: [punkty poza zakresem 15-30 słów]
- [ ] Liczba punktów: KW:X, W:X, P:X (w zakresie 1-5: TAK/NIE)
- [ ] Akcja: [przeformułować X punktów / OK]
```

**B. Wykonaj Korekty**
- Na podstawie checklisty nanieś wszystkie wymagane poprawki
- Usuń wypełniacz zgodnie z R0 (metapreambuła, puste zdania podsumowujące) - zacznij notatkę od pierwszego faktu nośnego
- Skróć notatkę preferując dolną granicę zakresu (350-400 słów), maksymalnie 500 słów gdy treść wymaga; przy krótkiej transkrypcji 320-350 słów jest OK zamiast dopisywania wypełniacza
- Usuń wszystkie naruszenia R2 (spostrzeżenia ojca o sobie)
- Popraw formatowanie zgodnie z R3
- Przeformułuj sekcje zgodnie z R4

**C. Finalna Weryfikacja**
- Zaktualizuj checklistę po poprawkach
- Upewnij się że wszystkie reguły mają status ✓
- Zapisz ostateczną wersję do `3-output/`

### 9. Archiwizacja

**MANDATORY**: Po zakończeniu uniformizacji, zarchiwizuj przetworzoną transkrypcję.

**Wykonanie**:
```bash
python src/archive_transcription.py \
  --transcription "1-input/<nazwa-pliku-transkrypcji>.txt" \
  --note "3-output/<nazwa-notatki>.md" \
  --checklist "2-work-in-progress/<nazwa-notatki>/<nazwa-notatki>-uniformization-checklist.md"
```

**Archiwizowane dane**:
- Pełny tekst oryginalnej transkrypcji
- Pełny tekst finalnej notatki (ze wszystkimi sekcjami)
- Statystyki przetwarzania:
  - Liczba słów (transkrypcja, notatka, total)
  - Liczba naruszeń (R1, R2, R3, R4)
  - Liczba punktów w sekcjach (Wydarzenia, Wyzwania, Postępy)
- Metadata: daty, nazwy plików, data przetworzenia

**Rezultat**:
- Rekord dodany do `5-archive/transcriptions_archive.parquet`
- Skompresowane archiwum wszystkich przetworzonych transkrypcji
- Umożliwia wyszukiwanie, statystyki i analizę jakości

**Zobacz**: `5-archive/README.md` dla szczegółów schematu i przykładów zapytań

## Przykłady

Zobacz przykładowe wpisy w:
- `4-examples/example_entry1.md`
- `4-examples/example_entry2.md`

## Wykonanie

Aby przetworzyć transkrypcję, użyj polecenia:
```
execute @INSTRUCTIONS.md for <nazwa-pliku-transkrypcji>
```
