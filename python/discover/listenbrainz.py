"""ListenBrainz: kalabalığın bilgisi — "bunu dinleyen şunu da dinliyor".

Reddit API başvurusu reddedildiği için (K10) söylem katmanının yerini bu alıyor.
Forum metni değil ama aynı işlevi görüyor: insanların dinleme davranışından çıkan
sanatçı yakınlığı. Kredi grafiğinin ve etiketlerin göremediği bağları taşır —
"Rush dinleyenler Led Zeppelin de dinliyor" bilgisi ne kredide ne etikette var.

Anahtarsız ve onaysız (test edildi 2026-08-11): labs uç noktası açık.
`api.listenbrainz.org` tarafındaki bazı uç noktalar token istiyor, onları
kullanmıyoruz.

Kullanım:
    python -m python.discover.listenbrainz --sanatci "Rush"
    python -m python.discover.listenbrainz --kutuphane --limit 40
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

from python.db import VARSAYILAN_DB, baglan
from python.metin import normalize_esleme
from python.onbellek import AgYok, ApiIstemci, musicbrainz

#: ListenBrainz'in yayımladığı hazır benzerlik veri kümesi. Ad uzun ama bir
#: parametre demeti: oturum tabanlı, 7500 günlük pencere, 300 sn oturum aralığı.
VARSAYILAN_ALGORITMA = (
    "session_based_days_7500_session_300_contribution_5_threshold_10_"
    "limit_100_filter_True_skip_30"
)


def listenbrainz(**kwargs) -> ApiIstemci:
    return ApiIstemci(
        servis="listenbrainz",
        temel_url="https://labs.api.listenbrainz.org",
        istek_araligi=0.6,
        basliklar={"User-Agent": "muzik-kesif-motoru/0.1 (kisisel arastirma)"},
        **kwargs,
    )


@dataclass(frozen=True)
class BenzerSanatci:
    mbid: str
    ad: str
    skor: int


def benzerleri_coz(govde) -> list[BenzerSanatci]:
    if not isinstance(govde, list):
        return []
    sonuc = []
    for kayit in govde:
        if not isinstance(kayit, dict):
            continue
        mbid = kayit.get("artist_mbid") or kayit.get("mbid") or ""
        ad = kayit.get("name") or kayit.get("artist_name") or ""
        skor = kayit.get("score")
        if ad and isinstance(skor, (int, float)):
            sonuc.append(BenzerSanatci(mbid, ad, int(skor)))
    return sorted(sonuc, key=lambda b: -b.skor)


def sanatci_mbid_bul(mb: ApiIstemci, ad: str) -> str | None:
    """Sanatçı adından MusicBrainz kimliği.

    ASIL AD yetmiyor: MusicBrainz Masayoshi Takanaka'yı "高中正義" olarak
    tutuyor, romanize hâli TAKMA AD listesinde. Yalnızca `name` alanına bakan
    eşleştirici onu bulamıyordu ve sonuç şuydu — kullanıcının zaten sahip olduğu
    sanatçı "keşif" diye önerildi (ölçüldü: bir eksende ilk 5 adayın 4'ü).
    Bu yüzden ad, sıralama adı (`sort-name`, "Takanaka, Masayoshi") ve bütün
    takma adlar birlikte denenir.

    Eşik gevşetilmiyor: yanlış sanatçı yanlış komşuluk demek, öneri motorunu
    doğrudan zehirler. Yalnızca aynı varlığın FARKLI YAZIMLARI kabul ediliyor.
    """
    hedef = normalize_esleme(ad)
    if not hedef:
        return None
    govde = mb.get_json(
        "artist", {"query": ad, "fmt": "json", "limit": 5, "inc": "aliases"}
    )
    for aday in (govde or {}).get("artists", []):
        adaylar = [aday.get("name", ""), aday.get("sort-name", "")]
        adaylar += [t.get("name", "") for t in (aday.get("aliases") or [])]
        for varyant in adaylar:
            n = normalize_esleme(varyant)
            if not n:
                continue
            # "Takanaka, Masayoshi" ↔ "Masayoshi Takanaka": sözcük kümesi aynı.
            if n == hedef or sorted(n.split()) == sorted(hedef.split()):
                return aday.get("id")
    return None


def benzer_sanatcilar(
    lb: ApiIstemci, artist_mbid: str, algoritma: str = VARSAYILAN_ALGORITMA
) -> list[BenzerSanatci]:
    govde = lb.get_json(
        "similar-artists/json", {"artist_mbids": artist_mbid, "algorithm": algoritma}
    )
    return benzerleri_coz(govde)


def kutuphane_komsulari(
    conn: sqlite3.Connection, *, limit: int | None = None, adet: int = 20
) -> tuple[list[dict], dict[str, int]]:
    """Kütüphanedeki sanatçıların komşularını topla.

    Kütüphanede ZATEN olan sanatçılar elenir — amaç keşif, teyit değil.
    """
    sorgu = """
        SELECT artist, COUNT(*) AS albüm
          FROM albums GROUP BY artist ORDER BY albüm DESC, artist
    """
    if limit:
        sorgu += f" LIMIT {int(limit)}"
    sanatcilar = [(s["artist"], s["albüm"]) for s in conn.execute(sorgu)]
    sahip_olunan = {normalize_esleme(a) for a, _ in sanatcilar}

    mb, lb = musicbrainz(), listenbrainz()
    sayac = {"sanatci": 0, "mbid_yok": 0, "komsu": 0}
    toplanan: dict[str, dict] = {}

    for sira, (ad, albüm) in enumerate(sanatcilar, 1):
        sayac["sanatci"] += 1
        try:
            mbid = sanatci_mbid_bul(mb, ad)
            if not mbid:
                sayac["mbid_yok"] += 1
                continue
            komsular = benzer_sanatcilar(lb, mbid)[:adet]
        except AgYok:
            continue

        # Kaynak sanatçının kendi listesi içinde normalize et. Ham skorlar
        # popülerlikle ölçekleniyor: Metallica'nın komşuluk skorları Casiopea'nın
        # skorlarının kat kat üstünde, dolayısıyla ham toplamda hep tanınmış
        # isimler kazanıyordu. Pay olarak bakınca soru "bu isim O SANATÇI için
        # ne kadar merkezî" olur ve ölçek sorunu kalkar.
        en_buyuk = max((k.skor for k in komsular), default=0) or 1
        for komsu in komsular:
            anahtar = normalize_esleme(komsu.ad)
            if not anahtar or anahtar in sahip_olunan:
                continue  # zaten kütüphanede
            kayit = toplanan.setdefault(
                anahtar,
                {"ad": komsu.ad, "mbid": komsu.mbid, "skor": 0.0,
                 "en_yuksek": 0.0, "kaynaklar": []},
            )
            pay = komsu.skor / en_buyuk          # 0–1, kaynak içinde
            # Kütüphanedeki albüm sayısıyla ağırlıklandır: 13 Rush albümü olan
            # birinin Rush komşuluğu, tek albümü olan sanatçınınkinden ağır basar.
            kayit["skor"] += pay * albüm
            kayit["en_yuksek"] = max(kayit["en_yuksek"], pay)
            kayit["kaynaklar"].append(ad)
            sayac["komsu"] += 1

        if sira % 10 == 0 or sira == len(sanatcilar):
            print(f"  {sira}/{len(sanatcilar)} sanatçı", file=sys.stderr)

    # Ham toplam popülerliği ödüllendiriyor: The Beatles, Queen, AC/DC herkesin
    # komşusu çıkıyor ve 302 albümlük bir prog/metal kütüphanesine bunları
    # önermek keşif değil. TF-IDF mantığı: kütüphanedeki HER sanatçının komşusu
    # olan bir isim, hiçbir şeyi ayırt etmiyor demektir.
    import math

    n = max(1, sayac["sanatci"])
    for kayit in toplanan.values():
        kac_kaynak = len(set(kayit["kaynaklar"]))
        kayit["kaynak_sayisi"] = kac_kaynak
        # log(N/df): tek bir sanatçıdan gelen komşu ağır basar, herkesten gelen hafifler.
        kayit["ozgul_skor"] = round(kayit["skor"] * math.log(1 + n / kac_kaynak), 2)
        kayit["kaynaklar"] = ", ".join(sorted(set(kayit["kaynaklar"]))[:5])

    siralanmis = sorted(toplanan.values(), key=lambda k: -k["ozgul_skor"])
    return siralanmis, sayac


def main(argv: list[str] | None = None) -> int:
    ayristirici = argparse.ArgumentParser(description="ListenBrainz komşuluk sinyali.")
    ayristirici.add_argument("--db", type=Path, default=VARSAYILAN_DB)
    ayristirici.add_argument("--sanatci", help="tek bir sanatçının komşuları")
    ayristirici.add_argument("--kutuphane", action="store_true", help="tüm kütüphane")
    ayristirici.add_argument("--limit", type=int, help="en fazla kaç sanatçı")
    ayristirici.add_argument("--cevrimdisi", action="store_true")
    args = ayristirici.parse_args(argv)

    if args.sanatci:
        mb = musicbrainz(cevrimdisi=args.cevrimdisi)
        lb = listenbrainz(cevrimdisi=args.cevrimdisi)
        mbid = sanatci_mbid_bul(mb, args.sanatci)
        if not mbid:
            print(f"MusicBrainz'de bulunamadı: {args.sanatci}", file=sys.stderr)
            return 1
        for komsu in benzer_sanatcilar(lb, mbid)[:20]:
            print(f"  {komsu.skor:>6}  {komsu.ad}")
        return 0

    if not args.kutuphane:
        ayristirici.error("--sanatci ya da --kutuphane verilmeli")

    conn = baglan(args.db)
    try:
        komsular, sayac = kutuphane_komsulari(conn, limit=args.limit)
    finally:
        conn.close()

    print(f"\nTaranan sanatçı: {sayac['sanatci']} (MBID bulunamayan: {sayac['mbid_yok']})")
    print(f"Kütüphanede OLMAYAN komşu sanatçı: {len(komsular)}\n")
    print(f"{'özgül':>10} {'toplam':>10} {'kaynak':>7}  {'sanatçı':<30} kimlerden geldi")
    for kayit in komsular[:30]:
        print(
            f"{kayit['ozgul_skor']:>10.2f} {kayit['skor']:>10.2f} "
            f"{kayit['kaynak_sayisi']:>7}  {kayit['ad'][:30]:<30} {kayit['kaynaklar'][:40]}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
