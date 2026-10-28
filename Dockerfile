FROM node:22-alpine AS frontend-build
WORKDIR /app

COPY package.json pnpm-lock.yaml ./
RUN npm install -g pnpm@10.16.1
RUN pnpm install --frozen-lockfile

COPY . .
RUN pnpm build

FROM python:3.12-slim
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    APP_HOST=0.0.0.0 \
    APP_PORT=8000

COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY backend ./backend
COPY --from=frontend-build /app/dist ./dist
RUN useradd --system --create-home appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appuser /app/data

USER appuser

EXPOSE 8000

CMD ["sh", "-c", "export APP_PORT=\"${PORT:-${APP_PORT:-8000}}\"; exec python -m uvicorn backend.app.main:app --host \"${APP_HOST:-0.0.0.0}\" --port \"$APP_PORT\""]
