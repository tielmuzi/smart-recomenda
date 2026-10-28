from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlencode, urlsplit

import httpx
import jwt
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env", override=False)
APP_ENV = os.getenv("APP_ENV", "development")
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("PORT", os.getenv("APP_PORT", "8000")))
FRONTEND_ORIGIN = os.getenv("FRONTEND_URL", "http://localhost:3000")
DEFAULT_CORS = FRONTEND_ORIGIN if APP_ENV == "production" else f"{FRONTEND_ORIGIN},http://127.0.0.1:3000,http://localhost:3000"
CORS_ORIGINS = [item.strip().rstrip("/") for item in os.getenv("CORS_ORIGINS", DEFAULT_CORS).split(",") if item.strip()]
AUTH_CLIENT_ID = os.getenv("AUTH_CLIENT_ID") or os.getenv("MANUS_PROJECT_ID", "")
AUTH_PORTAL_URL = os.getenv("AUTH_PORTAL_URL") or os.getenv("MANUS_OAUTH_PORTAL_URL", "")
AUTH_API_URL = os.getenv("AUTH_API_URL") or os.getenv("MANUS_OAUTH_API_URL", "")
AUTH_JWT_SECRET = os.getenv("AUTH_JWT_SECRET") or os.getenv("MANUS_JWT_SECRET", "")
AUTH_CALLBACK_URL = os.getenv("AUTH_CALLBACK_URL", f"{FRONTEND_ORIGIN.rstrip('/')}/api/v1/auth/callback")
AUTH_COOKIE_NAME = "webdev_app_session"
AUTH_SESSION_SECONDS = 8 * 60 * 60
AUTH_STATE_SECONDS = 10 * 60
DEMO_ACCESS = os.getenv("DEMO_ACCESS", "true").lower() == "true"
AUTH_COOKIE_SECURE = APP_ENV == "production" or os.getenv("AUTH_COOKIE_SECURE", "true").lower() == "true"
AUTH_COOKIE_SAMESITE = "none" if APP_ENV == "production" else os.getenv("AUTH_COOKIE_SAMESITE", "none").lower()
if AUTH_COOKIE_SAMESITE not in {"lax", "strict", "none"}:
    raise ValueError("AUTH_COOKIE_SAMESITE deve ser lax, strict ou none.")
if AUTH_COOKIE_SAMESITE == "none" and not AUTH_COOKIE_SECURE:
    raise ValueError("AUTH_COOKIE_SECURE precisa ser true quando AUTH_COOKIE_SAMESITE=none.")
DB_URL = os.getenv("DATABASE_URL", f"sqlite:///{ROOT / 'smartrecomenda.db'}")
DB_PATH = Path(DB_URL.replace("sqlite:///", "")) if DB_URL.startswith("sqlite:///") else ROOT / "smartrecomenda.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
DEMO_USER = "demo-academic-visitor"
ADMIN_IDS = {item.strip() for item in os.getenv("ADMIN_OPEN_IDS", "").split(",") if item.strip()}

SCHEMA = """
CREATE TABLE IF NOT EXISTS contents (id INTEGER PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL, type TEXT NOT NULL, genres TEXT NOT NULL, language TEXT NOT NULL, year INTEGER, cover TEXT NOT NULL, popularity REAL NOT NULL DEFAULT 0, is_demo INTEGER NOT NULL DEFAULT 1, featured INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS profiles (user_id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT, history_enabled INTEGER NOT NULL DEFAULT 0, role TEXT NOT NULL DEFAULT 'user');
CREATE TABLE IF NOT EXISTS preferences (user_id TEXT PRIMARY KEY, types TEXT NOT NULL, genres TEXT NOT NULL, languages TEXT NOT NULL, blocked_ids TEXT NOT NULL, diversity TEXT NOT NULL, FOREIGN KEY(user_id) REFERENCES profiles(user_id));
CREATE TABLE IF NOT EXISTS ratings (user_id TEXT NOT NULL, content_id INTEGER NOT NULL, rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5), updated_at TEXT DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(user_id, content_id));
CREATE TABLE IF NOT EXISTS favorites (user_id TEXT NOT NULL, content_id INTEGER NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(user_id, content_id));
CREATE TABLE IF NOT EXISTS interactions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, content_id INTEGER NOT NULL, kind TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS recommendation_events (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, strategy TEXT NOT NULL, item_count INTEGER NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_contents_type ON contents(type);
CREATE INDEX IF NOT EXISTS idx_interactions_user ON interactions(user_id);
CREATE INDEX IF NOT EXISTS idx_ratings_user ON ratings(user_id);
CREATE INDEX IF NOT EXISTS idx_favorites_user ON favorites(user_id);
CREATE INDEX IF NOT EXISTS idx_recommendations_user ON recommendation_events(user_id);
"""

