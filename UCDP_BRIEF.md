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

## 6. Red team: is our data trustworthy, and why would we be better

Written 2026-10-11 against the data file as it stood that day (112 ties) and the UCDP codebooks.

**What UCDP's trust rests on.** Full-time long-term coders. A two-pass method: global wires and BBC Monitoring, then local sources. Weekly resolution meetings. Automated tests before release. A persistent event id across versions, so revisions can be traced. Low, best and high on every event, with a source reference and a count of sources, and precision codes for place and date. Peer-reviewed dataset papers. University funding and no belligerent among funders. Thirty years as the field's reference. Where it is weak: it is media-dependent and says so; best is conservative by design, so closed theatres undercount (Myanmar 2,317 against ACLED's 15,000); Sudan's one-sided best of 62,775 sits on a low of 8,300; candidate data is six weeks behind and 37 percent flagged; the government is whoever holds the capital; and it has coded no support but troops since 2017.

**Where a reader should not trust us today.**

1. The checked date is the entry date. Every tie says 2026-10-11 because that is the day the rows were drafted. Nothing has been re-checked. The field should be called `entered` until a person reopens a source and confirms it, and the fade rule should wait for that.
2. "On the record" is used as a verdict on at least eight ties where the backer says something else about what it is doing: Kenya and the RSF, India and the Afghan Taliban, China and Pakistan, the U.S. air strikes and Yemen's government, Qatar and Hamas, Mexico and Cuba. The help may be on the record; the framing "backs that side" is ours.
3. The ladder does not ask whether the finding comes from a party to the fight. Five ties rest on U.S. Treasury or State findings, three of them in wars where the United States is a belligerent. By our own fourth tier, that is a side saying so.
4. Sixteen ties link Wikipedia, eleven of them on the record. All are in the newest entries, drafted when the search budget was gone. Four "documented" ties do not link the document they name. Forty-seven source texts name a primary document and link something else.
5. Twenty-four ties draw a 2025 to 2026 line on evidence with no date after 2024. One says so in its own note: "The evidence is from 2021 and 2022. No fresh proof for 2026."
6. The Sahel band says tens of thousands; its own source sentence says just under ten thousand. Myanmar's band rests on ACLED's count alone. The band note says bands come from trackers and the UN, but Ukraine's, the Gulf's and Yemen's come from the parties.
7. The windows are mixed: calendar 2025, April to March, one quarter, and soon UCDP's to August.
8. Sixty-eight ties name two or more sources in text; each has one link and no date.
9. There is no attribution for ACLED or UCDP anywhere on the page. Both require it.
10. A tie is one editor's reading of one link, entered by a research agent in one day, with no second reader and no corrections log. That is a draft of a dataset.

**The claim that survives.** None of "more accurate," "more complete," "verified," "independent" or "definitive." What is true: faster, narrower, about help rather than deaths, with the evidence shown on every line, and auditable against UCDP where UCDP has anything to audit. The sentence the page can carry: "UCDP counts the dead; this map draws who helps whom. The death bands are rounded from UCDP, ACLED and UN counts, and where they disagree the page says so. The ties are ours: each one names its evidence and how far the backer owns it, because no public dataset has tracked arms, money, bases or intelligence since 2017."

**Six weeks.**

Week 1: fix the Sahel band or its sentence and settle Myanmar against both counts; add the attribution block; rename `checked` to `entered`; make the band note say which counts are parties' counts; drop the placeholder Philippines tie; publish the fifteen-row comparison table on the page; name the editor and say a research agent drafts and a person enters.

Weeks 2 and 3: sources become a list with class, publisher, title, date, link and quote; add `evidence_to` and a precision for `since`, and fade or end the twenty-four undated ties; replace the sixteen Wikipedia links with the statements they paraphrase and point the four documented ties at their documents; write the rule for findings by belligerents and re-tier the five; add `disputed_by` beside the tier word and framing notes on the inferred open ties; start a corrections log the reader can see.

Weeks 4 to 6: two sources of different class for every non-open tie, or the tier drops a step, with the count published; UCDP conflict and dyad ids per entry with low, best and high for the window, the version string, the flagged share, and a monthly pull after the 20th shown with its own stamp; the two-numbers sentence wherever counts differ by more than two times; a second reader re-tiers every tie blind, with the disagreement rate published; a map methodology section with the standard form for a tie and how to report an error.
