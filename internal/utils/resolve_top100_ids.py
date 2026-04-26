"""One-shot: resolve Spotify IDs for the top-100-artists list and emit a CSV-style python module."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from internal.config import Config
from internal.spotify_client import SpotifyClient


# (rank, search_name, monthly_listeners, original_label_from_source)
ARTISTS: list[tuple[int, str, int, str]] = [
    (1,  "Taylor Swift",        155_805_678, "Taylor Swift"),
    (2,  "Ed Sheeran",           126_037_203, "Ed Sheeran"),
    (3,  "Billie Eilish",        125_648_835, "Billie Eilish"),
    (4,  "Ariana Grande",        111_193_719, "Ariana Grande"),
    (5,  "Eminem",               109_132_723, "Eminem"),
    (6,  "Bruno Mars",            81_871_142, "Bruno Mars"),
    (7,  "Adele",                 69_983_016, "Adele"),
    (8,  "Coldplay",              63_627_018, "Coldplay"),
    (9,  "Imagine Dragons",       59_647_129, "Imagine Dragons"),
    (10, "Queen",                 57_051_108, "Rainha"),
    (11, "Lana Del Rey",          56_672_433, "Lana Del Rey"),
    (12, "Selena Gomez",          54_166_818, "Selena Gomez"),
    (13, "XXXTentacion",          53_669_823, "XXXTentacion"),
    (14, "Olivia Rodrigo",        52_893_342, "Olivia Rodrigo"),
    (15, "Post Malone",           48_599_561, "Post Malone"),
    (16, "Dua Lipa",              47_938_159, "Dua Lipa"),
    (17, "Maroon 5",              47_534_632, "Maroon 5"),
    (18, "Kendrick Lamar",        47_519_670, "Kendrick Lamar"),
    (19, "Lady Gaga",             46_025_666, "Lady Gaga"),
    (20, "Juice WRLD",            45_055_570, "Juice WRLD"),
    (21, "Travis Scott",          43_451_466, "Travis Scott"),
    (22, "Beyoncé",               42_588_258, "Beyoncé"),
    (23, "One Direction",         41_125_458, "One Direction"),
    (24, "Michael Jackson",       40_944_253, "Michael Jackson"),
    (25, "Katy Perry",            40_189_524, "Katy Perry"),
    (26, "Guns N' Roses",         37_126_487, "Guns N' Roses"),
    (27, "Doja Cat",              36_920_792, "Doja Cat"),
    (28, "Camila Cabello",        36_347_970, "Camila Cabello"),
    (29, "SZA",                   35_613_177, "SZA"),
    (30, "Harry Styles",          35_267_364, "Harry Styles"),
    (31, "Marshmello",            34_907_550, "Marshmello"),
    (32, "Nicki Minaj",           34_677_189, "Nicki Minaj"),
    (33, "Linkin Park",           34_179_075, "Linkin Park"),
    (34, "Metallica",             34_167_402, "Metallica"),
    (35, "Arctic Monkeys",        34_124_921, "Arctic Monkeys"),
    (36, "Kanye West",            33_034_056, "Kanye West"),
    (37, "The Beatles",           31_789_733, "Os Beatles"),
    (38, "Sabrina Carpenter",     31_751_148, "Sabrina Carpenter"),
    (39, "Chris Brown",           30_894_910, "Chris Brown"),
    (40, "Romeo Santos",          29_351_071, "Romeu Santos"),
    (41, "J. Cole",               28_223_213, "J. Cole"),
    (42, "Miley Cyrus",           27_665_374, "Miley Cyrus"),
    (43, "Demi Lovato",           27_566_308, "Demi Lovato"),
    (44, "Sam Smith",             27_076_939, "Sam Smith"),
    (45, "Cardi B",               26_870_824, "Cardi B"),
    (46, "Tyler, The Creator",    26_592_435, "Tyler, o Criador"),
    (47, "Twenty One Pilots",     26_385_698, "Twenty One Pilots"),
    (48, "Charlie Puth",          26_290_753, "Charlie Puth"),
    (49, "21 Savage",             25_420_496, "21 Savage"),
    (50, "Nirvana",               25_118_637, "Nirvana"),
    (51, "Imperial",              25_014_074, "Força Régia"),  # uncertain
    (52, "ZAYN",                  24_601_765, "ZAYN"),
    (53, "Red Hot Chili Peppers", 24_411_912, "Pimentas Chili Vermelhas"),
    (54, "Future",                24_139_663, "Futuro"),
    (55, "2Pac",                  23_963_331, "2pac"),
    (56, "Pink Floyd",            23_675_910, "Pink Floyd"),
    (57, "Calvin Harris",         23_487_378, "Calvin Harris"),
    (58, "The Neighbourhood",     23_148_299, "A Vizinhança"),
    (59, "Lil Baby",              22_981_959, "Bebêzinho"),
    (60, "Halsey",                22_947_883, "Halsey"),
    (61, "Melanie Martinez",      22_753_460, "Melanie Martinez"),
    (62, "Frank Ocean",           22_168_060, "Frank Ocean"),
    (63, "The Chainsmokers",      21_806_198, "The Chainsmokers"),
    (64, "James Arthur",          21_435_914, "James Arthur"),
    (65, "Nicky Jam",             21_342_700, "Nicky Jam"),
    (66, "50 Cent",               20_726_915, "50 Cent"),
    (67, "Lil Uzi Vert",          20_284_182, "Lil Uzi Vert"),
    (68, "OneRepublic",           19_390_615, "OneRepublic"),
    (69, "Lil Wayne",             19_162_947, "Lil Wayne"),
    (70, "Britney Spears",        19_042_146, "Britney Spears"),
    (71, "Arcángel",              18_925_934, "Arcanjo"),
    (72, "Cigarettes After Sex",  18_853_781, "Cigarros após o sexo"),
    (73, "Rosalía",               18_683_269, "Rosa"),
    (74, "A$AP Rocky",            18_419_669, "A$AP Rocky"),
    (75, "Green Day",             18_382_712, "Green Day"),
    (76, "Becky G",               17_307_595, "Becky G"),
    (77, "Khalid",                17_245_376, "Khalid"),
    (78, "Snoop Dogg",            16_932_424, "Snoop Dogg"),
    (79, "Lil Peep",              16_879_868, "Lil Peep"),
    (80, "Bon Jovi",              16_778_756, "Bon Jovi"),
    (81, "Aerosmith",             16_767_124, "Aerosmith"),
    (82, "Justin Timberlake",     16_707_748, "Justin Timberlake"),
    (83, "Led Zeppelin",          16_622_558, "Led Zeppelin"),
    (84, "YoungBoy Never Broke Again", 16_595_987, "YoungBoy Nunca Mais Quebrou"),
    (85, "Elton John",            16_363_465, "Elton John"),
    (86, "The Rolling Stones",    16_310_185, "Os Rolling Stones"),
    (87, "Fifth Harmony",         16_254_256, "Quinta Harmonia"),
    (88, "Playboi Carti",         16_148_054, "Playboi Carti"),
    (89, "Pop Smoke",             16_087_794, "Pop Smoke"),
    (90, "Dr. Dre",               16_022_324, "Dr. Dre"),
    (91, "Gorillaz",              15_869_893, "Gorillaz"),
    (92, "Radiohead",             15_816_551, "Radiohead"),
    (93, "Meghan Trainor",        15_813_544, "Meghan Trainor"),
    (94, "Morgan Wallen",         15_323_368, "Morgan Wallen"),
    (95, "System of a Down",      15_242_154, "Sistema de um Down"),
    (96, "Childish Gambino",      15_235_573, "Childish Gambino"),
    (97, "Slipknot",              15_083_276, "Slipknot"),
    (98, "Migos",                 15_068_202, "Migos"),
    (99, "Fleetwood Mac",         15_047_136, "Fleetwood Mac"),
    (100, "Porter Robinson",      14_674_909, "Porteiro"),  # uncertain
]


def main() -> None:
    config = Config.load()
    client = SpotifyClient(config.client_id, config.client_secret, config.album_types)

    out_path = PROJECT_ROOT / "internal" / "data" / "top100artists.py"
    rows: list[tuple[int, str, str, int, str]] = []
    misses: list[int] = []

    for rank, query, listeners, original in ARTISTS:
        results = client._sp.search(q=query, type="artist", limit=1)
        items = results["artists"]["items"]
        if items:
            a = items[0]
            rows.append((rank, a["name"], a["id"], listeners, original))
            flag = "" if a["name"].lower() == query.lower() else " (fuzzy)"
            print(f"  {rank:>3}. {query:30s} -> {a['name']} [{a['id']}]{flag}")
        else:
            rows.append((rank, query, "", listeners, original))
            misses.append(rank)
            print(f"  {rank:>3}. {query:30s} -> NOT FOUND")

    # Write the python module — list of dicts (CSV-equivalent rows).
    with out_path.open("w", encoding="utf-8") as f:
        f.write('"""Top 100 artists by Spotify monthly listeners.\n\n')
        f.write('Source data was fed in with several names auto-translated to Portuguese\n')
        f.write('(e.g. "Os Beatles" -> "The Beatles"); ``source_label`` keeps the raw name\n')
        f.write('we received, ``name`` is what Spotify returned for the resolved artist.\n')
        f.write('"""\n\n')
        f.write('TOP_100_ARTISTS: list[dict] = [\n')
        for rank, name, sid, listeners, original in rows:
            f.write(
                f'    {{"rank": {rank}, "name": {name!r}, '
                f'"spotify_id": {sid!r}, "monthly_listeners": {listeners}, '
                f'"source_label": {original!r}}},\n'
            )
        f.write(']\n')

    print(f"\nWrote {len(rows)} rows to {out_path}")
    if misses:
        print(f"Missed lookups for ranks: {misses}")


if __name__ == "__main__":
    main()
