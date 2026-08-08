from fastapi import FastAPI

app = FastAPI()

class ProjectService:
    def summarize(self, name: str) -> str:
        return name.strip()

def normalize_project_name(value: str) -> str:
    return value.strip().lower()

@app.get("/api/projects")
def list_projects() -> dict:
    return {"items": []}

@app.post("/api/projects/{project_id}/review")
def review_project(project_id: str) -> dict:
    return {"project_id": project_id, "status": "reviewed"}

def intentionally_risky_expression(value: str):
    return eval(value)