DEMO_CONTENTS = [
    (101, "Orbital 9", "Uma engenheira recebe um sinal impossível vindo de uma estação esquecida e precisa decidir se responde.", "Filme", ["Ficção científica", "Suspense"], "Português", 2024, "https://images.unsplash.com/photo-1446776811953-b23d57bd21aa?auto=format&fit=crop&w=900&q=85", 0.91, 1, 1),
    (102, "Código de Aurora", "Série demonstrativa sobre uma equipe que transforma dados complexos em decisões humanas.", "Série", ["Tecnologia", "Drama"], "Português", 2025, "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=900&q=85", 0.87, 1, 1),
    (103, "After the Interface", "Uma faixa eletrônica minimalista sobre encontrar ritmo no ruído digital.", "Música", ["Indie", "Tecnologia"], "Inglês", 2025, "https://images.unsplash.com/photo-1516280440614-37939bbacd81?auto=format&fit=crop&w=900&q=85", 0.78, 1, 0),
    (104, "O mapa das pequenas escolhas", "Registro jornalístico fictício sobre como comunidades redesenham seus espaços com tecnologia aberta.", "Notícia", ["Cultura", "Tecnologia"], "Português", 2026, "https://images.unsplash.com/photo-1495020689067-958852a7765e?auto=format&fit=crop&w=900&q=85", 0.74, 1, 0),
    (105, "Maré de Dados", "Documentário demonstrativo sobre oceanos, sensores e decisões colaborativas.", "Filme", ["Documentário", "Tecnologia"], "Português", 2023, "https://images.unsplash.com/photo-1484291470158-b8f8d608850d?auto=format&fit=crop&w=900&q=85", 0.83, 1, 0),
    (106, "Vértice", "Thriller especulativo em que um algoritmo de trânsito começa a prever escolhas humanas.", "Série", ["Suspense", "Ficção científica"], "Inglês", 2024, "https://images.unsplash.com/photo-1535378917042-10a22c95931a?auto=format&fit=crop&w=900&q=85", 0.8, 1, 0),
    (107, "Design para amanhã", "Conversa visual e fictícia com designers que trabalham entre acessibilidade e futuro.", "Notícia", ["Design", "Cultura"], "Português", 2026, "https://images.unsplash.com/photo-1558655146-d09347e92766?auto=format&fit=crop&w=900&q=85", 0.71, 1, 0),
    (108, "Luzes de baixa frequência", "Álbum ambiente para leituras longas, noites calmas e ideias que precisam de espaço.", "Música", ["Indie", "Cultura"], "Inglês", 2024, "https://images.unsplash.com/photo-1511379938547-c1f69419868d?auto=format&fit=crop&w=900&q=85", 0.69, 1, 0),
    (109, "Padrão de Chuva", "Filme demonstrativo sobre uma cidade que redescobre seus arquivos através de sons.", "Filme", ["Drama", "Cultura"], "Português", 2022, "https://images.unsplash.com/photo-1500534623283-312aade485b7?auto=format&fit=crop&w=900&q=85", 0.66, 1, 0),
    (110, "Sinais do cotidiano", "Série curta demonstrativa sobre as pequenas tecnologias invisíveis que organizam uma rotina.", "Série", ["Documentário", "Design"], "Português", 2023, "https://images.unsplash.com/photo-1497366754035-f200968a6e72?auto=format&fit=crop&w=900&q=85", 0.63, 1, 0),
    (111, "Cidade em camadas", "Notícia fictícia sobre memória urbana, mapas colaborativos e o direito de pertencer.", "Notícia", ["Cultura", "Tecnologia"], "Português", 2026, "https://images.unsplash.com/photo-1477959858617-67f85cf4f1df?auto=format&fit=crop&w=900&q=85", 0.62, 1, 0),
    (112, "Matriz Solar", "Faixa instrumental que mistura sintetizadores quentes e a sensação de uma manhã nova.", "Música", ["Indie", "Ficção científica"], "Inglês", 2025, "https://images.unsplash.com/photo-1470229722913-7c0e2dbbafd3?auto=format&fit=crop&w=900&q=85", 0.6, 1, 0),
]

@contextmanager
def db():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()

def json_load(value: str, default: Any):
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default

def init_db():
    with db() as connection:
        connection.executescript(SCHEMA)
        for item in DEMO_CONTENTS:
            connection.execute("INSERT OR IGNORE INTO contents(id,title,description,type,genres,language,year,cover,popularity,is_demo,featured) VALUES(?,?,?,?,?,?,?,?,?,?,?)", (item[0], item[1], item[2], item[3], json.dumps(item[4]), item[5], item[6], item[7], item[8], item[9], item[10]))
        if DEMO_ACCESS:
            connection.execute(
                "INSERT OR IGNORE INTO profiles(user_id,name,email,role) VALUES(?,?,?,?)",
                (DEMO_USER, "Visitante acadêmico", None, "user"),
            )
            defaults = demo_prefs()
            connection.execute(
                "INSERT OR IGNORE INTO preferences(user_id,types,genres,languages,blocked_ids,diversity) VALUES(?,?,?,?,?,?)",
                (DEMO_USER, json.dumps(defaults["types"]), json.dumps(defaults["genres"]), json.dumps(defaults["languages"]), "[]", defaults["diversity"]),
            )

def demo_prefs():
    return {"types": ["Filme", "Série", "Música"], "genres": ["Ficção científica", "Tecnologia", "Suspense"], "languages": ["Português", "Inglês"], "blocked_ids": [], "diversity": "equilibrada"}

