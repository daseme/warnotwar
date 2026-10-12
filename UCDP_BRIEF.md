# UCDP and the map: what we learned, and what a sync would change

Written 2026-10-11 from the UCDP codebooks, the full GED 26.1 file (1989 to 2025), the three 2026 candidate files (January to August), the UCDP/PRIO, dyadic, non-state, one-sided and actor datasets at version 26.1, the ESD 18.1 codebook, and the 2026 Journal of Peace Research article. Every number below is our own sum of UCDP's `best` column, with `low` and `high` where they matter. Working files are in the session scratchpad; the sources are listed at the end.

## 1. How UCDP counts

**Three kinds of organized violence, each with a 25-death floor per calendar year.**

- *State-based armed conflict*: a contested incompatibility over government or territory, armed force between two parties, at least one a state, at least 25 battle-related deaths in the year. The "government" is whoever holds the capital, so in Yemen the Houthis are the government and the Presidential Leadership Council is the rebel.
- *Non-state conflict*: armed force between two organized groups, neither a government, 25 deaths. Cartels count.
- *One-sided violence*: a government or an organized group killing civilians, 25 deaths per actor per year.

**Minor and war.** A state-based conflict is *minor* at 25 to 999 battle-related deaths in a year and a *war* at 1,000 or more. UCDP counted 65 state-based conflicts in 2025, 13 of them wars, and 8 interstate conflicts, the most since 1945.

**Battle-related deaths include civilians caught in the fighting.** Deliberate killing of civilians is the separate one-sided category. So Sudan's 2025 is 12,269 battle deaths, a war, and 62,775 civilians killed one-sidedly, almost all of them the RSF's partner force at el-Fasher. A map that shows one number for Sudan hides which of those it is showing.

**Every event carries low, best, high.** Best is the sum of deaths on side A, side B, civilians, and unknown. The spread is the honesty: DR Congo 2025 is 9,172 best but 8,305 to 29,659; Ethiopia 5,458 but 3,319 to 17,924; Sudan's one-sided 62,775 sits on a low of about 8,300.

**Identities are stable.** Every conflict has an id and an incompatibility, every government-rebel pair is a dyad, every actor has a permanent id. A foreign state that sends troops is a *secondary warring party* on that side; no other kind of help is in the current data.

## 2. The products

| Product | What | Coverage | Freshness |
|---|---|---|---|
| GED 26.1 | one row per event, with location to admin-1 and often town, low/best/high, number of sources | 1989 to 2025 | yearly, released about June |
| Candidate GED | same rows, released before full review, with a `code_status` flag; unknown actors appear as XXX plus a country code | monthly 26.0.1 to 26.0.8, quarterly 26.01.26.06 | about six weeks behind; data is pulled on the 20th of each month |
| UCDP/PRIO, dyadic, battle deaths, non-state, one-sided, actor, country-year | the yearly summaries | to 2025 | yearly |
| ESD 18.1 | external support: troops, presence, access, weapons, materiel, training, funding, intelligence, territory, with an "alleged" flag | 1975 to 2017 | not updated since |

The API serves the same data by version string and needs a token, requested by email from the maintainer, free, three to five working days, 5,000 requests a day. Everything is CC BY 4.0 with citation of the dataset papers and the version.

Of the 13,659 unique 2026 candidate events, 8,543 are "Clear", 3,317 "Check dyad", 600 "Check deaths". The one-sided event that puts Iran at 19,900 civilian deaths in January 2026 is a single row flagged "Check type of violence".

## 3. Our fifteen wars against UCDP

Our band is the past twelve months: "3" tens of thousands a year, "2" thousands, "1" about a thousand. UCDP's 2025 is the calendar year from GED 26.1; 2026 is January to August from the candidate files, all three types summed.

| Our entry | Our band | UCDP 2025 best (low to high) | 2026 Jan to Aug | UCDP's carve-up | Verdict |
|---|---|---|---|---|---|
| Ukraine | 3 | 94,778 (87,336 to 140,931) | 57,906 | one interstate war, North Korea a secondary party | agrees |
| Sudan | 3 | 75,174 (20,890 to 90,837) | 3,987 | state-based 12,269 across two dyads; one-sided 62,775 | agrees on the number, but the kind matters |
| Gaza and Lebanon | 2 | 14,771 across two conflicts | 5,420 | Israel: Palestine (a war), Israel: Southern Lebanon (minor in 2025, 4,434 in 2026) | agrees |
| Yemen | 2 | 444 plus 781 in the US/UK strikes | 2,038 | Houthis coded as the government; PLC the rebel; Saudi, UAE, Bahrain secondary | agrees for 2026 |
| Myanmar | 3 | 2,317 (2,280 to 3,322) | 1,252 | one government conflict (a war at 1,353) plus four territorial, all minor | **contradicts: UCDP says 2** |
| Eastern Congo | 2 | 9,172 (8,305 to 29,659) | 2,412 | AFC a war, Rwanda secondary on the rebel side; ADF separate | agrees |
| The Sahel | 3 | 7,715 (7,514 to 10,346) | 4,219 | seven state-based conflicts across three countries plus three one-sided actors | **contradicts: UCDP says 2** |
| Somalia | 2 | 3,872 | 2,890 | one war with six contributing states as secondary parties | agrees |
| Syria | 1 | 3,449 | 564 | half one-sided (coast, Sweida); SDF and IS conflicts with Türkiye and the US as secondaries | agrees for 2026 |
| Haiti | 2 | 2,448 | 492 | **state-based**, a war in 2025, Kenya and five others as secondary parties | agrees for 2025; 2026 pace is band 1 |
| Pakistan and Afghanistan | 2 | 3,331 plus 745 | 3,307 plus 745 | TTP a war, Balochistan rising, the Afghanistan border an interstate minor | agrees |
| The Gulf | 2 | 1,222 (Iran-Israel, a war) | 3,810 in the new conflict "Iran – Israel, United States" | events across ten countries; US tanker strikes coded as one-sided, 5 deaths | agrees |
| Ethiopia | 2 | 5,458 (3,319 to 17,924) | 2,826 | Fano a war at 3,835; OLA minor | agrees; September is after the data |
| South Sudan | 2 | 661 (621 to 825) | 613 | government vs SPLM/A-IO minor; most deaths non-state and one-sided | **contradicts: UCDP says 1** |
| Nigeria | 2 | 4,158 | 6,488 | Islamic State a war with the US, Cameroon and Niger as secondaries; 2,850 of 2026 from unidentified actors | agrees |

