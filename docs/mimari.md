# Mimari

## Veri akışı

```
FLAC kütüphanesi ──┐
                   ├──> ingest ──> albums, plays
Symfonium logu ────┘                  │
                                      v
                          enrich (MusicBrainz, Discogs)
                                      │
                          credits, tags, audio_features
                                      │
                                      v
                        öznitelik matrisi (Parquet)
                                      │
                                      v
                     boyut indirgeme + FCM + stabilite
                                      │
                              memberships, clusters
                                      │
                                      v
                     [Streamlit] küme isimlendirme  ← FAZ 1 BİTİŞİ
                                      │
                                      v
                          eksen seçimi ("neyi besleyeyim?")
                                      │
                                      v
                       aday üretimi (kredi grafiği / komşuluk / uzaklık)
                                      │
                                      v
           derin araştırma (Reddit, incelemeler) + ozetle() [varsayılan: çıkarımsal]
                                      │
                                      v
                       öneri kartı + 30 sn önizleme + geri bildirim
```

## Öznitelik matrisi

Kümelemeye giren albüm × öznitelik matrisi dört bloktan oluşur:

1. **Kredi blokları** — sık geçen müzisyenler için ikili göstergeler (albümde çaldı mı).
   Sadece kütüphanede ≥2 albümde geçen kişiler alınır, yoksa matris seyrekleşir.
2. **Sahne/coğrafya** — ülke, label, dönem (10 yıllık dilim).
3. **Etiketler** — ağırlıklı tür/alt tür vektörü.
4. **Ses öznitelikleri** — librosa özetleri, standartlaştırılmış.

Bloklar arası ölçek farkı sorun yaratır: her blok kendi içinde normalize edilir ve
blok ağırlıkları yapılandırılabilir tutulur (`python/kumeleme/ayar.py`). Varsayılan olarak kredi
bloğu ağırlığı yüksek — projenin çekirdek tezi bu.

## Neden bu sıra

Kredi zenginleştirme en yavaş ve en rate-limitli adım. Önce çalıştırılır ve
önbelleklenir; kümeleme parametreleriyle oynarken tekrar API'ye gidilmez.
