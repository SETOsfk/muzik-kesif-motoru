# Keşif Motoru — tek imaj: web sunucusu + aktarım süreci (CLAP, CPU).
#
# Hugging Face Spaces bu dosyayı olduğu gibi derler (bkz. .github/workflows/
# hf-space.yml). Her ortamda HTTPS vekili ardında: KESIF_HTTPS=1.
#
# torch CPU tekerleğiyle kurulur (~200 MB; GPU sürümü ~2 GB ve gereksiz:
# klip başına ~1 sn). Sunucu süreci torch'u YÜKLEMEZ, yalnız aktarım süreci.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/app/data/hf \
    KESIF_HTTPS=1

# libsndfile: librosa'nın MP3 önizlemeyi okuması için.
RUN apt-get update \
 && apt-get install -y --no-install-recommends libsndfile1 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements-sunucu.txt requirements-aktarim.txt ./
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu \
 && pip install -r requirements-aktarim.txt

COPY python ./python
COPY web ./web

# Kök olmayan kullanıcı; veri /app/data'da (compose'da bağlanan klasör).
RUN useradd --create-home --uid 1000 kesif && mkdir -p data && chown kesif:kesif data
USER kesif

EXPOSE 8800
HEALTHCHECK --interval=60s --timeout=5s --start-period=20s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8800/saglik', timeout=4)"
CMD ["python", "-m", "web.sunucu", "--host", "0.0.0.0", "--port", "8800"]
