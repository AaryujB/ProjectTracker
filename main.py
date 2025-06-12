# main.py - FastAPI Backend
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import uuid
import os
from datetime import datetime
from typing import Optional, List

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Database setup
def init_db():
    conn = sqlite3.connect('projects.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            client TEXT NOT NULL,
            assignee TEXT NOT NULL,
            status TEXT NOT NULL,
            description TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()


init_db()


# Pydantic models
class ProjectCreate(BaseModel):
    name: str
    client: str
    assignee: str
    status: str = "Planning"
    description: Optional[str] = ""


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    client: Optional[str] = None
    assignee: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None


class Project(BaseModel):
    id: str
    name: str
    client: str
    assignee: str
    status: str
    description: str
    created_at: str
    updated_at: str


# Database helpers
def get_db_connection():
    conn = sqlite3.connect('projects.db')
    conn.row_factory = sqlite3.Row
    return conn


# API Routes
@app.post("/api/projects", response_model=Project)
async def create_project(project: ProjectCreate):
    project_id = str(uuid.uuid4())
    now = datetime.now().isoformat()

    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO projects (id, name, client, assignee, status, description, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (project_id, project.name, project.client, project.assignee,
          project.status, project.description or "", now, now))
    conn.commit()
    conn.close()

    return Project(
        id=project_id,
        name=project.name,
        client=project.client,
        assignee=project.assignee,
        status=project.status,
        description=project.description or "",
        created_at=now,
        updated_at=now
    )


@app.get("/api/projects", response_model=List[Project])
async def get_projects():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM projects ORDER BY updated_at DESC')
    rows = c.fetchall()
    conn.close()

    return [Project(**dict(row)) for row in rows]


@app.get("/api/projects/{project_id}", response_model=Project)
async def get_project(project_id: str):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM projects WHERE id = ?', (project_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Project not found")

    return Project(**dict(row))


@app.put("/api/projects/{project_id}", response_model=Project)
async def update_project(project_id: str, project_update: ProjectUpdate):
    conn = get_db_connection()
    c = conn.cursor()

    # Get existing project
    c.execute('SELECT * FROM projects WHERE id = ?', (project_id,))
    existing = c.fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="Project not found")

    # Update fields
    updates = {}
    if project_update.name is not None:
        updates['name'] = project_update.name
    if project_update.client is not None:
        updates['client'] = project_update.client
    if project_update.assignee is not None:
        updates['assignee'] = project_update.assignee
    if project_update.status is not None:
        updates['status'] = project_update.status
    if project_update.description is not None:
        updates['description'] = project_update.description

    updates['updated_at'] = datetime.now().isoformat()

    if updates:
        set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [project_id]
        c.execute(f'UPDATE projects SET {set_clause} WHERE id = ?', values)
        conn.commit()

    # Return updated project
    c.execute('SELECT * FROM projects WHERE id = ?', (project_id,))
    row = c.fetchone()
    conn.close()

    return Project(**dict(row))


@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('DELETE FROM projects WHERE id = ?', (project_id,))
    if c.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Project not found")
    conn.commit()
    conn.close()
    return {"message": "Project deleted"}


# Create static directory if it doesn't exist
os.makedirs("static", exist_ok=True)

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def serve_frontend():
    return FileResponse("static/index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)