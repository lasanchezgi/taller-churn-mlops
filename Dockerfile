# Imagen opcional del servicio (T061). Sin cuentas ni registros externos.
FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
# Editable: config.ROOT se calcula desde la ubicación del código y debe resolver a /app
RUN pip install --no-cache-dir -e .

# El modelo, su ficha (con hash_modelo) y el panel viajan con la imagen
COPY models ./models
COPY dashboard ./dashboard

# La sal del codificado debe venir del entorno: docker run -e CHURN_HASH_SALT=...
ENV CHURN_HASH_SALT=""
RUN useradd --create-home app && mkdir -p logs reports/metrics && chown -R app /app
USER app
EXPOSE 8000
CMD ["uvicorn", "churn.api:app", "--host", "0.0.0.0", "--port", "8000"]
