import json
import hashlib
import logging
import os
import secrets
import sqlite3
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

try:
    from app.optimizer.packing import Box, optimize_packing
except ModuleNotFoundError:  # pragma: no cover
    from optimizer.packing import Box, optimize_packing

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from openpyxl import Workbook, load_workbook
from pydantic import BaseModel

logger = logging.getLogger("warehouse_optimizer")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


class Package(BaseModel):
    name: str
    length: float
    width: float
    height: float
    quantity: int


class OptimizationRequest(BaseModel):
    room_length: float
    room_width: float
    room_height: float
    packages: list[Package]


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    password_confirmation: str


class AuthService:
    SESSION_COOKIE = "warehouse_session"
    _sessions: dict[str, str] = {}

    @classmethod
    def login(cls, username: str, password: str) -> str | None:
        expected_username = os.getenv("WAREHOUSE_ADMIN_USER", "admin")
        expected_password = os.getenv("WAREHOUSE_ADMIN_PASSWORD", "admin")
        if secrets.compare_digest(username, expected_username) and secrets.compare_digest(password, expected_password):
            admin_id = UserService.ensure_user(username, password)
            OptimizationHistoryService.claim_unowned_runs(admin_id)
            token = secrets.token_urlsafe(32)
            cls._sessions[token] = username
            return token

        if not UserService.authenticate(username, password):
            return None

        token = secrets.token_urlsafe(32)
        cls._sessions[token] = username
        return token

    @classmethod
    def is_authenticated(cls, token: str | None) -> bool:
        return bool(token and token in cls._sessions)

    @classmethod
    def username(cls, token: str | None) -> str | None:
        return cls._sessions.get(token) if token else None

    @classmethod
    def logout(cls, token: str | None) -> None:
        if token:
            cls._sessions.pop(token, None)


class ExcelImportService:
    @staticmethod
    def _to_float(value):
        if value is None:
            return 0.0
        if isinstance(value, str):
            value = value.strip().replace(",", ".")
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _normalize(value):
        if value is None:
            return ""
        return str(value).strip().lower().replace(" ", "_")

    @staticmethod
    def build_template_workbook() -> BytesIO:
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Warehouse"
        sheet.append(["room_length", "room_width", "room_height"])
        sheet.append([1000, 800, 300])
        sheet.append([])
        sheet.append(["name", "length", "width", "height", "quantity"])
        sheet.append(["Karton A", 120, 60, 50, 12])
        sheet.append(["Karton B", 80, 50, 40, 20])
        sheet.append(["Paczka C", 60, 40, 30, 35])
        for column_cells in sheet.columns:
            max_length = max(len(str(cell.value)) if cell.value is not None else 0 for cell in column_cells)
            sheet.column_dimensions[column_cells[0].column_letter].width = max_length + 2
        buffer = BytesIO()
        workbook.save(buffer)
        buffer.seek(0)
        return buffer

    @staticmethod
    def parse_excel(file_bytes: bytes) -> dict:
        workbook = load_workbook(filename=BytesIO(file_bytes), read_only=True, data_only=True)
        sheet = workbook.active
        rows = list(sheet.iter_rows(values_only=True))

        if not rows:
            raise ValueError("Excel jest pusty.")

        room = {}
        for index, row in enumerate(rows):
            normalized = [ExcelImportService._normalize(value) for value in row]
            label_positions = {
                key: position
                for position, key in enumerate(normalized)
                if key in {"room_length", "room_width", "room_height"}
            }
            if not label_positions:
                continue
            next_row = rows[index + 1] if index + 1 < len(rows) else []
            for key, position in label_positions.items():
                if position < len(next_row) and next_row[position] not in (None, ""):
                    room[key] = ExcelImportService._to_float(next_row[position])
            if room:
                break

        if not room:
            room_values = []
            for row in rows[:3]:
                room_values.extend(
                    ExcelImportService._to_float(value)
                    for value in row[:3]
                    if value not in (None, "")
                )
            if len(room_values) >= 3:
                room = {
                    "room_length": room_values[0],
                    "room_width": room_values[1],
                    "room_height": room_values[2],
                }

        if not room:
            raise ValueError("Nie znaleziono wymiarów magazynu w pliku Excel.")

        package_rows = []
        header_positions = {}
        for index, row in enumerate(rows):
            normalized = [ExcelImportService._normalize(value) for value in row]
            if any(value in {"name", "length", "width", "height", "quantity"} for value in normalized):
                header_positions = {
                    key: position
                    for position, key in enumerate(normalized)
                    if key in {"name", "length", "width", "height", "quantity"}
                }
                for package_index in range(index + 1, len(rows)):
                    package_row = rows[package_index]
                    if not package_row or all(value in (None, "") for value in package_row):
                        continue
                    name_value = package_row[header_positions.get("name", 0)] if "name" in header_positions and header_positions["name"] < len(package_row) else ""
                    length_value = package_row[header_positions.get("length", 1)] if "length" in header_positions and header_positions["length"] < len(package_row) else 0
                    width_value = package_row[header_positions.get("width", 2)] if "width" in header_positions and header_positions["width"] < len(package_row) else 0
                    height_value = package_row[header_positions.get("height", 3)] if "height" in header_positions and header_positions["height"] < len(package_row) else 0
                    quantity_value = package_row[header_positions.get("quantity", 4)] if "quantity" in header_positions and header_positions["quantity"] < len(package_row) else 1
                    if name_value in (None, ""):
                        continue
                    package_rows.append(
                        {
                            "name": str(name_value).strip(),
                            "length": ExcelImportService._to_float(length_value),
                            "width": ExcelImportService._to_float(width_value),
                            "height": ExcelImportService._to_float(height_value),
                            "quantity": int(ExcelImportService._to_float(quantity_value) or 1),
                        }
                    )
                break

        if not package_rows:
            package_rows = []

        return {
            "room_length": room.get("room_length") or 0,
            "room_width": room.get("room_width") or 0,
            "room_height": room.get("room_height") or 0,
            "packages": package_rows,
        }