def provision_user(user_id: str, name: str, email: str | None):
    role = "admin" if user_id != DEMO_USER and user_id in ADMIN_IDS else "user"
    with db() as connection:
        connection.execute(
            "INSERT INTO profiles(user_id,name,email,role) VALUES(?,?,?,?) "
            "ON CONFLICT(user_id) DO UPDATE SET name=excluded.name,email=excluded.email,role=excluded.role",
            (user_id, name, email, role),
        )
        defaults = demo_prefs()
        connection.execute(
            "INSERT OR IGNORE INTO preferences(user_id,types,genres,languages,blocked_ids,diversity) VALUES(?,?,?,?,?,?)",
            (user_id, json.dumps(defaults["types"]), json.dumps(defaults["genres"]), json.dumps(defaults["languages"]), "[]", defaults["diversity"]),
        )

def current_user(request: Request) -> str:
    token = request.cookies.get(AUTH_COOKIE_NAME)
    if not token:
        authorization = request.headers.get("authorization", "")
        token = authorization.removeprefix("Bearer ").strip() if authorization.startswith("Bearer ") else ""
    if not token:
        if DEMO_ACCESS:
            return DEMO_USER
        if not AUTH_JWT_SECRET or not AUTH_CLIENT_ID:
            raise HTTPException(503, "Autenticação não está configurada.")
        raise HTTPException(401, "Autenticação necessária.")
    if not AUTH_JWT_SECRET or not AUTH_CLIENT_ID:
        raise HTTPException(503, "Autenticação não está configurada para validar esta sessão.")
    try:
        claims = jwt.decode(
            token,
            AUTH_JWT_SECRET,
            algorithms=["HS256"],
            options={"require": ["exp", "sub", "appId"]},
        )
    except jwt.InvalidTokenError as error:
        if DEMO_ACCESS:
            request.state.demo_fallback = True
            return DEMO_USER
        raise HTTPException(401, "Sessão inválida ou expirada.") from error
    if claims.get("appId") != AUTH_CLIENT_ID or not isinstance(claims.get("sub"), str) or not claims["sub"]:
        if DEMO_ACCESS:
            request.state.demo_fallback = True
            return DEMO_USER
        raise HTTPException(401, "Sessão inválida para esta aplicação.")
    return claims["sub"]

def is_admin(user_id: str) -> bool:
    return user_id != DEMO_USER and user_id in ADMIN_IDS


def auth_configured() -> bool:
    callback = urlsplit(AUTH_CALLBACK_URL)
    callback_valid = callback.scheme in {"http", "https"} and bool(callback.netloc)
    if APP_ENV == "production":
        callback_valid = callback_valid and callback.scheme == "https" and "localhost" not in callback.netloc
    return bool(AUTH_CLIENT_ID and AUTH_PORTAL_URL and AUTH_API_URL and AUTH_JWT_SECRET and callback_valid)


def auth_callback_url() -> str:
    if not auth_configured():
        raise HTTPException(503, "Configure as variáveis AUTH_* e uma URL de callback válida.")
    return AUTH_CALLBACK_URL


def encoded_state(payload: dict[str, str]) -> str:
    return urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")


def decode_state(state: str) -> dict[str, Any]:
    try:
        decoded = urlsafe_b64decode(state + "=" * (-len(state) % 4))
        payload = json.loads(decoded)
    except (ValueError, json.JSONDecodeError) as error:
        raise HTTPException(400, "Estado OAuth inválido.") from error
    if not isinstance(payload, dict) or not isinstance(payload.get("nonce"), str) or not isinstance(payload.get("redirectUri"), str):
        raise HTTPException(400, "Estado OAuth inválido.")
    return payload


def auth_provider_endpoint(path: str) -> str:
    return f"{AUTH_API_URL.rstrip('/')}/webdev.v1.WebDevAuthPublicService/{path}"


def exchange_auth_code(code: str, redirect_uri: str) -> dict[str, Any]:
    try:
        with httpx.Client(timeout=10) as client:
            response = client.post(
                auth_provider_endpoint("ExchangeToken"),
                json={
                    "clientId": AUTH_CLIENT_ID,
                    "grantType": "authorization_code",
                    "code": code,
                    "redirectUri": redirect_uri,
                },
            )
            response.raise_for_status()
            token_payload = response.json()
            access_token = token_payload.get("accessToken")
            if not isinstance(access_token, str) or not access_token:
                raise HTTPException(502, "O provedor não retornou um token de acesso.")
            identity_response = client.post(
                auth_provider_endpoint("GetUserInfo"),
                json={"accessToken": access_token},
            )
            identity_response.raise_for_status()
            identity = identity_response.json()
    except httpx.HTTPStatusError as error:
        raise HTTPException(502, "O provedor de autenticação recusou a solicitação.") from error
    except httpx.RequestError as error:
        raise HTTPException(502, "Não foi possível conectar ao provedor de autenticação.") from error
    except ValueError as error:
        raise HTTPException(502, "O provedor de autenticação retornou uma resposta inválida.") from error
    if not isinstance(identity, dict) or not isinstance(identity.get("openId"), str) or not identity["openId"]:
        raise HTTPException(502, "O provedor não retornou uma identidade válida.")
    return identity

