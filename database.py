import sqlite3
import hashlib
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "motores.db"


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS ativos (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ativo_id    TEXT UNIQUE NOT NULL,
                descricao   TEXT,
                localizacao TEXT,
                criado_em   TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS leituras (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                ativo_id        TEXT NOT NULL,
                fonte           TEXT DEFAULT 'esp32',
                temperatura_c   REAL,
                vibracao_mm_s   REAL,
                corrente_a      REAL,
                tensao_v        REAL,
                rpm             REAL,
                fator_potencia  REAL,
                coletado_em     TEXT,
                processado_em   TEXT DEFAULT (datetime('now')),
                flag_anomalia   INTEGER DEFAULT 0,
                hash_registro   TEXT,
                ax_rms          REAL,
                ay_rms          REAL,
                az_rms          REAL,
                mag_rms         REAL,
                freq_hz         REAL,
                gx_rms          REAL,
                gy_rms          REAL,
                gz_rms          REAL,
                peaks           TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_leituras_ativo
                ON leituras(ativo_id, coletado_em);
        """)


def cadastrar_ativo(ativo_id: str, descricao: str = "", localizacao: str = "") -> bool:
    """Insere ativo se não existir. Retorna True se criado, False se já existia."""
    with _connect() as conn:
        try:
            conn.execute(
                "INSERT INTO ativos (ativo_id, descricao, localizacao) VALUES (?, ?, ?)",
                (ativo_id, descricao, localizacao),
            )
            return True
        except sqlite3.IntegrityError:
            return False


def get_ativos() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM ativos ORDER BY criado_em").fetchall()
    return [dict(r) for r in rows]


def get_leituras(ativo_id: str | None = None, limit: int = 500) -> list[dict]:
    with _connect() as conn:
        if ativo_id:
            rows = conn.execute(
                "SELECT * FROM leituras WHERE ativo_id = ? ORDER BY coletado_em DESC LIMIT ?",
                (ativo_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM leituras ORDER BY coletado_em DESC LIMIT ?",
                (limit,),
            ).fetchall()
    return [dict(r) for r in rows]


def insert_leitura(ativo_id: str, dados: dict) -> int:
    payload = json.dumps({**dados, "ativo_id": ativo_id}, sort_keys=True, default=str)
    hash_reg = hashlib.sha256(payload.encode()).hexdigest()

    cols = [
        "ativo_id", "fonte", "temperatura_c", "vibracao_mm_s", "corrente_a",
        "tensao_v", "rpm", "fator_potencia", "coletado_em", "flag_anomalia",
        "hash_registro", "ax_rms", "ay_rms", "az_rms", "mag_rms",
        "freq_hz", "gx_rms", "gy_rms", "gz_rms", "peaks",
    ]
    values = [
        ativo_id,
        dados.get("fonte", "esp32"),
        dados.get("temperatura_c"),
        dados.get("vibracao_mm_s"),
        dados.get("corrente_a"),
        dados.get("tensao_v"),
        dados.get("rpm"),
        dados.get("fator_potencia"),
        dados.get("coletado_em", datetime.utcnow().isoformat()),
        dados.get("flag_anomalia", 0),
        hash_reg,
        dados.get("ax_rms"),
        dados.get("ay_rms"),
        dados.get("az_rms"),
        dados.get("mag_rms"),
        dados.get("freq_hz"),
        dados.get("gx_rms"),
        dados.get("gy_rms"),
        dados.get("gz_rms"),
        json.dumps(dados.get("peaks", [])),
    ]

    placeholders = ", ".join(["?"] * len(cols))
    col_names = ", ".join(cols)

    with _connect() as conn:
        cur = conn.execute(
            f"INSERT INTO leituras ({col_names}) VALUES ({placeholders})", values
        )
        return cur.lastrowid


init_db()
