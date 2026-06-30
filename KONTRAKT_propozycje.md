# KONTRAKT STYKU — „propozycja automatu ↔ bramka akceptacji operatora"

> Dwustronny interfejs między pasem AUTOMATU (Artur) a pasem BRAMKI/OPERATORA (Sylwia).
> Każdy wypełnia SWOJĄ stronę na gałęzi → PR → druga strona zatwierdza (review = obustronne
> potwierdzenie) → wpisujemy do „UZGODNIONE". **Dopóki UZGODNIONE nie domknięte — nikt nie koduje
> swojej strony.** Git = wersje (historia = negocjacja).

---

## STRONA AUTOMATU (wypełnia Artur) — PROPOZYCJA v0 (do dyskusji)

Automat, po przeliczeniu case'a, zapisuje **propozycję akcji** do Firestore (kolekcja `propozycje`),
ze `status="do_akceptacji"`. Bramka operatora czyta `do_akceptacji`, pokazuje, ustawia decyzję.
Automat NIE wykonuje akcji przed `zielonym` (faza 1 = człowiek w pętli).

Proponowany schemat dokumentu:
```json
{
  "id": "uuid",
  "created_at": 1782740000,
  "status": "do_akceptacji",        // do_akceptacji → zaakceptowana | odrzucona | wykonana | wyjatek
  "test_mode": true,                // faza shadow

  "sprawa": {                       // skąd, czego dotyczy
    "nrZam": 378663, "dokId": 0, "pz": "pz2", "grupa": "DE",
    "kanal_zrodlo": "whatsapp"      // skąd przyszedł kontekst (WA/email/eBay)
  },

  "typ": "wiadomosc",               // "wiadomosc" | "kurier"  (rozszerzalne)
  "akcja": {
    // typ=wiadomosc:
    "kanal": "whatsapp", "recipient": "48695287327", "tresc": "<draft do klienta>",
    // typ=kurier (zamiast powyższego):
    "awizacja": { "...": "blok zlecenia jak w awizacje_kurier (CreateZwrotka, faza 1 UPS skrzynia)" }
  },

  "kontekst": {                     // co automat wziął pod uwagę (do wglądu operatora)
    "rolka_skrot": "<skrót rozmowy WA/mail>", "fakty": { "...": "..." }
  },
  "uzasadnienie": "<dlaczego automat to proponuje, krótko>",

  // pola wypełniane przez BRAMKĘ (Sylwia) — automat ich NIE dotyka po utworzeniu:
  "decyzja": null,                  // "zielony" | "czerwony"
  "komentarz": null,                // komentarz operatora/wdrażającego (zwł. przy czerwonym)
  "decydent": null, "decyzja_at": null
}
```

Założenia od strony automatu (do potwierdzenia przez bramkę):
- Automat tworzy dok ze `status="do_akceptacji"` i NIE rusza go potem (jak w awizacjach).
- Po `zielony`: wykonanie (wysyłka przez bramę / awizacja kuriera) robi… ⬜ DO USTALENIA: automat
  (poll po decyzji) czy osobny worker? — zapisać tu.
- Idempotencja: jedna propozycja per (nrZam, typ) w danym oknie? ⬜ DO USTALENIA.

PYTANIA AUTOMATU DO BRAMKI:
1. Jakich pól bramka POTRZEBUJE, żeby ładnie wyrenderować zielony/czerwony + panel odrzutów?
2. Czy „czerwony" ma podtypy („do poprawy" vs „wyślij jednak")? Jak je kodujemy?
3. Kto wykonuje akcję po `zielony` — automat czy worker bramki?

---

## STRONA BRAMKI / OPERATORA (wypełnia Sylwia)

⬜ TODO (Sylwia): czego bramka potrzebuje od propozycji (pola do renderu zielony/czerwony),
schemat odrzutu + komentarza, jak działa panel odrzutów, kto wykonuje akcję po `zielony`.

---

## UZGODNIONE (wpisujemy DOPIERO po obustronnym potwierdzeniu)

⬜ (puste — domkniemy po zgraniu obu stron).