def content_from_row(row: sqlite3.Row, reason: str | None = None, rating: float | None = None) -> dict[str, Any]:
    return {"id": row["id"], "title": row["title"], "description": row["description"], "type": row["type"], "genres": json_load(row["genres"], []), "language": row["language"], "year": row["year"], "cover": row["cover"], "popularity": row["popularity"], "is_demo": bool(row["is_demo"]), "featured": bool(row["featured"]), "rating": rating, "rating_count": 0, "reason": reason}

def average_rating(connection: sqlite3.Connection, content_id: int) -> tuple[float | None, int]:
    row = connection.execute("SELECT AVG(rating) average, COUNT(*) total FROM ratings WHERE content_id=?", (content_id,)).fetchone()
    return (round(row["average"], 1) if row["average"] is not None else None, row["total"])

def load_user_signals(connection: sqlite3.Connection, user_id: str) -> dict[str, Any]:
    ratings = connection.execute(
        "SELECT content_id,rating FROM ratings WHERE user_id=?",
        (user_id,),
    ).fetchall()
    favorites = connection.execute(
        "SELECT content_id FROM favorites WHERE user_id=?",
        (user_id,),
    ).fetchall()
    interactions = connection.execute(
        "SELECT content_id,kind,COUNT(*) count FROM interactions WHERE user_id=? GROUP BY content_id,kind",
        (user_id,),
    ).fetchall()

    content_rows = connection.execute("SELECT id,genres,type,language FROM contents").fetchall()
    content_meta = {
        row["id"]: {
            "genres": json_load(row["genres"], []),
            "type": row["type"],
            "language": row["language"],
        }
        for row in content_rows
    }
    genre_totals: dict[str, float] = {}
    type_totals: dict[str, float] = {}
    language_totals: dict[str, float] = {}
    rated_ids = set()
    favorite_ids = {row["content_id"] for row in favorites}
    view_counts: dict[int, int] = {}
    hidden_ids: set[int] = set()

    def apply_signal(content_id: int, value: float):
        meta = content_meta.get(content_id)
        if not meta:
            return
        for genre in set(meta["genres"]):
            genre_totals[genre] = genre_totals.get(genre, 0.0) + value
        type_totals[meta["type"]] = type_totals.get(meta["type"], 0.0) + value
        language_totals[meta["language"]] = language_totals.get(meta["language"], 0.0) + value

    for row in ratings:
        rated_ids.add(row["content_id"])
        normalized_rating = (row["rating"] - 3) / 2
        apply_signal(row["content_id"], normalized_rating)
    for content_id in favorite_ids:
        apply_signal(content_id, 0.8)
    for row in interactions:
        content_id, kind, count = row["content_id"], row["kind"], row["count"]
        if kind == "view":
            view_counts[content_id] = count
            apply_signal(content_id, min(0.24, 0.08 * count))
        elif kind == "hide":
            hidden_ids.add(content_id)
            apply_signal(content_id, -1.0)

    return {
        "genre_totals": genre_totals,
        "type_totals": type_totals,
        "language_totals": language_totals,
        "rated_ids": rated_ids,
        "favorite_ids": favorite_ids,
        "view_counts": view_counts,
        "hidden_ids": hidden_ids,
    }


def normalized_affinity(candidate_values: list[str], totals: dict[str, float]) -> float:
    if not candidate_values or not totals:
        return 0.0
    average_signal = sum(totals.get(value, 0.0) for value in set(candidate_values)) / len(set(candidate_values))
    return max(-1.0, min(1.0, average_signal / 1.5))


def score_content(
    row: sqlite3.Row,
    prefs: dict[str, Any],
    signals: dict[str, Any],
    average_rating_value: float | None,
) -> tuple[float, str]:
    row_genres = set(json_load(row["genres"], []))
    selected = set(prefs["genres"])
    selected_types = set(prefs["types"])
    selected_languages = set(prefs["languages"])
    genre_overlap = len(row_genres & selected) / max(1, len(selected)) if selected else 0.0
    type_match = 1.0 if row["type"] in selected_types else 0.0
    language_match = 1.0 if row["language"] in selected_languages else 0.0
    explicit_affinity = genre_overlap * 0.65 + type_match * 0.25 + language_match * 0.10
    learned_affinity = (
        normalized_affinity(list(row_genres), signals["genre_totals"]) * 0.65
        + normalized_affinity([row["type"]], signals["type_totals"]) * 0.25
        + normalized_affinity([row["language"]], signals["language_totals"]) * 0.10
    )
    global_quality = ((average_rating_value or 3.0) - 3.0) / 2.0 if average_rating_value is not None else 0.0
    popularity = max(0.0, min(1.0, float(row["popularity"] or 0)))
    seen_penalty = min(0.20, 0.10 * signals["view_counts"].get(row["id"], 0))
    if row["id"] in signals["rated_ids"]:
        seen_penalty += 0.12
    exploration = 0.06 if prefs.get("diversity") == "exploradora" else 0.0

    score = (
        0.44 * explicit_affinity
        + 0.34 * learned_affinity
        + 0.10 * global_quality
        + 0.12 * popularity
        - seen_penalty
        + exploration * (1.0 - explicit_affinity)
    )
    score = max(0.0, min(1.0, (score + 0.18) / 1.18))

    learned_genres = row_genres & signals["genre_totals"].keys()
    strongest_genre = max(
        learned_genres,
        key=lambda genre: signals["genre_totals"].get(genre, 0.0),
        default=None,
    )
    if strongest_genre and signals["genre_totals"][strongest_genre] > 0 and strongest_genre not in selected:
        reason = f"Com base nas suas avaliações e itens salvos, você tende a gostar de {strongest_genre.lower()}."
    elif row_genres & selected:
        reason = f"Combina com o tema {sorted(row_genres & selected)[0].lower()} que você escolheu."
    elif row["id"] in signals["favorite_ids"]:
        reason = "Você salvou este conteúdo nos favoritos."
    elif average_rating_value is not None and average_rating_value >= 4.0:
        reason = "Bem avaliado por quem também explora este catálogo."
    elif prefs.get("diversity") == "exploradora":
        reason = "Uma opção para ampliar seu repertório com base nos seus sinais anteriores."
    else:
        reason = "Selecionado pelo equilíbrio entre suas preferências e a popularidade."
    return score, reason

