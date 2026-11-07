"""Komşuluk yolları: MusicBrainz kadro grafiği ve Deezer «benzer sanatçılar».

2026-11-07. İki gerekçe, ikisi de ölçümden:

1. **Kadro bağı insanların en çok güvendiği gerekçe.** Forum okumasında
   (`docs/arastirma/9-*`) en tutarlı insan önerileri kadroya dayanıyordu:
   Exivious («iki Cynic üyesi var», 7 kişi / 5 iplik), Deadsoul Tribe
   («Psychotic Waltz'taki adamın grubu»), Gentle Hearts (Casiopea basçısı).
   Projenin tezi de bu (K7: «iyi davulcu dinleyen adam bilgisi kredilerde»).
   MusicBrainz ilişkileri CC0 — kalıcı önbellek serbest; Discogs API'sinin
   saklama maddesi sorunu yok (`docs/arastirma/10-*`).
   Örnek (2026-11-07, canlı): Cynic → Sean Malone → Aghora, Gordian Knot;
   forumda ikisi de Cynic için önerilmiş.

2. **Deezer `artist/{id}/related`** kalabalığın «hayranları şunu da dinliyor»
   işareti (K10). Belgelenmiş uç, anahtarsız (3/3 denendi). Saklanan şey metin
   (ad, sıra); ses değil — Deezer'ın ses saklama yasağına girmiyor.

Hız: MusicBrainz ve ListenBrainz saniyede 1 istek (istemcide 1,05 sn), Deezer
0,35 sn. Hepsi `onbellek.ApiIstemci` üzerinden: aynı istek iki kez yapılmaz (K5).
"""

from __future__ import annotations

from collections import defaultdict

from python.metin import normalize_esleme
from python.onbellek import AgYok, ApiIstemci

#: Kadro ilişkileri ve ağırlıkları. «supporting musician» (turne/oturum
#: müzisyeni) bağı daha gevşek: aynı sahnede çalmak, aynı grubu kurmak değil.
KADRO_ILISKILERI = {"member of band": 1.0, "supporting musician": 0.5}

#: Bir grubun bu kadardan fazla üyesi taranmaz (istek bütçesi: üye başına bir
#: MusicBrainz isteği, saniyede bir). Uzun ömürlü gruplarda 30+ eski üye var.
AZAMI_UYE = 12

#: Sıra kaynaşmasının K'sı (tohumlar arası birleştirme, Cormack 2009).
RRF_K = 60


# --------------------------------------------------------------------------- #
# MusicBrainz kadro grafiği
# --------------------------------------------------------------------------- #

def _mbid(mb: ApiIstemci, ad: str) -> str | None:
    """Ad → MBID (`listenbrainz.sanatci_mbid_bul`). MusicBrainz arama servisi
    yük altında isteği geri çevirebiliyor (503, «search-shed», 2026-11-07
    görüldü): o zaman None — önbelleğe yazılmaz, sonraki çalıştırmada denenir."""
    from python.discover.listenbrainz import sanatci_mbid_bul

    try:
        return sanatci_mbid_bul(mb, ad)
    except AgYok:
        raise
    except Exception:
        return None


def _iliskiler(mb: ApiIstemci, mbid: str) -> dict | None:
    try:
        return mb.get_json(f"artist/{mbid}", {"inc": "artist-rels", "fmt": "json"})
    except AgYok:
        raise
    except Exception:
        return None


def _baglar(govde: dict, yon: str) -> list[tuple[str, str, float, list[str]]]:
    """(mbid, ad, ağırlık, enstrümanlar) — verilen yöndeki kadro ilişkileri.

    Grup açısından üyeler «backward», kişi açısından grupları «forward».
    Aynı kişi birden çok dönemle (ayrılıp dönen üye) tekrar ediyor: en güçlü
    ilişki ve enstrümanların birleşimi tutulur.
    """
    en_iyi: dict[str, tuple[str, float, set[str]]] = {}
    for r in (govde or {}).get("relations") or []:
        agirlik = KADRO_ILISKILERI.get(r.get("type"))
        if agirlik is None or r.get("direction") != yon:
            continue
        a = r.get("artist") or {}
        if not a.get("id"):
            continue
        ad, w, ens = en_iyi.get(a["id"], (a.get("name", ""), 0.0, set()))
        ens |= {x for x in (r.get("attributes") or []) if x not in ("original", "founder")}
        en_iyi[a["id"]] = (ad or a.get("name", ""), max(w, agirlik), ens)
    return [(m, ad, w, sorted(e)) for m, (ad, w, e) in en_iyi.items()]


