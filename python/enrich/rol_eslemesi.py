"""Discogs / MusicBrainz rol varyantlarını kanonik rollere indirger.

Projenin tezi kredi grafiğinde: "iyi davulcu dinleyen adam" bilgisi burada üretilir.
Ham roller normalize edilmezse "Drums", "Drums [Additional]", "Drum Kit", "Batterie"
dört ayrı öznitelik olur, matris seyrekleşir ve aynı davulcu dört farklı kişi gibi
görünür. Bu dosya o çöküşü engelleyen yerdir.

Üç aşama:
1. Ham dize parçalanır — Discogs tek kişiye "Bass, Backing Vocals" yazar.
2. Nitelikler atılır — "[Additional]", "(uncredited)", "2", "*".
3. Kanonik role eşlenir — önce birebir sözlük, sonra sıralı anahtar kelime kuralları.

Sözlükte olmayan roller sessizce yutulmaz: `RolAyrim.bilinmeyen` ile geri döner,
`krediler.py` bunları CSV'ye raporlar ve sözlük zamanla büyür.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# --------------------------------------------------------------------------- #
# Kanonik roller
# --------------------------------------------------------------------------- #

ENSTRUMAN_ROLLERI = frozenset(
    {
        "drums", "percussion", "bass", "guitar", "keyboards", "piano", "organ",
        "synthesizer", "vocals", "backing_vocals", "saxophone", "trumpet",
        "trombone", "flute", "clarinet", "violin", "viola", "cello", "strings",
        "horns", "harmonica", "banjo", "mandolin", "harp", "accordion", "sitar",
        "turntables", "programming", "sampler", "oud", "baglama",
    }
)

URETIM_ROLLERI = frozenset(
    {
        "producer", "engineer", "mix", "master", "recording", "songwriter",
        "composer", "arranger", "conductor", "featuring", "remix",
    }
)

KANONIK_ROLLER = ENSTRUMAN_ROLLERI | URETIM_ROLLERI

# Müzikal içeriği olmayan roller — bilinçli olarak atılır, "bilinmeyen" sayılmaz.
ATILAN_ROLLER = frozenset(
    {
        "artwork", "design", "photography", "illustration", "layout", "sleeve",
        "liner notes", "notes", "management", "a&r", "executive producer",
        "executive-producer", "coordinator", "translation", "lacquer cut by",
        "pressed by", "distributed by", "manufactured by", "copyright",
        "phonographic copyright", "published by", "licensed to", "legal",
        "cover", "art direction", "creative director", "band photo", "graphics",
        "crew", "booking", "lighting", "a&r", "artists and repertoire", "stylist",
        "hair", "make-up", "catering", "assistant to", "personal assistant",
        "product manager", "marketing", "promotion", "mastering studio",
        "creative direction", "painting", "executive", "associate", "associate producer",
        # MB'nin bilgi taşımayan genel ilişki türleri: rol adı değil, "başka bir şey".
        "misc", "other", "band", "instrument", "performer", "vocal", "personnel",
    }
)

# --------------------------------------------------------------------------- #
# Birebir eşleme — en sık görülen varyantlar
# --------------------------------------------------------------------------- #

BIREBIR: dict[str, str] = {
    # davul / perküsyon
    "drums": "drums", "drum": "drums", "drum kit": "drums", "drum set": "drums",
    "drumset": "drums", "drums & percussion": "drums", "batterie": "drums",
    "schlagzeug": "drums", "davul": "drums", "acoustic drums": "drums",
    "percussion": "percussion", "perkusyon": "percussion", "congas": "percussion",
    "bongos": "percussion", "tabla": "percussion", "timbales": "percussion",
    "vibraphone": "percussion", "marimba": "percussion", "glockenspiel": "percussion",
    "tambourine": "percussion", "darbuka": "percussion", "cajon": "percussion",
    "cymbal": "percussion", "cymbals": "percussion", "hi-hat": "percussion",
    "hihat": "percussion", "gong": "percussion", "chimes": "percussion",
    "bells": "percussion", "bell": "percussion", "bell tree": "percussion",
    "wind chimes": "percussion", "cowbell": "percussion", "crotales": "percussion",
    "tubular bells": "percussion", "triangle": "percussion",
    "timpani": "percussion", "handclaps": "percussion", "claps": "percussion",
    "vibraslap": "percussion", "wind chime": "percussion", "wind chimes": "percussion",
    "shaker": "percussion", "castanets": "percussion", "woodblock": "percussion",
    "membranophone": "percussion", "idiophone": "percussion", "djembe": "percussion",
    # bas
    "bass": "bass", "bass guitar": "bass", "electric bass": "bass",
    "fretless bass": "bass", "double bass": "bass", "upright bass": "bass",
    "contrabass": "bass", "acoustic bass": "bass", "bas": "bass",
    "bass [6-string]": "bass", "stick": "bass",
    # gitar
    "guitar": "guitar", "guitars": "guitar", "electric guitar": "guitar",
    "acoustic guitar": "guitar", "rhythm guitar": "guitar", "lead guitar": "guitar",
    "slide guitar": "guitar", "classical guitar": "guitar", "12-string guitar": "guitar",
    "steel guitar": "guitar", "pedal steel guitar": "guitar", "gitar": "guitar",
    "baritone guitar": "guitar", "nylon string guitar": "guitar", "dobro": "guitar",
    # klavye
    "keyboards": "keyboards", "keyboard": "keyboards", "klavye": "keyboards",
    "piano": "piano", "acoustic piano": "piano", "grand piano": "piano",
    "electric piano": "piano", "rhodes": "piano", "wurlitzer": "piano",
    "clavinet": "piano", "celesta": "piano", "harpsichord": "piano",
    "organ": "organ", "hammond organ": "organ", "hammond": "organ",
    "farfisa": "organ", "farfisa organ": "organ", "harmonium": "organ",
    "synthesizer": "synthesizer", "synth": "synthesizer", "synthesizers": "synthesizer",
    "moog": "synthesizer", "minimoog": "synthesizer", "mellotron": "synthesizer",
    "oberheim": "synthesizer", "prophet-5": "synthesizer", "theremin": "synthesizer",
    "synclavier": "synthesizer", "fairlight": "synthesizer", "emulator": "synthesizer",
    # Taurus pedal sentezleyici: Discogs aynı kadroyu başka baskıda zaten
    # "Synthesizer" diye kredilemiş — pedal bir klavye değil, bir sentezleyicidir.
    "pedalboard": "synthesizer", "taurus pedals": "synthesizer",
    "bass pedals": "synthesizer", "pedals": "synthesizer",
    # vokal
    "vocals": "vocals", "vocal": "vocals", "voice": "vocals", "lead vocals": "vocals",
    "lead vocal": "vocals", "singer": "vocals", "vokal": "vocals",
    "backing vocals": "backing_vocals", "background vocals": "backing_vocals",
    "backing vocal": "backing_vocals", "choir": "backing_vocals",
    "chorus": "backing_vocals", "harmony vocals": "backing_vocals",
    "talkbox": "vocals", "talk box": "vocals", "vocoder": "vocals", "rap": "vocals",
    # nefesli / yaylı
    "saxophone": "saxophone", "sax": "saxophone", "tenor saxophone": "saxophone",
    "alto saxophone": "saxophone", "soprano saxophone": "saxophone",
    "baritone saxophone": "saxophone",
    "trumpet": "trumpet", "cornet": "trumpet", "flugelhorn": "trumpet",
    "trombone": "trombone", "tuba": "horns", "french horn": "horns",
    "horns": "horns", "brass": "horns", "horn": "horns",
    "wind instruments": "horns", "woodwind": "flute", "reeds": "clarinet",
    "flute": "flute", "clarinet": "clarinet", "oboe": "flute", "bassoon": "clarinet",
    "duduk": "flute", "zurna": "clarinet", "mey": "flute", "kaval": "flute",
    "violin": "violin", "fiddle": "violin", "viola": "viola", "cello": "cello",
    "strings": "strings", "string quartet": "strings", "orchestra": "strings",
    "keman": "violin",
    # diğer
    "harmonica": "harmonica", "banjo": "banjo", "mandolin": "mandolin",
    "harp": "harp", "accordion": "accordion", "sitar": "sitar",
    "oud": "oud", "ud": "oud", "bağlama": "baglama", "baglama": "baglama",
    "saz": "baglama", "ney": "flute", "kanun": "harp", "kemence": "violin",
    "turntables": "turntables", "dj": "turntables", "scratches": "turntables",
    "sampler": "sampler", "samples": "sampler",
    "programming": "programming", "programmed by": "programming",
    "drum programming": "programming", "drum machine": "programming",
    "beats": "programming", "electronics": "programming",
    "computer": "programming", "loops": "sampler", "loop": "sampler",
    # üretim
    "producer": "producer", "produced by": "producer", "co-producer": "producer",
    "prodüktör": "producer", "produktor": "producer",
    "engineer": "engineer", "engineered by": "engineer", "sound engineer": "engineer",
    "assistant engineer": "engineer", "technician": "engineer",
    # MB "assistant" ilişkisi stüdyo asistanıdır — mühendislik ailesine girer.
    "assistant": "engineer", "assistant mixer": "engineer",
    # Ses efekti / manipülasyon kredisi: elektronik üretim tarafına yazılır.
    "effects": "programming", "sound effects": "programming", "fx": "programming",
    "mixed by": "mix", "mix": "mix", "mixing": "mix", "remixed by": "remix",
    "remix": "remix", "remixer": "remix",
    # Enstrümanı belirtilmemiş konuk icracı — kadroda yeri var, aleti bilinmiyor.
    "musician": "featuring", "guest musician": "featuring", "additional musician": "featuring",
    "mastered by": "master", "master": "master", "mastering": "master",
    "remastered by": "master", "remaster": "master",
    "recorded by": "recording", "recording": "recording",
    # Kurgu bir mühendislik işidir, ayrı bir enstrüman değil.
    "edited by": "engineer", "editing": "engineer", "editor": "engineer",
    "written-by": "songwriter", "written by": "songwriter", "writer": "songwriter",
    "words by": "songwriter", "words": "songwriter", "lyricist": "songwriter",
    "songwriter": "songwriter", "lyrics by": "songwriter", "lyrics": "songwriter",
    "music by": "composer", "composed by": "composer", "composer": "composer",
    "arranged by": "arranger", "arranger": "arranger", "arrangement": "arranger",
    "orchestrator": "arranger", "orchestration": "arranger",
    "orchestrated by": "arranger",
    "conductor": "conductor", "conducted by": "conductor",
    "featuring": "featuring", "feat": "featuring", "feat.": "featuring",
    "guest": "featuring", "soloist": "featuring", "performer": "featuring",
}

# Birebir tutmayanlar için sıralı kurallar. Sıra önemli: "bass guitar" önce
# "bass"e takılmalı, "drum programming" önce "programming"e.
ANAHTAR_KURALLAR: tuple[tuple[str, str], ...] = (
    ("programming", "programming"),
    ("machine", "programming"),
    ("sequencer", "programming"),
    ("sample", "sampler"),
    ("turntable", "turntables"),
    ("scratch", "turntables"),
    ("backing vocal", "backing_vocals"),
    ("background vocal", "backing_vocals"),
    ("choir", "backing_vocals"),
    ("vocal", "vocals"),
    ("voice", "vocals"),
    ("bass", "bass"),
    ("guitar", "guitar"),
    ("drum", "drums"),
    ("percussion", "percussion"),
    ("piano", "piano"),
    ("organ", "organ"),
    ("synth", "synthesizer"),
    ("keyboard", "keyboards"),
    ("saxophone", "saxophone"),
    ("trumpet", "trumpet"),
    ("trombone", "trombone"),
    ("flute", "flute"),
    ("clarinet", "clarinet"),
    ("violin", "violin"),
    ("viola", "viola"),
    ("cello", "cello"),
    ("string", "strings"),
    ("horn", "horns"),
    ("brass", "horns"),
    ("harmonica", "harmonica"),
    ("banjo", "banjo"),
    ("mandolin", "mandolin"),
    ("accordion", "accordion"),
    ("harp", "harp"),
    ("produc", "producer"),
    ("engineer", "engineer"),
    ("mixed", "mix"),
    ("mixing", "mix"),
    ("master", "master"),
    ("record", "recording"),
    ("written", "songwriter"),
    ("lyric", "songwriter"),
    ("compos", "composer"),
    ("arrang", "arranger"),
    ("conduct", "conductor"),
    ("featur", "featuring"),
)

_NITELIK = re.compile(r"[\[\(\{][^\]\)\}]*[\]\)\}]")   # [Additional], (uncredited)
_AYIRICI = re.compile(r"\s*(?:,|/|;|\band\b|&|\+)\s*")
_TEMIZ = re.compile(r"[*\d]+$")                        # "Drums 2", "Bass*"


@dataclass(frozen=True)
class RolAyrim:
    roller: tuple[str, ...]
    bilinmeyen: tuple[str, ...]

    def __bool__(self) -> bool:
        return bool(self.roller)


def _tek_rol(parca: str) -> tuple[str | None, bool]:
    """(kanonik rol, bilinmeyen mi). Bilinçli atılanlarda (None, False)."""
    metin = _NITELIK.sub(" ", parca).strip().lower()
    metin = _TEMIZ.sub("", metin).strip(" -–—.")
    metin = re.sub(r"\s+", " ", metin)
    if not metin:
        return None, False
    if metin in ATILAN_ROLLER:
        return None, False
    if metin in BIREBIR:
        return BIREBIR[metin], False
    if metin in KANONIK_ROLLER:
        return metin, False
    for parca_metin, rol in ANAHTAR_KURALLAR:
        if parca_metin in metin:
            return rol, False
    if any(atilan in metin for atilan in ATILAN_ROLLER):
        return None, False
    return None, True


def _birebir_bak(metin: str) -> tuple[str | None, bool] | None:
    """Yalnızca sözlük/atılan kontrolü — anahtar kelime tahmini YAPMAZ.

    Bütün dizeyi denemek için kullanılır: "A&R" atılanlar listesinde ama
    ayırıcı "&" onu "a" + "r" diye parçalarsa bu bilgi kaybolur. Anahtar kelime
    kuralı burada devreye girmemeli, yoksa "Bass, Backing Vocals" bütün olarak
    "bass"e eşleşir ve ikinci rol düşer.
    """
    temiz = re.sub(r"\s+", " ", _TEMIZ.sub("", metin.strip().lower()).strip(" -–—."))
    if not temiz:
        return None, False
    if temiz in ATILAN_ROLLER:
        return None, False
    if temiz in BIREBIR:
        return BIREBIR[temiz], False
    if temiz in KANONIK_ROLLER:
        return temiz, False
    return None


def rollere_ayir(ham: str | None) -> RolAyrim:
    """Ham rol dizesini kanonik rollere ayır.

    >>> rollere_ayir("Bass, Backing Vocals [Additional]").roller
    ('backing_vocals', 'bass')
    """
    if not ham:
        return RolAyrim((), ())

    # Parçalamadan önce bütün dizeyi birebir dene (yalnızca sözlük).
    butun = _birebir_bak(_NITELIK.sub(" ", ham))
    if butun is not None:
        rol, _ = butun
        return RolAyrim((rol,) if rol else (), ())

    roller: set[str] = set()
    bilinmeyen: set[str] = set()
    # Nitelikler ayırıcı içerebilir ("Guitar [Rhythm, Lead]") — önce onlar temizlenir.
    for parca in _AYIRICI.split(_NITELIK.sub(" ", ham)):
        parca = parca.strip()
        if not parca:
            continue
        rol, bilinmiyor = _tek_rol(parca)
        if rol:
            roller.add(rol)
        elif bilinmiyor:
            bilinmeyen.add(parca.lower())
    return RolAyrim(tuple(sorted(roller)), tuple(sorted(bilinmeyen)))


def rol_normalize(ham: str | None) -> str | None:
    """Tek rol bekleniyorsa kısayol (MusicBrainz nitelikleri gibi)."""
    ayrim = rollere_ayir(ham)
    return ayrim.roller[0] if ayrim.roller else None


if __name__ == "__main__":  # elle göz atmak için
    ornekler = [
        "Drums", "Drums [Additional]", "Bass, Backing Vocals", "Electric Guitar",
        "Written-By, Producer", "Mixed By", "Drum Programming", "Artwork",
        "Bağlama", "Tenor Saxophone", "Hammond Organ", "Zither",
    ]
    for ornek in ornekler:
        ayrim = rollere_ayir(ornek)
        print(f"{ornek:<28} → {ayrim.roller}  bilinmeyen={ayrim.bilinmeyen}")
