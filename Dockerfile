FROM python:3.9-alpine
ENV TZ=America/Sao_Paulo
WORKDIR /app

COPY src/ src/
COPY poetry.lock poetry.lock
COPY pyproject.toml pyproject.toml

RUN apk add --no-cache musl-dev gcc git
RUN pip install poetry --no-cache-dir
RUN poetry export --without-hashes --without dev -f requirements.txt -o requirements.txt
RUN pip install --no-cache-dir -r requirements.txt \
    && rm -rf /root/.cache/pip/* \
    && pip uninstall poetry -y \
    && rm -rf requirements.txt pyproject.toml poetry.lock \
    rm -rf /usr/share/doc /usr/share/man /usr/share/info /var/cache/apk/*

RUN rm -rf /tmp/* /var/tmp/* \
    && rm -rf /var/lib/apt/lists/*

USER nobody

ENTRYPOINT ["python", "-m", "src"]