class ExcelExportService:
    @staticmethod
    def build_run_workbook(item: dict) -> Workbook:
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Optimization"

        request = json.loads(item.get("request_json") or "{}")
        result = json.loads(item.get("result_json") or "{}")
        placed_boxes = result.get("placed_boxes") or []
        packages = request.get("packages") or []

        metadata = [
            ["Run ID", item.get("id")],
            ["Created at", item.get("created_at")],
            ["room_length", item.get("room_length")],
            ["room_width", item.get("room_width")],
            ["room_height", item.get("room_height")],
            ["package_count", item.get("package_count")],
            ["placed_count", item.get("placed_count")],
            ["not_placed_count", item.get("not_placed_count")],
            ["utilization", item.get("utilization")],
        ]
        for row in metadata:
            sheet.append(row)

        sheet.append([])
        sheet.append(["request", "value"])
        sheet.append(["room_length", request.get("room_length")])
        sheet.append(["room_width", request.get("room_width")])
        sheet.append(["room_height", request.get("room_height")])

        sheet.append([])
        sheet.append(["name", "length", "width", "height", "quantity"])
        for package in packages:
            sheet.append([
                package.get("name", ""),
                package.get("length", 0),
                package.get("width", 0),
                package.get("height", 0),
                package.get("quantity", 1),
            ])

        sheet.append([])
        sheet.append(["Optimization summary", ""])
        sheet.append(["placed", result.get("optimization", {}).get("placed")])
        sheet.append(["not_placed", result.get("optimization", {}).get("not_placed")])
        sheet.append(["utilization", result.get("optimization", {}).get("utilization")])

        sheet.append([])
        sheet.append(["name", "length", "width", "height", "x", "y", "z"])
        for box in placed_boxes:
            sheet.append([
                box.get("name", ""),
                box.get("length", 0),
                box.get("width", 0),
                box.get("height", 0),
                box.get("x", 0),
                box.get("y", 0),
                box.get("z", 0),
            ])

        for column_cells in sheet.columns:
            max_length = max(len(str(cell.value)) if cell.value is not None else 0 for cell in column_cells)
            sheet.column_dimensions[column_cells[0].column_letter].width = max_length + 2

        return workbook

    @staticmethod
    def build_run_buffer(item: dict) -> BytesIO:
        workbook = ExcelExportService.build_run_workbook(item)
        buffer = BytesIO()
        workbook.save(buffer)
        buffer.seek(0)
        return buffer