def kadro_komsulari(mb: ApiIstemci, ad: str, *, mbid: str | None = None,
                    azami_uye: int = AZAMI_UYE) -> list[dict]:
    """Tohum sanatçının kadro komşuları, ortak kişi ağırlığına göre sıralı.

    Grup tohum: üyeleri (kişi) ve üyelerinin BAŞKA grupları. Skor, adayı tohuma
    bağlayan kişilerin ilişki ağırlıklarının toplamı — iki Cynic üyesinin
    çaldığı Exivious, bir üyenin uğradığı gruptan önde.
    Kişi tohum (Allan Holdsworth): grupları ve o gruplardaki grup arkadaşları.

    Dönen: [{"ad", "mbid", "skor", "kisiler": [(kişi, enstrümanlar)]}].
    """
    mbid = mbid or _mbid(mb, ad)
    if not mbid:
        return []
    tohum = _iliskiler(mb, mbid)
    if not tohum:
        return []
    skor: dict[str, float] = defaultdict(float)
    adlar: dict[str, str] = {}
    kisiler: dict[str, list[tuple[str, list[str]]]] = defaultdict(list)

    def ekle(aday_mbid: str, aday_ad: str, w: float, kisi: str, ens: list[str]) -> None:
        if aday_mbid == mbid or normalize_esleme(aday_ad) == normalize_esleme(ad):
            return
        skor[aday_mbid] += w
        adlar[aday_mbid] = aday_ad
        kisiler[aday_mbid].append((kisi, ens))

    if tohum.get("type") == "Person":
        for g_mbid, g_ad, w, ens in _baglar(tohum, "forward")[:azami_uye]:
            ekle(g_mbid, g_ad, w, ad, ens)
            for k_mbid, k_ad, w2, ens2 in _baglar(_iliskiler(mb, g_mbid) or {}, "backward"):
                ekle(k_mbid, k_ad, w * w2 * 0.5, g_ad, ens2)    # grup arkadaşı: 2 adım
    else:
        uyeler = sorted(_baglar(tohum, "backward"), key=lambda x: (-x[2], x[1]))[:azami_uye]
        for k_mbid, k_ad, w, ens in uyeler:
            ekle(k_mbid, k_ad, w * 0.5, k_ad, ens)               # üyenin kendisi (solo)
            for g_mbid, g_ad, w2, _ in _baglar(_iliskiler(mb, k_mbid) or {}, "forward"):
                ekle(g_mbid, g_ad, w * w2, k_ad, ens)
    sira = sorted(skor, key=lambda m: (-skor[m], adlar[m]))
    return [{"ad": adlar[m], "mbid": m, "skor": round(skor[m], 3), "kisiler": kisiler[m]}
            for m in sira]


# --------------------------------------------------------------------------- #
# Deezer «benzer sanatçılar» ve ListenBrainz kalabalığı
# --------------------------------------------------------------------------- #

def deezer_kimlik(dz: ApiIstemci, ad: str) -> int | None:
    """Ad tam (normalize) eşleşirse Deezer sanatçı kimliği. Gevşek eşleşme
    yanlış sanatçının komşuluğunu getirir; eşik gevşetilmez."""
    try:
        govde = dz.get_json("search/artist", {"q": ad, "limit": 25})
    except AgYok:
        raise
    except Exception:
        return None
    hedef = normalize_esleme(ad)
    # Aynı adlı birden çok kayıt olabiliyor («Tool» araması): en çok hayranı olan.
    eslesen = [a for a in (govde or {}).get("data") or []
               if normalize_esleme(a.get("name", "")) == hedef]
    return max(eslesen, key=lambda a: a.get("nb_fan") or 0).get("id") if eslesen else None


