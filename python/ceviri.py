"""Veride Türkçe duran adların İngilizce karşılıkları (2026-09-23).

Etiketler (`album_etiket.etiket`) ve bağlamlar veritabanında Türkçe adlarıyla
saklanıyor ve öyle kalmalı: ad bir KİMLİK — bağlantılarda (`/etiketler?etiket=`)
ve sorgularda kullanılıyor. Burada yalnız GÖSTERİM çevriliyor.

Çeviri kelime kelime değil, müzisyenin kendi dilinde: "ayak yüklü davul"
"foot-loaded drums" değil "kick-heavy drums"; "kök notada bas" "root-note
bass"; "haşin vokal" "harsh vocals" (metal jargonu).
"""

from __future__ import annotations

from python.dil import t

#: Ölçüm etiketleri (python/etiket.py:OLCUM_ETIKETLERI) → (ad, açıklama)
OLCUM_EN: dict[str, tuple[str, str]] = {
    "hızlı": ("fast", "Tempo in the top fifth of your library."),
    "ağır": ("slow", "Tempo in the bottom fifth of your library."),
    "geniş dinamik": ("wide dynamics", "A big gap between loud and quiet moments. Measured on the drum stem, which carries the mix's dynamics best."),
    "sıkıştırılmış": ("compressed", "Narrow dynamic range: heavy compression."),
    "ride ağırlıklı davul": ("ride-heavy drums", "Most of the drum sound comes from cymbals: ride or hi-hat running constantly."),
    "tok davul": ("punchy drums", "Cymbals used sparingly; the weight is on toms and snare."),
    "ayak yüklü davul": ("kick-heavy drums", "The kick drum sits forward in the mix."),
    "trampet önde davul": ("snare-forward drums", "The weight is on the snare: a hard-hitting backbeat."),
    "programlanmış ritim": ("programmed beat", "Hits locked to the 16th-note grid: a machine, or playing very close to one."),
    "serbest ritim": ("loose groove", "Hits drift noticeably off the grid: human swing or free time."),
    "kuru davul": ("dry drums", "Hits cut off immediately: damped heads or gated reverb."),
    "çınlayan davul": ("ringing drums", "Drums ring out long: an open room or lots of reverb."),
    "davul önde miks": ("drum-forward mix", "Drums take up the most room in the mix."),
    "gürültülü davul": ("gritty drums", "The drum layer is noise-heavy: saturation or crushed room mics."),
    "melodik bas": ("melodic bass", "The bass doesn't sit on the root; it roams across a wide range."),
    "kök notada bas": ("root-note bass", "The bass sits on the root of the chord and stays put."),
    "derin bas": ("deep bass", "Bass in a lower register than usual; possibly downtuned."),
    "yoğun bas": ("busy bass", "Many notes per beat; the bass leaves no gaps."),
    "bas ağırlıklı miks": ("bass-heavy mix", "Bass takes up the most room in the mix."),
    "distorsiyonlu bas": ("distorted bass", "The bass layer is noisy: overdrive or fuzz."),
    "tırmalayan bas": ("biting bass", "The bass's centre of gravity is in the treble: finger or pick attack up front."),
    "distorsiyonlu gitar": ("distorted guitar", "The guitar/keys layer is noisy: distortion or saturation."),
    "temiz ton": ("clean tone", "The melodic layer is tonal and clean."),
    "parlak tını": ("bright timbre", "The guitar/keys layer's centre of gravity is in the treble."),
    "tok tını": ("warm timbre", "The guitar/keys layer's centre of gravity is in the low end."),
    "uzayan": ("sustained", "Notes ring on; atmospheric."),
    "kesik": ("staccato", "Short, clipped notes."),
    "geniş gezinen gitar": ("wide-ranging guitar", "Guitar/keys travel across a wide range: solo or arpeggio heavy."),
    "nota yoğun gitar": ("note-dense guitar", "Many notes per beat: riff- or passage-heavy."),
    "gitar duvarı": ("wall of guitars", "Guitar/keys take up the most room in the mix."),
    "vibratolu gitar": ("vibrato guitar", "Pitch keeps wavering: vibrato, bends or a whammy bar."),
    "geniş vokal": ("wide-range vocals", "The voice travels across a wide range."),
    "düz söyleyiş": ("flat delivery", "The voice stays in a narrow range, close to speech."),
    "tiz vokal": ("high vocals", "High register."),
    "kalın vokal": ("low vocals", "Low register."),
    "vibratolu vokal": ("vibrato vocals", "Pitch keeps wavering: pronounced vibrato."),
    "hızlı söyleyiş": ("rapid-fire delivery", "Many syllables per beat: rap or dense phrasing."),
    "vokal önde miks": ("vocal-forward mix", "Vocals take up the most room in the mix."),
    "vokal geride miks": ("buried vocals", "Vocals sit inside the mix; the instruments lead."),
    "haşin vokal": ("harsh vocals", "The vocal layer is noise-heavy: screams, growls or hard saturation."),
}