def recommendations(user_id: str, limit: int = 8, item_type: str | None = None, genre: str | None = None, language: str | None = None) -> tuple[list[dict[str, Any]], str]:
    with db() as connection:
        pref_row = connection.execute("SELECT * FROM preferences WHERE user_id=?", (user_id,)).fetchone()
        prefs = {key: json_load(pref_row[key], []) if key != "diversity" else pref_row[key] for key in ["types", "genres", "languages", "blocked_ids", "diversity"]} if pref_row else demo_prefs()
        signals = load_user_signals(connection, user_id)
        blocked_ids = set(prefs["blocked_ids"]) | signals["hidden_ids"]
        ratings_by_content = {
            row["id"]: (round(row["average"], 1) if row["average"] is not None else None, row["total"])
            for row in connection.execute(
                "SELECT content_id id,AVG(rating) average,COUNT(*) total FROM ratings GROUP BY content_id"
            ).fetchall()
        }
        items = []
        for row in connection.execute("SELECT * FROM contents ORDER BY popularity DESC").fetchall():
            if row["id"] in blocked_ids:
                continue
            if item_type and row["type"] != item_type:
                continue
            if genre and genre not in json_load(row["genres"], []):
                continue
            if language and row["language"] != language:
                continue
            avg, count = ratings_by_content.get(row["id"], (None, 0))
            score, reason = score_content(row, prefs, signals, avg)
            item = content_from_row(row, reason, avg)
            item["rating_count"] = count
            item["score"] = round(score, 3)
            items.append(item)

        items.sort(key=lambda item: item["score"], reverse=True)
        chosen = []
        candidates = list(items)
        while candidates and len(chosen) < limit:
            selected_index = 0
            if prefs.get("diversity") != "foco" and chosen:
                different_type_index = next(
                    (index for index, item in enumerate(candidates) if item["type"] != chosen[-1]["type"]),
                    None,
                )
                if different_type_index is not None:
                    selected_index = different_type_index
            chosen.append(candidates.pop(selected_index))
        connection.execute("INSERT INTO recommendation_events(user_id,strategy,item_count) VALUES(?,?,?)", (user_id, "HybridStrategy", len(chosen)))
        return chosen, "HybridStrategy"

class PreferencePayload(BaseModel):
    types: list[str] = Field(default_factory=list)
    genres: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    blocked_ids: list[int] = Field(default_factory=list)
    diversity: Literal["equilibrada", "exploradora", "foco"] = "equilibrada"

class RatingPayload(BaseModel): rating: int = Field(ge=1, le=5)
class InteractionPayload(BaseModel):
    kind: Literal["view", "hide"]

class ContentPayload(BaseModel):
    title: str = Field(min_length=2, max_length=120); description: str = Field(min_length=10, max_length=500); type: Literal["Filme", "Série", "Música", "Notícia"]; genres: list[str] = Field(min_length=1); language: str = "Português"; year: int | None = None; cover: str = "https://images.unsplash.com/photo-1446776811953-b23d57bd21aa?auto=format&fit=crop&w=900&q=85"

@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield

