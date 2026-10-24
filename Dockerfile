FROM python:3.12-slim

# Distrust emSign ECC Root CA - G3 (compromised intermediates, Mozilla emergency distrust 2026-10)
RUN sed -i 's|^mozilla/emSign_ECC_Root_CA_-_G3\.crt$|!&|' /etc/ca-certificates.conf \
    && update-ca-certificates --fresh > /dev/null \
    && test ! -e /etc/ssl/certs/emSign_ECC_Root_CA_-_G3.pem

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "-u", "-m", "gfk.main"]