**Above a thousand in UCDP that we do not have.** Mexico: 7,904 in 2025 as non-state violence, low 2,720, 1,779 so far in 2026, three cartel dyads each over a thousand. Colombia: 986 in 2025 and 1,392 in 2026 to August. Tanzania: 1,009 one-sided in 2025 (408 to 2,692). Iran's January 2026 one-sided row. Burkina Faso alone would be a band-2 war.

**Ours that UCDP would not count.** The Cuba blockade and the China-Philippines incidents, with no deaths. The Ecuador strike, with nothing coded. The boat strikes: none appear through August 2026, only two tanker strikes off Oman. The Venezuela raid is coded: Government of the United States against Government of Venezuela, 81 best, 5 January 2026, an interstate minor conflict.

The widest disagreement is not with us but between the two trackers we both lean on: ACLED and UCDP differ by three to six times on Myanmar, Somalia and the Sahel.

## 4. What a sync would change

**Fields.** `band` becomes a trailing twelve-month sum of best with low and high carried. `parties` get UCDP actor ids (United States 3, Russia 57, Ukraine 61, Sudan 112, Iran 114, Israel 121, Houthis 123, Hamas 209, Islamic State 234, TTP 356, Hezbollah 366, TPLF 410, al-Shabaab 717, SPLM/A-IO 4226, PLC 6254, SDF 6288, JNIM 6716, BRAS 7542, OLA 7595, NUG 8060, Fano 8118, RSF 8635, FLA 8822, AFC 8885, Viv Ansanm 9067, SFA 9645). `areas` map to `adm_1`, with a crosswalk from UCDP's spellings ("North Darfur state") to Natural Earth's. Our `troops` ties map to secondary warring parties today; our other kinds map onto the ESD vocabulary, but that vocabulary stops in 2017.

**What UCDP does not have and we keep.** Evidence tiers and stances on every tie. Non-troop support for 2024 to 2026: arms, drones, money, intelligence, bases, cover. The force-short-of-war class. Monthly turns and a trailing window instead of calendar years. The disagreement note.

**What changes if we adopt their numbers.** Myanmar 3 to 2. The Sahel 3 to 2. South Sudan 2 to 1. Haiti's 2026 pace to 1. Mexico and probably Colombia come in. Sudan gets two numbers, battle and one-sided.

**Mechanics.** Monthly, after the 20th: pull the new candidate file or the same version through the API, drop duplicate ids, keep `code_status`, join conflict ids to a hand-kept map of UCDP conflicts to our entries (one to many: the Sahel is seven conflicts and three one-sided actors), sum best, low and high per entry and per province, splice GED 26.1 for the months before January, and state the window on the page: "GED 26.1 plus Candidate 26.0.8, to 31 August 2026". A weekly sync is not possible; the feed is monthly with a six-week lag. UCDP audits the map; it cannot be the first source for last week.

## 5. Lessons

**Copy from UCDP.** Write the inclusion rule as a number per year and name the three kinds of violence apart, so Sudan's "war" says 12,000 battle deaths and 63,000 civilians killed. Carry low, best and high and derive the band. Give every party a stable id and treat troops as the formal class they are. Keep a 25-death floor so small wars have a place to live before they reach a thousand.

**Keep ours.** Tiers and stances. Current-year support of every kind. The squares. The month-by-month record. The sentence that says the counts disagree.

## Sources

- https://ucdp.uu.se/apidocs/ and https://ucdp.uu.se/downloads/
- Codebooks: GED 26.1, Candidate 1.5, UCDP/PRIO ACD 26.1, dyadic 26.1, non-state 26.1, one-sided 26.1, ESD 18.1
- Data: ged261-csv.zip; GEDEvent_v26_01_26_06.csv, GEDEvent_v26_0_7.csv, GEDEvent_v26_0_8.csv; ucdp-prio-acd-261, ucdp-brd-conf-261, ucdp-nonstate-261, ucdp-onesided-261, ucdp-actor-261, organizedviolencecy-261
- Davies, Pettersson and Öberg, "Organized violence 1989–2025", Journal of Peace Research 63(4), 2026
- Citation required: the dataset papers (Sundberg and Melander 2013 for GED; Hegre et al. 2020 for Candidate; Meier et al. 2022 for ESD) and the version number