app = FastAPI(title="SmartRecomenda API", version="0.1.0", description="API de recomendação explicável para o projeto acadêmico SmartRecomenda.", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
if (ROOT / "dist" / "assets").exists():
    app.mount("/assets", StaticFiles(directory=ROOT / "dist" / "assets"), name="assets")

@app.middleware("http")
async def enforce_request_origin(request: Request, call_next):
    if request.method in {"POST", "PUT", "PATCH", "DELETE"} and request.url.path.startswith("/api/v1/"):
        origin = request.headers.get("origin", "").rstrip("/")
        allowed_origins = {item.rstrip("/") for item in CORS_ORIGINS}
        if not origin or origin not in allowed_origins:
            return Response("Origem da solicitação não autorizada.", status_code=403)
    return await call_next(request)

@app.get("/api/v1/auth/config")
def get_auth_config():
    return {"enabled": auth_configured(), "demo_access": DEMO_ACCESS}

@app.get("/api/v1/auth/login")
def auth_login():
    if not auth_configured():
        raise HTTPException(503, "Configure AUTH_CLIENT_ID, AUTH_PORTAL_URL, AUTH_API_URL e AUTH_JWT_SECRET.")
    callback_url = auth_callback_url()
    nonce = secrets.token_urlsafe(32)
    state = encoded_state({"redirectUri": callback_url, "nonce": nonce})
    portal_url = f"{AUTH_PORTAL_URL.rstrip('/')}/app-auth"
    query = urlencode({
        "appId": AUTH_CLIENT_ID,
        "redirectUri": callback_url,
        "state": state,
        "responseType": "code",
    })
    redirect = RedirectResponse(f"{portal_url}?{query}", status_code=302)
    redirect.set_cookie(
        "smartrecomenda_oauth_nonce",
        nonce,
        max_age=AUTH_STATE_SECONDS,
        httponly=True,
        secure=AUTH_COOKIE_SECURE,
        samesite="lax",
        path="/api/v1/auth/callback",
    )
    return redirect

@app.get("/api/v1/auth/callback")
def auth_callback(request: Request, code: str = "", state: str = "", error: str = ""):
    if error:
        raise HTTPException(401, "A autenticação foi cancelada.")
    if not code or not state:
        raise HTTPException(400, "O retorno OAuth não contém código e estado.")
    state_payload = decode_state(state)
    nonce_cookie = request.cookies.get("smartrecomenda_oauth_nonce", "")
    if not nonce_cookie or not secrets.compare_digest(state_payload["nonce"], nonce_cookie):
        raise HTTPException(400, "A validação de estado OAuth falhou.")
    callback_url = auth_callback_url()
    if state_payload["redirectUri"] != callback_url:
        raise HTTPException(400, "O endereço de retorno OAuth não corresponde ao início do login.")

    identity = exchange_auth_code(code, callback_url)
    user_id = identity["openId"]
    name = identity.get("name") if isinstance(identity.get("name"), str) else "Usuário"
    email = identity.get("email") if isinstance(identity.get("email"), str) else None
    provision_user(user_id, name, email)

    now = int(time.time())
    session_token = jwt.encode(
        {"sub": user_id, "appId": AUTH_CLIENT_ID, "iat": now, "exp": now + AUTH_SESSION_SECONDS},
        AUTH_JWT_SECRET,
        algorithm="HS256",
    )
    redirect = RedirectResponse("/", status_code=303)
    redirect.set_cookie(
        AUTH_COOKIE_NAME,
        session_token,
        max_age=AUTH_SESSION_SECONDS,
        httponly=True,
        secure=AUTH_COOKIE_SECURE,
        samesite=AUTH_COOKIE_SAMESITE,
        path="/",
    )
    redirect.delete_cookie(
        "smartrecomenda_oauth_nonce",
        secure=AUTH_COOKIE_SECURE,
        httponly=True,
        samesite="lax",
        path="/api/v1/auth/callback",
    )
    return redirect

@app.get("/api/v1/auth/me")
def auth_me(request: Request, response: Response):
    user_id = current_user(request)
    if getattr(request.state, "demo_fallback", False):
        response.delete_cookie(
            AUTH_COOKIE_NAME,
            secure=AUTH_COOKIE_SECURE,
            httponly=True,
            samesite=AUTH_COOKIE_SAMESITE,
            path="/",
        )
    with db() as connection:
        row = connection.execute("SELECT user_id,name,email,role FROM profiles WHERE user_id=?", (user_id,)).fetchone()
    if not row:
        provision_user(user_id, user_id, None)
        with db() as connection:
            row = connection.execute("SELECT user_id,name,email,role FROM profiles WHERE user_id=?", (user_id,)).fetchone()
    if not row:
        raise HTTPException(500, "Não foi possível provisionar a conta autenticada.")
    user = dict(row)
    user["demo"] = user_id == DEMO_USER
    return user

@app.post("/api/v1/auth/logout")
def auth_logout(response: Response):
    response.delete_cookie(
        AUTH_COOKIE_NAME,
        secure=AUTH_COOKIE_SECURE,
        httponly=True,
        samesite=AUTH_COOKIE_SAMESITE,
        path="/",
    )
    return {"ok": True}

@app.get("/health")
def health(): return {"status": "ok", "service": "smartrecomenda-api", "environment": APP_ENV, "host": APP_HOST, "port": APP_PORT, "data_mode": "demo"}

@app.get("/api/v1/contents")
def list_contents(q: str = "", type: str = "", genre: str = "", offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=50)):
    with db() as connection:
        rows = connection.execute("SELECT * FROM contents ORDER BY featured DESC, popularity DESC").fetchall()
        result = []
        for row in rows:
            haystack = f"{row['title']} {row['description']} {row['type']} {' '.join(json_load(row['genres'], []))}".lower()
            if q.lower() not in haystack or (type and row["type"] != type) or (genre and genre not in json_load(row["genres"], [])): continue
            avg, count = average_rating(connection, row["id"]); item = content_from_row(row, rating=avg); item["rating_count"] = count; result.append(item)
        return {"items": result[offset:offset + limit], "total": len(result), "offset": offset, "limit": limit}

@app.get("/api/v1/contents/{content_id}")
def get_content(content_id: int):
    with db() as connection:
        row = connection.execute("SELECT * FROM contents WHERE id=?", (content_id,)).fetchone()
        if not row: raise HTTPException(404, "Conteúdo não encontrado.")
        avg, count = average_rating(connection, content_id); item = content_from_row(row, rating=avg); item["rating_count"] = count; return item