def deezer_benzer(dz: ApiIstemci, ad: str, *, adet: int = 50) -> list[dict]:
    """[{"ad", "sira", "fans"}] — Deezer'ın «benzer sanatçılar» listesi, sırasıyla."""
    kimlik = deezer_kimlik(dz, ad)
    if not kimlik:
        return []
    try:
        govde = dz.get_json(f"artist/{kimlik}/related", {"limit": adet})
    except AgYok:
        raise
    except Exception:
        return []
    return [{"ad": a.get("name", ""), "sira": i, "fans": a.get("nb_fan")}
            for i, a in enumerate((govde or {}).get("data") or [], 1) if a.get("name")]


def lb_benzer(mb: ApiIstemci, lb: ApiIstemci, ad: str) -> list[dict]:
    """[{"ad", "sira", "skor"}] — ListenBrainz kalabalık komşuları."""
    from python.discover.listenbrainz import benzer_sanatcilar

    mbid = _mbid(mb, ad)
    if not mbid:
        return []
    try:
        return [{"ad": b.ad, "sira": i, "skor": b.skor}
                for i, b in enumerate(benzer_sanatcilar(lb, mbid), 1)]
    except AgYok:
        raise
    except Exception:
        return []


# --------------------------------------------------------------------------- #
# Toplama ve tohumlar arası birleştirme
# --------------------------------------------------------------------------- #

#: Dış komşuluk yolları ve kanıt aileleri (`kesif.KANIT_AILESI`): kadro bağı
#: «kredi», kalabalık benzerliği «sahne» ailesi.
DIS_YOLLAR = ("deezer_benzer", "listenbrainz", "kadro")


def komsular_topla(adlar, *, dz: ApiIstemci | None = None, mb: ApiIstemci | None = None,
                   lb: ApiIstemci | None = None, yollar=DIS_YOLLAR, ilerleme=None
                   ) -> dict[str, dict[str, list[dict]]]:
    """{yol: {sanatçı anahtarı: komşu listesi}} — önbellekten ya da ağdan.

    İstemci verilmezse varsayılanlar (`data/cache`). Önbellekte olmayan ve
    çevrimdışı istemcide `AgYok` veren sanatçı boş liste alır, hata değil.
    """
    from python.discover.calma_listesi import deezer_listesi
    from python.discover.listenbrainz import listenbrainz
    from python.onbellek import musicbrainz

    dz = dz or deezer_listesi()
    mb = mb or musicbrainz()
    lb = lb or listenbrainz()
    getir = {"deezer_benzer": lambda ad: deezer_benzer(dz, ad),
             "listenbrainz": lambda ad: lb_benzer(mb, lb, ad),
             "kadro": lambda ad: kadro_komsulari(mb, ad)}
    sonuc: dict[str, dict[str, list[dict]]] = {y: {} for y in yollar}
    adlar = list(adlar)
    for i, ad in enumerate(adlar, 1):
        anahtar = normalize_esleme(ad)
        for yol in yollar:
            try:
                sonuc[yol][anahtar] = getir[yol](ad)
            except Exception:       # çevrimdışı / servis düştü: boş, hata değil
                sonuc[yol][anahtar] = []
        if ilerleme:
            ilerleme(i, len(adlar), ad, {y: len(sonuc[y][anahtar]) for y in yollar})
    return sonuc

def tohumlardan_sira(komsular: dict[str, list[dict]], *, haric: set[str] = frozenset()
                     ) -> list[str]:
    """{tohum: komşu listesi} → tek sıra (normalize anahtarlar).

    Tohumlar arası RRF: skor(a) = Σ_tohum 1/(K + sıra_tohum(a)). Birçok tohumun
    ortak komşusu öne çıkar; tek tohumun uzun listesi ekseni ele geçiremez.
    `haric`: sahip olunanlar ve tohumların kendisi.
    """
    skor: dict[str, float] = defaultdict(float)
    for liste in komsular.values():
        gorulen: set[str] = set()
        for r, k in enumerate(liste, 1):
            a = normalize_esleme(k["ad"])
            if not a or a in haric or a in gorulen:
                continue
            gorulen.add(a)
            skor[a] += 1.0 / (RRF_K + r)
    return [a for a, _ in sorted(skor.items(), key=lambda x: (-x[1], x[0]))]