class OptimizationService:
    @staticmethod
    def build_boxes(packages: list[Package]) -> list[Box]:
        return [
            Box(
                name=package.name,
                length=package.length,
                width=package.width,
                height=package.height,
                quantity=package.quantity,
            )
            for package in packages
        ]

    @staticmethod
    def calculate_result(data: OptimizationRequest) -> dict:
        boxes = OptimizationService.build_boxes(data.packages)
        placed, not_placed = optimize_packing(
            room_length=data.room_length,
            room_width=data.room_width,
            room_height=data.room_height,
            boxes=boxes,
        )

        room_volume = (
            data.room_length * data.room_width * data.room_height / 1_000_000
        )
        placed_volume = sum(
            box.length * box.width * box.height / 1_000_000 for box in placed
        )
        utilization = (
            (placed_volume / room_volume) * 100 if room_volume > 0 else 0
        )

        return {
            "success": True,
            "room": {
                "length": data.room_length,
                "width": data.room_width,
                "height": data.room_height,
                "volume": round(room_volume, 3),
            },
            "optimization": {
                "placed": len(placed),
                "not_placed": len(not_placed),
                "utilization": round(utilization, 2),
            },
            "placed_boxes": [
                {
                    "name": box.name,
                    "length": box.length,
                    "width": box.width,
                    "height": box.height,
                    "x": box.x,
                    "y": box.y,
                    "z": box.z,
                }
                for box in placed
            ],
            "not_placed_boxes": not_placed,
        }


