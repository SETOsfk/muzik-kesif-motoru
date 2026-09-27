import json
from pathlib import Path
from python.ingest.dinleme_logu import spotify_oku, bicim_sez

def test_spotify_oku(tmp_path: Path):
    ornek = [
        {
            "ts": "2023-08-10T14:32:00Z",
            "master_metadata_album_artist_name": "Casiopea",
            "master_metadata_album_album_name": "Mint Jams",
            "master_metadata_track_name": "Asayake",
            "ms_played": 210000,
            "reason_end": "trackdone",
        },
        {
            "ts": "2023-08-10T14:35:00Z",
            "master_metadata_album_artist_name": "Atlanan Grup",
            "master_metadata_album_album_name": "Atlanan Albüm",
            "master_metadata_track_name": "Kısa Şarkı",
            "ms_played": 15000,  # 15 sn (30 sn altında - atlandı)
            "reason_end": "fwdbtn",
        },
    ]
    dosya = tmp_path / "Streaming_History_Audio_2023.json"
    dosya.write_text(json.dumps(ornek), encoding="utf-8")

    assert bicim_sez(dosya) == "spotify"

    satirlar, tarihsiz = spotify_oku(dosya, "2023-08-10", asgari_ms=30000)
    assert len(satirlar) == 1
    assert satirlar[0].artist == "Casiopea"
    assert satirlar[0].album == "Mint Jams"
    assert satirlar[0].track == "Asayake"
    assert satirlar[0].tarih == "2023-08-10"