@app.get("/api/v1/recommendations")
def get_recommendations(request: Request, type: str | None = None, genre: str | None = None, language: str | None = None, limit: int = Query(8, ge=1, le=12)):
    items, strategy = recommendations(current_user(request), limit=limit, item_type=type, genre=genre, language=language)
    return {"items": items, "strategy": strategy, "formula": "0.44E + 0.34H + 0.10Q + 0.12P"}

@app.get("/api/v1/recommendations/{content_id}/explanation")
def explanation(request: Request, content_id: int):
    items, _ = recommendations(current_user(request)); item = next((item for item in items if item["id"] == content_id), None); return {"content_id": content_id, "reason": item["reason"] if item else "Este conteúdo está disponível no catálogo demonstrativo."}

@app.get("/api/v1/preferences")
def get_preferences(request: Request):
    with db() as connection:
        row = connection.execute("SELECT * FROM preferences WHERE user_id=?", (current_user(request),)).fetchone()
        if not row: return demo_prefs()
        return {"types": json_load(row["types"], []), "genres": json_load(row["genres"], []), "languages": json_load(row["languages"], []), "blocked_ids": json_load(row["blocked_ids"], []), "diversity": row["diversity"]}

@app.put("/api/v1/preferences")
def put_preferences(request: Request, payload: PreferencePayload):
    user_id = current_user(request)
    with db() as connection:
        connection.execute("INSERT INTO profiles(user_id,name,email,role) VALUES(?,?,?,?) ON CONFLICT(user_id) DO NOTHING", (user_id, "Usuário demonstrativo", None, "user"))
        connection.execute("INSERT INTO preferences(user_id,types,genres,languages,blocked_ids,diversity) VALUES(?,?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET types=excluded.types,genres=excluded.genres,languages=excluded.languages,blocked_ids=excluded.blocked_ids,diversity=excluded.diversity", (user_id, json.dumps(payload.types), json.dumps(payload.genres), json.dumps(payload.languages), json.dumps(payload.blocked_ids), payload.diversity))
    return payload.model_dump()

@app.get("/api/v1/favorites")
def get_favorites(request: Request):
    with db() as connection:
        rows = connection.execute("SELECT c.* FROM contents c JOIN favorites f ON f.content_id=c.id WHERE f.user_id=? ORDER BY f.created_at DESC", (current_user(request),)).fetchall(); return [content_from_row(row) for row in rows]

@app.post("/api/v1/favorites/{content_id}")
def toggle_favorite(request: Request, content_id: int):
    user_id = current_user(request)
    with db() as connection:
        existing = connection.execute("SELECT 1 FROM favorites WHERE user_id=? AND content_id=?", (user_id, content_id)).fetchone()
        if existing:
            connection.execute("DELETE FROM favorites WHERE user_id=? AND content_id=?", (user_id, content_id))
            state = False
            kind = "unfavorite"
        else:
            connection.execute("INSERT INTO favorites(user_id,content_id) VALUES(?,?)", (user_id, content_id))
            state = True
            kind = "favorite"
        connection.execute("INSERT INTO interactions(user_id,content_id,kind) VALUES(?,?,?)", (user_id, content_id, kind))
        return {"favorite": state}

@app.post("/api/v1/ratings/{content_id}")
def rate(request: Request, content_id: int, payload: RatingPayload):
    with db() as connection:
        if not connection.execute("SELECT 1 FROM contents WHERE id=?", (content_id,)).fetchone(): raise HTTPException(404, "Conteúdo não encontrado.")
        connection.execute("INSERT INTO ratings(user_id,content_id,rating) VALUES(?,?,?) ON CONFLICT(user_id,content_id) DO UPDATE SET rating=excluded.rating,updated_at=CURRENT_TIMESTAMP", (current_user(request), content_id, payload.rating)); connection.execute("INSERT INTO interactions(user_id,content_id,kind) VALUES(?,?,?)", (current_user(request), content_id, "rating")); return {"ok": True, "rating": payload.rating}

@app.post("/api/v1/interactions/{content_id}")
def record_interaction(request: Request, content_id: int, payload: InteractionPayload):
    user_id = current_user(request)
    with db() as connection:
        if not connection.execute("SELECT 1 FROM contents WHERE id=?", (content_id,)).fetchone():
            raise HTTPException(404, "Conteúdo não encontrado.")
        connection.execute(
            "INSERT INTO interactions(user_id,content_id,kind) VALUES(?,?,?)",
            (user_id, content_id, payload.kind),
        )
    return {"ok": True, "kind": payload.kind}

@app.get("/api/v1/interactions")
def get_interactions(request: Request):
    with db() as connection:
        rows = connection.execute("SELECT DISTINCT c.* FROM contents c JOIN interactions i ON i.content_id=c.id WHERE i.user_id=? ORDER BY i.created_at DESC", (current_user(request),)).fetchall(); return [content_from_row(row) for row in rows]

@app.delete("/api/v1/interactions")
def delete_interactions(request: Request):
    with db() as connection: connection.execute("DELETE FROM interactions WHERE user_id=?", (current_user(request),)); return {"ok": True}