class OptimizationHistoryService:
    DB_PATH = Path(
        os.getenv(
            "WAREHOUSE_DB_PATH",
            str(Path(__file__).resolve().parent / "warehouse_history.db"),
        )
    )

    @staticmethod
    def _connect() -> sqlite3.Connection:
        connection = sqlite3.connect(OptimizationHistoryService.DB_PATH)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _ensure_schema() -> None:
        with OptimizationHistoryService._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS optimization_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    room_length REAL NOT NULL,
                    room_width REAL NOT NULL,
                    room_height REAL NOT NULL,
                    package_count INTEGER NOT NULL,
                    placed_count INTEGER NOT NULL,
                    not_placed_count INTEGER NOT NULL,
                    utilization REAL NOT NULL,
                    request_json TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    user_id INTEGER
                )
                """
            )
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(optimization_runs)").fetchall()
            }
            if "user_id" not in columns:
                connection.execute("ALTER TABLE optimization_runs ADD COLUMN user_id INTEGER")

    @staticmethod
    def save_run(request: OptimizationRequest, result: dict, user_id: int | None = None) -> int:
        OptimizationHistoryService._ensure_schema()
        optimization = result.get("optimization", {})
        payload = request.model_dump()
        created_at = datetime.now(timezone.utc).isoformat()

        with OptimizationHistoryService._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO optimization_runs (
                    created_at,
                    room_length,
                    room_width,
                    room_height,
                    package_count,
                    placed_count,
                    not_placed_count,
                    utilization,
                    request_json,
                    result_json,
                    user_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    created_at,
                    request.room_length,
                    request.room_width,
                    request.room_height,
                    len(request.packages),
                    optimization.get("placed", 0),
                    optimization.get("not_placed", 0),
                    float(optimization.get("utilization", 0) or 0),
                    json.dumps(payload),
                    json.dumps(result),
                    user_id,
                ),
            )
            return int(cursor.lastrowid)

    @staticmethod
    def list_recent(limit: int = 20, user_id: int | None = None) -> list[dict]:
        OptimizationHistoryService._ensure_schema()
        with OptimizationHistoryService._connect() as connection:
            if user_id is None:
                rows = connection.execute(
                    "SELECT * FROM optimization_runs ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM optimization_runs WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
                    (user_id, limit),
                ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def get_run(run_id: int, user_id: int | None = None) -> dict | None:
        OptimizationHistoryService._ensure_schema()
        with OptimizationHistoryService._connect() as connection:
            if user_id is None:
                row = connection.execute("SELECT * FROM optimization_runs WHERE id = ?", (run_id,)).fetchone()
            else:
                row = connection.execute(
                    "SELECT * FROM optimization_runs WHERE id = ? AND user_id = ?",
                    (run_id, user_id),
                ).fetchone()
        if row is None:
            return None
        return dict(row)

    @staticmethod
    def claim_unowned_runs(user_id: int) -> None:
        OptimizationHistoryService._ensure_schema()
        with OptimizationHistoryService._connect() as connection:
            connection.execute(
                "UPDATE optimization_runs SET user_id = ? WHERE user_id IS NULL",
                (user_id,),
            )


class UserService:
    DB_PATH = OptimizationHistoryService.DB_PATH
    ITERATIONS = 310_000

    @classmethod
    def _connect(cls) -> sqlite3.Connection:
        connection = sqlite3.connect(cls.DB_PATH)
        connection.row_factory = sqlite3.Row
        return connection

    @classmethod
    def _ensure_schema(cls) -> None:
        with cls._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

    @classmethod
    def _hash_password(cls, password: str, salt: bytes | None = None) -> str:
        salt = salt or secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            cls.ITERATIONS,
        )
        return f"{salt.hex()}${digest.hex()}"

    @classmethod
    def register(cls, username: str, password: str) -> bool:
        cls._ensure_schema()
        with cls._connect() as connection:
            try:
                connection.execute(
                    "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                    (username, cls._hash_password(password), datetime.now(timezone.utc).isoformat()),
                )
            except sqlite3.IntegrityError:
                return False
        return True

    @classmethod
    def authenticate(cls, username: str, password: str) -> bool:
        cls._ensure_schema()
        with cls._connect() as connection:
            row = connection.execute(
                "SELECT password_hash FROM users WHERE username = ?",
                (username,),
            ).fetchone()
        if row is None:
            return False

        salt_hex, digest_hex = row["password_hash"].split("$", 1)
        expected = bytes.fromhex(digest_hex)
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            cls.ITERATIONS,
        )
        return secrets.compare_digest(actual, expected)

    @classmethod
    def ensure_user(cls, username: str, password: str) -> int:
        cls._ensure_schema()
        with cls._connect() as connection:
            row = connection.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
            if row is not None:
                return int(row["id"])
        cls.register(username, password)
        return cls.get_id(username)

    @classmethod
    def get_id(cls, username: str) -> int:
        cls._ensure_schema()
        with cls._connect() as connection:
            row = connection.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if row is None:
            raise ValueError(f"Nie znaleziono użytkownika: {username}")
        return int(row["id"])


class WarehouseAppFactory:
    @staticmethod
    def create_app() -> FastAPI:
        app = FastAPI(title="WarehouseOptimizer")
        base_dir = Path(__file__).resolve().parent

        app.mount(
            "/static",
            StaticFiles(directory=str(base_dir / "static")),
            name="static",
        )
        templates = Jinja2Templates(directory=str(base_dir / "templates"))

        @app.get("/", response_class=HTMLResponse)
        async def home(request: Request):
            return templates.TemplateResponse(
                request=request,
                name="index.html",
                context={},
            )

        def require_authentication(request: Request) -> int:
            token = request.cookies.get(AuthService.SESSION_COOKIE)
            if not AuthService.is_authenticated(token):
                raise HTTPException(status_code=401, detail="Wymagane logowanie.")
            username = AuthService.username(token)
            if username is None:
                raise HTTPException(status_code=401, detail="Wymagane logowanie.")
            return UserService.get_id(username)

        @app.post("/api/login")
        async def login(data: LoginRequest):
            token = AuthService.login(data.username, data.password)
            if token is None:
                raise HTTPException(status_code=401, detail="Nieprawidłowy login lub hasło.")

            response = JSONResponse({"success": True, "username": data.username})
            response.set_cookie(
                AuthService.SESSION_COOKIE,
                token,
                httponly=True,
                samesite="lax",
                max_age=60 * 60 * 8,
            )
            return response

        @app.post("/api/register", status_code=201)
        async def register(data: RegisterRequest):
            username = data.username.strip()
            if len(username) < 3:
                raise HTTPException(status_code=400, detail="Login musi mieć co najmniej 3 znaki.")
            if len(data.password) < 8:
                raise HTTPException(status_code=400, detail="Hasło musi mieć co najmniej 8 znaków.")
            if data.password != data.password_confirmation:
                raise HTTPException(status_code=400, detail="Hasła nie są takie same.")
            if not UserService.register(username, data.password):
                raise HTTPException(status_code=409, detail="Taki login już istnieje.")
            return {"success": True}

        @app.post("/api/logout")
        async def logout(request: Request):
            AuthService.logout(request.cookies.get(AuthService.SESSION_COOKIE))
            response = JSONResponse({"success": True})
            response.delete_cookie(AuthService.SESSION_COOKIE)
            return response

        @app.get("/api/session")
        async def session(request: Request):
            user_id = require_authentication(request)
            return {"success": True, "user_id": user_id}

        @app.get("/api/optimizations")
        async def list_optimizations(request: Request, limit: int = 20):
            user_id = require_authentication(request)
            logger.info("Requested optimization history with limit=%s", limit)
            return {"success": True, "items": OptimizationHistoryService.list_recent(limit, user_id)}

        @app.get("/api/optimizations/{run_id}")
        async def get_optimization(request: Request, run_id: int):
            user_id = require_authentication(request)
            logger.info("Requested optimization detail for run_id=%s", run_id)
            item = OptimizationHistoryService.get_run(run_id, user_id)
            if item is None:
                raise HTTPException(status_code=404, detail="Nie znaleziono optymalizacji.")
            return {"success": True, "item": item}

        @app.get("/api/optimizations/{run_id}/excel")
        async def export_optimization_excel(request: Request, run_id: int):
            user_id = require_authentication(request)
            logger.info("Exporting optimization Excel for run_id=%s", run_id)
            item = OptimizationHistoryService.get_run(run_id, user_id)
            if item is None:
                raise HTTPException(status_code=404, detail="Nie znaleziono optymalizacji.")

            workbook = ExcelExportService.build_run_buffer(item)
            return StreamingResponse(
                workbook,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f'attachment; filename="optimization_run_{run_id}.xlsx"'},
            )

        @app.get("/api/excel-template")
        async def excel_template(request: Request):
            require_authentication(request)
            logger.info("Generating Excel template")
            template = ExcelImportService.build_template_workbook()
            return StreamingResponse(
                template,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": 'attachment; filename="warehouse_template.xlsx"'},
            )

        @app.post("/api/excel-import")
        async def excel_import(request: Request, file: UploadFile = File(...)):
            require_authentication(request)
            if not file.filename or not file.filename.lower().endswith((".xlsx", ".xlsm", ".xls")):
                logger.warning("Rejected invalid file upload: %s", file.filename)
                raise HTTPException(status_code=400, detail="Dozwolone są tylko pliki Excel (.xlsx, .xlsm, .xls).")
            try:
                logger.info("Importing Excel file: %s", file.filename)
                data = ExcelImportService.parse_excel(await file.read())
                logger.info("Excel import successful: room=%s x %s x %s, packages=%s", data.get("room_length"), data.get("room_width"), data.get("room_height"), len(data.get("packages", [])))
            except Exception as exc:  # pragma: no cover - runtime validation path
                logger.exception("Excel import failed for file=%s", file.filename)
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            return {"success": True, "data": data}

        @app.post("/api/optimize")
        async def optimize(request: Request, data: OptimizationRequest):
            user_id = require_authentication(request)
            logger.info(
                "Optimization requested: room=%sx%sx%s packages=%s",
                data.room_length,
                data.room_width,
                data.room_height,
                len(data.packages),
            )
            result = OptimizationService.calculate_result(data)
            run_id = OptimizationHistoryService.save_run(data, result, user_id)
            result["run_id"] = run_id
            logger.info("Optimization saved in history with run_id=%s", run_id)
            return result

        return app


app = WarehouseAppFactory.create_app()