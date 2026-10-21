# Imagen para ejecutar DengueML-UPN en cualquier equipo con Docker o en un servicio de contenedores.
FROM python:3.12-slim
WORKDIR /app
COPY requirements-lock.txt requirements.txt ./
RUN pip install --no-cache-dir -r requirements-lock.txt
COPY src ./src
COPY models ./models
COPY data/versions ./data/versions
COPY reports/fuente_oficial.json ./reports/fuente_oficial.json
EXPOSE 8501
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
CMD ["sh", "-c", "streamlit run src/app.py --server.address=0.0.0.0 --server.port=${PORT:-8501} --server.headless=true"]
