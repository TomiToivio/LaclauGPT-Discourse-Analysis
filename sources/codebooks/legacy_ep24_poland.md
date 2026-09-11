# EP24 codebook — Poland (Polska)

Codebook for the EP24 Poland reprocessing pilot (issue #73).
Grounded in: legacy `entities.xlsx` canonical mappings (79 Poland
entities), research diary mentions (PL identifiers, 160 diary rows),
and public sources (Wikipedia pl/en summaries verified 2026-09-08;
Yle Uutiset Polish-election coverage as the Finnish public-source
view of the Polish campaign).

## Parties (actors, kind=actor)

| Canonical label | Short (pl) | Family (legacy bucket) |
|---|---|---|
| Law and Justice (Poland) | PiS | Far right |
| Civic Coalition (Poland) | Koalicja Obywatelska | Centre right |
| Third Way (Poland) | Trzecia Droga | Centre right |
| Left (Poland) | Lewica | Red-green |
| Confederation Liberty and Independence (Poland) | Konfederacja | Far right |
| Polish People's Party (Poland) | PSL | Centre right |
| National Movement (Poland) | Ruch Narodowy | Far right |
| New Left (Poland) | Nowa Lewica | Red-green |

## Politicians (entities verified in legacy data + diaries)

- Jarosław Kaczyński (Law and Justice; Poland) — top diary mention
- Donald Tusk (Civic Coalition; Poland) — PM, top diary mention
- Radosław Sikorski (Civic Coalition; Poland)
- Andrzej Halicki (Civic Coalition; Poland)
- Dominik Tarczyński (Law and Justice; Poland)
- Jacek Kurski (Law and Justice; Poland)
- Katarzyna Pełczyńska-Nałęcz (Third Way; Poland)
- Ryszard Petru (Third Way; Poland)
- Marcin Kierwiński (Civic Coalition; Poland)
- Michał Wawrykiewicz (Civic Coalition; Poland)
- Bronisław Komorowski (Civic Coalition; Poland) — former President
- Dorota Anna Kolarska (The Left; Poland)
- Marcin Banot (Others; Poland)
- Antoni Macierewicz (Law and Justice; Poland) — diary mention
- Andrzej Duda (PiS-aligned president, heavily referenced)

## Seed signifiers (paper §2.2, EP24-tuned)

- artificial intelligence
- wybory do Parlamentu Europejskiego / EP elections
- krytyka UE (EU criticism)
- klimat (climate)
- imigracja (immigration)
- bezpieczeństwo (security, war-in-Ukraine border context)
- polska wieś (rural Poland, PSL framing)
- suwerenność (sovereignty framing)
- praworządność (rule of law framing, Tusk–PiS axis)
- ceny energii (energy prices)

## Country context (injected into prompts via topic_background)

Poland holds 53 EP seats (largest gain after Brexit redistribution).
Election day 2024-06-09, mid-cycle of the Tusk coalition (Civic
Coalition–Third Way–Left) versus the opposition PiS, with
Confederation to their right. Campaign axes: sovereignty vs
integration, rule-of-law dispute with the previous government, war
neighbours (Ukraine) framing, and farm-sector discontent (PSL base).
Top themes from the legacy theme mappings: far-right parties,
campaign and campaigning, economy and finance, grievance politics,
voters and voting.

## Sources for this codebook

- Wikipedia (pl): Wybory do Parlamentu Europejskiego w Polsce w 2024
  roku; party pages (PiS, Platforma Obywatelska, Konfederacja Wolność
  i Niepodległość, Polska 2050, Nowa Lewica, PSL) — verified 2026-09-08
- Yle Uutiset (fi) coverage of the Polish EP election — public source
- Legacy `entities.xlsx` (79 Poland rows) and research diary
  PL-identifier rows (160) from the EP24 dashboard workbook