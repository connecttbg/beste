
Beste Negler – prosty sklep dropshipping (Flask)

1. Stwórz i aktywuj virtualenv, następnie zainstaluj zależności:
   pip install -r requirements.txt

2. Uruchom aplikację:
   python app.py

3. Pierwsze uruchomienie utworzy bazę SQLite (beste_negler.db).
   Aby mieć konto admina, w Python shellu (wewnątrz aplikacji) utwórz użytkownika
   i ustaw mu is_admin = True.

4. Panel admina:
   /admin/products – lista produktów
   /admin/import   – import z pliku CSV o nagłówkach:
   "sku";"EAN";"name";"description";"category";"weight";"qty";"price";"tax";"brand";"images"

5. Opisy produktów:
   - description_no: opis norweski
   - description_en: opis angielski; jeśli pusty, można dodać integrację z zewnętrznym API
     tłumaczeniowym w funkcji translate_text w app.py.
