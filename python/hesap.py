"""Hesap ve oturum — üyelik, giriş, çerez jetonu.

TASARIM KARARLARI VE GEREKÇELERİ

**Parola özeti `scrypt`, standart kütüphaneden.** Yeni bağımlılık yok (K2) ve
`hashlib.scrypt` bellek-zor bir türetme işlevi; düz SHA-256 ya da tek turlu
özet sözlük saldırısına açık olurdu. Tuz kullanıcı başına rastgele, parametreler
satır içinde saklanıyor ki ileride artırılabilsin ve eski kayıtlar okunmaya
devam etsin.

**Karşılaştırma sabit zamanlı** (`hmac.compare_digest`). `==` ile karşılaştırmak
yanıt süresinden bilgi sızdırır.

**Oturum jetonu `secrets`ten**, veritabanında düz saklanıyor. Düz saklamanın
gerekçesi kapsam: bu uygulama tek makinede, beş kişilik, yerel ağda çalışıyor;
veritabanına erişebilen zaten kullanıcıların kütüphanesine de erişebiliyor.
Kapsam genişlerse jeton da özetlenmeli — o zaman geldiğinde burası değişir.

**Parola ZORUNLU DEĞİL.** Spotify ile bağlanan kullanıcının parolası olmaz;
`parola_ozeti` NULL kalır ve o hesaba yalnız Spotify'la girilebilir. Tersi de
geçerli: e-posta ile açılan hesap sonradan Spotify'a bağlanabilir.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3
from datetime import datetime, timezone

#: scrypt parametreleri. n bellek maliyetini belirler; 2**14 masaüstünde
#: ~16 MB ve giriş başına birkaç yüz milisaniye — kullanıcıya görünmez,
#: kaba kuvvete pahalı.
_SCRYPT = {"n": 2 ** 14, "r": 8, "p": 1, "dklen": 32}

#: Oturum çerezinin adı ve ömrü (gün). Beş kişilik yerel bir uygulamada
#: kullanıcıyı sürekli giriş yapmaya zorlamak anlamsız.
CEREZ_ADI = "kesif_oturum"
OTURUM_GUN = 30


def _simdi() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --------------------------------------------------------------------------- #
# Parola
# --------------------------------------------------------------------------- #

def parola_ozetle(parola: str) -> str:
    """`scrypt$tuz$ozet` — parametreler kayıtla birlikte saklanır."""
    tuz = secrets.token_bytes(16)
    ozet = hashlib.scrypt(parola.encode("utf-8"), salt=tuz, **_SCRYPT)
    return f"scrypt${tuz.hex()}${ozet.hex()}"


def parola_tutuyor_mu(parola: str, saklanan: str | None) -> bool:
    """Sabit zamanlı doğrulama. Biçim tanınmazsa False — istisna değil.

    Hesabın parolası yoksa (Spotify ile açılmış) `saklanan` None'dır ve
    doğrulama BAŞARISIZ olmalı; aksi hâlde boş parolayla girilebilirdi.
    """
    if not saklanan:
        return False
    try:
        yontem, tuz_hex, ozet_hex = saklanan.split("$")
    except ValueError:
        return False
    if yontem != "scrypt":
        return False
    hesaplanan = hashlib.scrypt(
        parola.encode("utf-8"), salt=bytes.fromhex(tuz_hex), **_SCRYPT)
    return hmac.compare_digest(hesaplanan.hex(), ozet_hex)


# --------------------------------------------------------------------------- #
# Kullanıcı
# --------------------------------------------------------------------------- #

def kullanici_olustur(
    conn: sqlite3.Connection, ad: str, *, eposta: str | None = None,
    parola: str | None = None, spotify_id: str | None = None,
    spotify_yenile: str | None = None,
) -> int:
    """Yeni hesap; kullanici_id döner. E-posta ve spotify_id tekildir."""
    with conn:
        imlec = conn.execute(
            "INSERT INTO kullanici (ad, eposta, parola_ozeti, spotify_id, "
            "spotify_yenile, olusturma) VALUES (?,?,?,?,?,?)",
            (ad, eposta, parola_ozetle(parola) if parola else None,
             spotify_id, spotify_yenile, _simdi()),
        )
    return int(imlec.lastrowid)


def kullanici_bul(
    conn: sqlite3.Connection, *, kullanici_id: int | None = None,
    eposta: str | None = None, spotify_id: str | None = None,
) -> sqlite3.Row | None:
    if kullanici_id is not None:
        alan, deger = "kullanici_id", kullanici_id
    elif eposta:
        alan, deger = "eposta", eposta.strip().lower()
    elif spotify_id:
        alan, deger = "spotify_id", spotify_id
    else:
        return None
    return conn.execute(
        f"SELECT * FROM kullanici WHERE {alan} = ?", (deger,)).fetchone()


def spotify_bagla(
    conn: sqlite3.Connection, kullanici_id: int, spotify_id: str,
    yenile_jetonu: str | None,
) -> None:
    """Var olan hesaba Spotify kimliğini bağla."""
    with conn:
        conn.execute(
            "UPDATE kullanici SET spotify_id = ?, spotify_yenile = COALESCE(?, "
            "spotify_yenile) WHERE kullanici_id = ?",
            (spotify_id, yenile_jetonu, kullanici_id))


def giris_dogrula(
    conn: sqlite3.Connection, eposta: str, parola: str
) -> int | None:
    """E-posta + parola. Başarısızsa None — SEBEBİ SÖYLENMEZ.

    "Böyle bir kullanıcı yok" ile "parola yanlış" ayrımı, saldırgana hangi
    e-postaların kayıtlı olduğunu söyler. Tek mesaj döner.
    """
    kayit = kullanici_bul(conn, eposta=eposta)
    if kayit is None:
        # Kullanıcı yoksa da özet hesapla: yanıt süresi farkı, e-postanın
        # kayıtlı olup olmadığını ele verir.
        parola_tutuyor_mu(parola, parola_ozetle("kukla"))
        return None
    if not parola_tutuyor_mu(parola, kayit["parola_ozeti"]):
        return None
    return int(kayit["kullanici_id"])


# --------------------------------------------------------------------------- #
# Oturum
# --------------------------------------------------------------------------- #

def oturum_ac(conn: sqlite3.Connection, kullanici_id: int) -> str:
    jeton = secrets.token_urlsafe(32)
    simdi = _simdi()
    with conn:
        conn.execute(
            "INSERT INTO oturum (jeton, kullanici_id, olusturma, son_gorulme) "
            "VALUES (?,?,?,?)", (jeton, kullanici_id, simdi, simdi))
        conn.execute("UPDATE kullanici SET son_giris = ? WHERE kullanici_id = ?",
                     (simdi, kullanici_id))
    return jeton


def oturum_coz(conn: sqlite3.Connection, jeton: str | None) -> int | None:
    """Jetondan kullanici_id. Süresi dolmuşsa silinir ve None döner."""
    if not jeton:
        return None
    kayit = conn.execute(
        "SELECT kullanici_id, son_gorulme FROM oturum WHERE jeton = ?",
        (jeton,)).fetchone()
    if kayit is None:
        return None
    try:
        gorulme = datetime.fromisoformat(kayit["son_gorulme"])
    except ValueError:
        gorulme = datetime.now(timezone.utc)
    if (datetime.now(timezone.utc) - gorulme).days > OTURUM_GUN:
        oturum_kapat(conn, jeton)
        return None
    with conn:
        conn.execute("UPDATE oturum SET son_gorulme = ? WHERE jeton = ?",
                     (_simdi(), jeton))
    return int(kayit["kullanici_id"])


def oturum_kapat(conn: sqlite3.Connection, jeton: str | None) -> None:
    if jeton:
        with conn:
            conn.execute("DELETE FROM oturum WHERE jeton = ?", (jeton,))


def kullanici_sayisi(conn: sqlite3.Connection) -> int:
    return int(conn.execute("SELECT COUNT(*) FROM kullanici").fetchone()[0])


# --------------------------------------------------------------------------- #
# Komut satırı — hesap yönetimi
# --------------------------------------------------------------------------- #

def main(argv: list[str] | None = None) -> int:
    """Hesap işleri. Parola ARGÜMAN OLARAK ALINMAZ.

    Komut satırı argümanı `ps` çıktısında ve kabuk geçmişinde görünür; parola
    `getpass` ile, ekrana basılmadan okunuyor.
    """
    import argparse
    import getpass

    from python.db import baglan_ortak

    a = argparse.ArgumentParser(description="Hesap yönetimi")
    alt = a.add_subparsers(dest="komut", required=True)

    listele = alt.add_parser("listele", help="hesapları göster")
    listele.set_defaults(fn="listele")

    parola = alt.add_parser("parola", help="parola belirle/değiştir")
    parola.add_argument("--eposta", help="hedef hesap (e-postası)")
    parola.add_argument("--id", type=int, help="hedef hesap (kullanici_id)")
    parola.set_defaults(fn="parola")

    eposta_k = alt.add_parser("eposta", help="hesabın e-postasını belirle/değiştir")
    eposta_k.add_argument("--id", type=int, required=True)
    eposta_k.add_argument("adres")
    eposta_k.set_defaults(fn="eposta")

    sil = alt.add_parser("sil", help="hesabı ve verisini sil")
    sil.add_argument("--id", type=int, required=True)
    sil.set_defaults(fn="sil")

    args = a.parse_args(argv)
    conn = baglan_ortak()
    try:
        if args.fn == "listele":
            satirlar = conn.execute(
                "SELECT kullanici_id, ad, eposta, spotify_id, parola_ozeti IS NOT NULL "
                "AS parolali, son_giris FROM kullanici ORDER BY kullanici_id"
            ).fetchall()
            print(f"{'id':>3}  {'ad':<16}{'e-posta':<26}{'parola':<8}"
                  f"{'spotify':<9}son giriş")
            print("-" * 74)
            for r in satirlar:
                print(f"{r['kullanici_id']:>3}  {r['ad'][:15]:<16}"
                      f"{(r['eposta'] or '—')[:25]:<26}"
                      f"{'var' if r['parolali'] else 'YOK':<8}"
                      f"{'bağlı' if r['spotify_id'] else '—':<9}"
                      f"{r['son_giris'] or '—'}")
            print(f"\n{len(satirlar)}/5 hesap kullanılıyor")
            return 0

        if args.fn == "parola":
            if args.id is not None:
                kayit = kullanici_bul(conn, kullanici_id=args.id)
            elif args.eposta:
                kayit = kullanici_bul(conn, eposta=args.eposta)
            else:
                print("--id ya da --eposta gerekli"); return 1
            if kayit is None:
                print("hesap bulunamadı"); return 1

            yeni = getpass.getpass(f"{kayit['ad']} için yeni parola: ")
            if len(yeni) < 8:
                print("en az 8 karakter"); return 1
            if yeni != getpass.getpass("tekrar: "):
                print("parolalar tutmadı"); return 1
            with conn:
                conn.execute(
                    "UPDATE kullanici SET parola_ozeti = ? WHERE kullanici_id = ?",
                    (parola_ozetle(yeni), kayit["kullanici_id"]))
            print(f"parola belirlendi: {kayit['ad']}")
            return 0

        if args.fn == "eposta":
            kayit = kullanici_bul(conn, kullanici_id=args.id)
            if kayit is None:
                print("hesap bulunamadı"); return 1
            adres = args.adres.strip().lower()
            if "@" not in adres or "." not in adres.split("@")[-1]:
                print("geçerli bir e-posta adresi değil"); return 1
            # Tekillik kısıtı var; çakışmada anlaşılır mesaj ver.
            baskasi = kullanici_bul(conn, eposta=adres)
            if baskasi is not None and baskasi["kullanici_id"] != args.id:
                print(f"bu e-posta zaten {baskasi['ad']} hesabında kayıtlı")
                return 1
            with conn:
                conn.execute(
                    "UPDATE kullanici SET eposta = ? WHERE kullanici_id = ?",
                    (adres, args.id))
            print(f"e-posta belirlendi: {kayit['ad']} → {adres}")
            if not kayit["parola_ozeti"]:
                print("NOT: bu hesabın parolası yok. "
                      f"`python -m python.hesap parola --id {args.id}`")
            return 0

        if args.fn == "sil":
            from python.db import kullanici_db
            kayit = kullanici_bul(conn, kullanici_id=args.id)
            if kayit is None:
                print("hesap bulunamadı"); return 1
            with conn:
                conn.execute("DELETE FROM oturum WHERE kullanici_id = ?", (args.id,))
                conn.execute("DELETE FROM kullanici WHERE kullanici_id = ?", (args.id,))
            # Kütüphane dosyası da gider; paylaşımlı veriye dokunulmaz.
            yol = kullanici_db(args.id)
            for ek in ("", "-wal", "-shm"):
                dosya = type(yol)(str(yol) + ek)
                if dosya.exists():
                    dosya.unlink()
            print(f"silindi: {kayit['ad']} (kütüphane dosyası dahil)")
            return 0
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
