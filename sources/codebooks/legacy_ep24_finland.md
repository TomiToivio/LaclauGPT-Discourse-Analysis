# EP24 codebook — Finland (Suomi)

Codebook for the EP24 Finland reprocessing pilot (issue #73).
Grounded in: legacy `entities.xlsx` canonical mappings (54 Finland
entities), research diary mentions (FI identifiers, 158 diary rows),
and public sources (Wikipedia fi/en summaries verified 2026-09-08;
Yle Uutiset as the Finnish public-source reference for campaign
coverage).

## Parties (actors, kind=actor)

| Canonical label | Short | Family (legacy "political_preference" bucket) |
|---|---|---|
| National Coalition Party (Finland) | Kokoomus | Centre right |
| Finns Party (Finland) | Perussuomalaiset | Far right |
| Finnish Social Democratic Party (Finland) | SDP | Red-green |
| Green League (Finland) | Vihreä liitto | Red-green |
| Left Alliance (Finland) | Vasemmistoliitto | Red-green |
| Centre Party (Finland) | Keskusta | Centre right |
| Swedish People's Party of Finland | RKP | Centre right |
| Christian Democrats (Finland) | Kristillisdemokraatit | Centre right |
| Movement Now (Finland) | Liike Nyt | Others |

## Politicians (entities verified in legacy data + diaries)

- Petteri Orpo (National Coalition Party; Finland) — PM, not an EP candidate but heavily referenced
- Riikka Purra (Finns Party; Finland) — Finance Minister
- Jussi Saramo (Left Alliance; Finland)
- Sirpa Pietikäinen (National Coalition Party; Finland) — incumbent MEP
- Jenna Simula (Finns Party; Finland)
- Kaisa Juuso (Finns Party; Finland)
- Mari Rantanen (Finns Party; Finland)
- Pekka Toveri (National Coalition Party; Finland)
- Simo Grönroos (Finns Party; Finland)
- Ville Merinen (Finnish Social Democratic Party; Finland)
- Antti Lindtman (Finnish Social Democratic Party; Finland)
- Sebastian Tynkkynen (Finns Party; Finland) — top diary mention
- Li Andersson (Left Alliance; Finland) — lead EP candidate
- Henna Virkkunen (National Coalition Party; Finland) — incumbent MEP
- Eero Heinäluoma (Finnish Social Democratic Party; Finland)

## Seed signifiers (paper §2.2, EP24-tuned)

- artificial intelligence
- europarlamenttivaalit / EP elections
- EU-kritiikki (EU criticism)
- ilmasto (climate)
- maahanmuutto (immigration)
- turvallisuus (security, NATO context)
- hyvinvointivaltio (welfare state)
- kalliiden energian syyllisyys (energy prices)
- suomalainen työ (Finnish labour framing)
- maataloustuet (CAP subsidies)

## Country context (injected into prompts via topic_background)

Finland holds 15 EP seats (up from 14 after Brexit adjustment).
Election day 2024-06-09. Government at election time: Orpo cabinet
(Kokoomus–Finns Party–RKP–Christian Democrats), which made the EP
campaign an opposition-to-own-government dynamic for SDP and Left
Alliance, and a coalition-defence dynamic for the government parties.
Top themes from the legacy theme mappings (122 canonical themes;
Finland-relevant concentration): far-right parties, economy and
finance, climate and sustainability, security, farming subsidies.

## Sources for this codebook

- Wikipedia (fi): Suomen europarlamenttivaalit 2024; party pages
  (Kokoomus, Perussuomalaiset, SDP, Vihreä liitto, Vasemmistoliitto,
  RKP) — verified 2026-09-08
- Yle Uutiset (fi): EP2024 campaign coverage archive — public source
- Legacy `entities.xlsx` (54 Finland rows) and research diary
  FI-identifier rows (158) from the EP24 dashboard workbook