@app.get("/api/v1/profile")
def profile(request: Request):
    with db() as connection:
        row = connection.execute("SELECT user_id,name,email,history_enabled,role FROM profiles WHERE user_id=?", (current_user(request),)).fetchone(); return dict(row) if row else {"user_id": current_user(request), "name": "Usuário demonstrativo", "role": "user"}

@app.get("/api/v1/admin/metrics")
def admin_metrics(request: Request):
    if not is_admin(current_user(request)): raise HTTPException(403, "Acesso administrativo necessário.")
    with db() as connection:
        categories = {row["type"]: row["total"] for row in connection.execute("SELECT type,COUNT(*) total FROM contents GROUP BY type").fetchall()}
        top_contents = [
            dict(row)
            for row in connection.execute(
                """
                SELECT c.id,c.title,c.type,
                    (SELECT COUNT(*) FROM interactions i WHERE i.content_id=c.id AND i.kind='view') views,
                    (SELECT COUNT(*) FROM favorites f WHERE f.content_id=c.id) favorites,
                    (SELECT COUNT(*) FROM ratings r WHERE r.content_id=c.id) ratings,
                    (SELECT ROUND(AVG(r.rating),1) FROM ratings r WHERE r.content_id=c.id) average_rating
                FROM contents c
                ORDER BY views DESC,favorites DESC,ratings DESC,c.popularity DESC
                LIMIT 5
                """
            ).fetchall()
        ]
        daily_activity = [
            dict(row)
            for row in connection.execute(
                """
                WITH days AS (
                    SELECT date('now', '-' || n || ' days') day
                    FROM (SELECT 0 n UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3
                          UNION ALL SELECT 4 UNION ALL SELECT 5 UNION ALL SELECT 6)
                )
                SELECT days.day,
                    (SELECT COUNT(*) FROM recommendation_events r WHERE date(r.created_at)=days.day) recommendations,
                    (SELECT COUNT(*) FROM interactions i WHERE date(i.created_at)=days.day) interactions
                FROM days ORDER BY days.day
                """
            ).fetchall()
        ]
        recent_activity = [
            dict(row)
            for row in connection.execute(
                """
                SELECT p.name user_name,c.title content_title,i.kind,i.created_at
                FROM interactions i
                JOIN contents c ON c.id=i.content_id
                LEFT JOIN profiles p ON p.user_id=i.user_id
                ORDER BY i.created_at DESC,i.id DESC
                LIMIT 8
                """
            ).fetchall()
        ]
        return {
            "contents": connection.execute("SELECT COUNT(*) n FROM contents").fetchone()["n"],
            "ratings": connection.execute("SELECT COUNT(*) n FROM ratings").fetchone()["n"],
            "favorites": connection.execute("SELECT COUNT(*) n FROM favorites").fetchone()["n"],
            "active_users": connection.execute(
                "SELECT COUNT(DISTINCT user_id) n FROM interactions WHERE created_at >= datetime('now','-30 days')"
            ).fetchone()["n"],
            "views": connection.execute(
                "SELECT COUNT(*) n FROM interactions WHERE kind='view'"
            ).fetchone()["n"],
            "recommendations": connection.execute(
                "SELECT COUNT(*) n FROM recommendation_events WHERE created_at >= datetime('now','-30 days')"
            ).fetchone()["n"],
            "categories": categories,
            "top_contents": top_contents,
            "daily_activity": daily_activity,
            "recent_activity": recent_activity,
            "strategy": "HybridStrategy",
            "data_label": "Dados demonstrativos fictícios",
        }

@app.post("/api/v1/admin/contents")
def create_content(request: Request, payload: ContentPayload):
    if not is_admin(current_user(request)): raise HTTPException(403, "Acesso administrativo necessário.")
    content_id = int(hashlib.sha256(f"{payload.title}-{time.time()}".encode()).hexdigest()[:8], 16)
    with db() as connection: connection.execute("INSERT INTO contents(id,title,description,type,genres,language,year,cover,popularity,is_demo,featured) VALUES(?,?,?,?,?,?,?,?,?,?,?)", (content_id, payload.title, payload.description, payload.type, json.dumps(payload.genres), payload.language, payload.year, payload.cover, 0.5, 1, 0)); row = connection.execute("SELECT * FROM contents WHERE id=?", (content_id,)).fetchone(); return content_from_row(row)

@app.get("/", include_in_schema=False)
def serve_app():
    built = ROOT / "dist" / "index.html"
    return FileResponse(built) if built.exists() else {"message": "SmartRecomenda API ativa. Execute pnpm build para servir o frontend."}

@app.get("/manus-routes.json", include_in_schema=False)
def route_manifest():
    manifest = ROOT / "dist" / "manus-routes.json"
    return FileResponse(manifest, media_type="application/json") if manifest.exists() else {"routes": []}

@app.get("/{path:path}", include_in_schema=False)
def spa_fallback(path: str):
    if path.startswith(("api/", "docs", "openapi.json", "health", "assets/", "manus-routes.json")): raise HTTPException(404, "Rota não encontrada.")
    built = ROOT / "dist" / "index.html"
    return FileResponse(built) if built.exists() else {"message": "Frontend ainda não compilado."}