#: Bağlam etiketleri (python/etiket.py:BAGLAM_SOZLUGU)
BAGLAM_EN: dict[str, str] = {
    "sakin": "calm", "enerjik": "energetic", "melankolik": "melancholic",
    "romantik": "romantic", "karanlık": "dark", "epik": "epic", "parti": "party",
    "meditatif": "meditative", "neşeli": "upbeat", "sabah": "morning",
    "akşam": "late night", "odaklanma": "focus", "sürüş": "driving",
    "yaz": "summer", "nostaljik": "nostalgic", "enstrümantal": "instrumental",
}

#: Enstrüman rolleri (credits.role, python/muzisyen.py)
ROL_ADI: dict[str, tuple[str, str]] = {
    "drums": ("davul", "drums"), "percussion": ("perküsyon", "percussion"),
    "bass": ("bas", "bass"), "guitar": ("gitar", "guitar"),
    "keyboards": ("klavye", "keys"), "piano": ("piyano", "piano"),
    "organ": ("org", "organ"), "synthesizer": ("synthesizer", "synth"),
    "saxophone": ("saksafon", "sax"), "vocals": ("vokal", "vocals"),
    "backing_vocals": ("arka vokal", "backing vocals"),
    "flute": ("flüt", "flute"), "trumpet": ("trompet", "trumpet"),
    "violin": ("keman", "violin"), "cello": ("çello", "cello"),
    "trombone": ("trombon", "trombone"), "clarinet": ("klarnet", "clarinet"),
    "harmonica": ("mızıka", "harmonica"), "songwriter": ("söz-müzik", "songwriter"),
    "composer": ("besteci", "composer"), "producer": ("prodüktör", "producer"),
    "engineer": ("ses mühendisi", "engineer"), "lyricist": ("söz yazarı", "lyricist"),
    "arranger": ("düzenleyici", "arranger"), "mixing": ("miks", "mixing"),
    "conductor": ("şef", "conductor"), "strings": ("yaylılar", "strings"),
    "turntables": ("pikap", "turntables"), "programming": ("programlama", "programming"),
}


def etiket_adi(etiket: str) -> str:
    """Ölçüm ya da bağlam etiketinin etkin dildeki adı."""
    if etiket in OLCUM_EN:
        return t(etiket, OLCUM_EN[etiket][0])
    if etiket in BAGLAM_EN:
        return t(etiket, BAGLAM_EN[etiket])
    return etiket


def etiket_aciklama(etiket: str, turkce: str = "") -> str:
    en = OLCUM_EN.get(etiket, (None, None))[1]
    return t(turkce or etiket, en or turkce or etiket)


def rol_adi(rol: str) -> str:
    tr, en = ROL_ADI.get(rol, (rol, rol))
    return t(tr, en)


#: Ölçüm sütunlarının kullanıcıya görünen adı. Sütun adı bir KİMLİK
#: (`tekme_payi`); ekranda «Tekme Payı» gibi okunur bir ad görünür.
OLCUT_ADI: dict[str, tuple[str, str]] = {
    "dinamik_db": ("Dinamik Aralık", "Dynamic Range"),
    "enerji_payi": ("Mikste Ağırlık", "Weight in the Mix"),
    "harmonik_pay": ("Ton Temizliği", "Tonal Clarity"),
    "izgara_entropi": ("Ritim İnsanlığı", "Human Feel"),
    "nota_vurus": ("Nota Yoğunluğu", "Note Density"),
    "parlaklik": ("Parlaklık", "Brightness"),
    "perde_araligi": ("Perde Aralığı", "Pitch Range"),
    "perde_medyan": ("Ses Yüksekliği", "Register"),
    "sustain_orani": ("Nota Uzunluğu", "Note Length"),
    "tekme_payi": ("Tekme Payı", "Kick Share"),
    "tempo": ("Tempo", "Tempo"),
    "trampet_payi": ("Trampet Payı", "Snare Share"),
    "vibrato_hizi": ("Vibrato Hızı", "Vibrato Speed"),
    "zcr": ("Pürüz", "Grit"),
    "zil_payi": ("Zil Payı", "Cymbal Share"),
}


def olcut_adi(sutun: str) -> str:
    """`tekme_payi` → «Tekme Payı». Bilinmeyen sütun da ham görünmez."""
    tr, en = OLCUT_ADI.get(sutun, (None, None))
    if tr is None:
        tr = en = sutun.replace("_", " ").title()
    return t(tr, en)


def roller_adi(roller: str) -> str:
    """"percussion, drums" → «perküsyon, davul»."""
    return ", ".join(rol_adi(r.strip()) for r in str(roller or "").split(",") if r.strip())
