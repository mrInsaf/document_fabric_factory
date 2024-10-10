import json

from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import aiosqlite
import os

from starlette.responses import FileResponse

from misc import add_qr_to_docx

app = FastAPI()

# Добавляем поддержку CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Разрешённые источники
    allow_credentials=True,
    allow_methods=["*"],  # Разрешить все методы
    allow_headers=["*"],  # Разрешить все заголовки
)


# Создаем и подключаемся к базе данных SQLite
DATABASE = "documents.db"

# Папка для хранения загружаемых файлов
UPLOAD_FOLDER = "files/upload"
PROCESSED_FOLDER = "files/processed"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Создаем папку, если её нет
os.makedirs(PROCESSED_FOLDER, exist_ok=True)  # Создаем папку, если её нет


async def init_db():
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute(""" 
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                qr_code_data TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()


@app.on_event("startup")
async def startup():
    await init_db()


@app.post("/api/documents")
async def create_document(
        title: str = Form(...),
        description: str = Form(...),
        file: UploadFile = File(...)
):
    file_location = os.path.join(UPLOAD_FOLDER, file.filename)
    with open(file_location, "wb") as file_object:
        file_object.write(await file.read())

    data_dict = {
        "title": title,
        "description": description
    }
    qr_data = json.dumps(data_dict)
    output_path = add_qr_to_docx(file_location, qr_data, PROCESSED_FOLDER, file.filename)

    async with aiosqlite.connect(DATABASE) as db:
        try:
            query = """
                INSERT INTO documents (title, description)
                VALUES (?, ?)
            """
            await db.execute(query, (title, description))
            await db.commit()
            return FileResponse(output_path)
        except Exception as e:
            print(e)
            raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=5000)
