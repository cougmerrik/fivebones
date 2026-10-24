FROM python:3.12.9-slim
WORKDIR /app
COPY server/requirements.lock ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt && useradd --uid 10001 --create-home bones && mkdir /data && chown bones /data
COPY server/app ./app
USER bones
ENV DATABASE_PATH=/data/fivebones.sqlite3 PORT=8000 PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["python", "-m", "app.start"]
