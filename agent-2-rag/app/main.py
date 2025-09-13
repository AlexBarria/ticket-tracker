from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from graph_processor import AgentPipeline
import jwt

agent_pipeline = AgentPipeline()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI(title="Agent 2 - RAG")


def get_user_role(token: str = Depends(oauth2_scheme)):
    """Decodes the JWT to get the user ID ('sub')."""
    try:
        # For simplicity, we decode without full verification here.
        # In production, you should verify the token signature against Auth0's public key.
        payload = jwt.decode(token, options={"verify_signature": False})
        user_name = payload.get("name", "User")
        if user_name is None:
            raise HTTPException(status_code=401, detail="Invalid token: user ID not found")
        namespace = 'https://ticket-tracker.com'
        return payload.get(f'{namespace}/roles', [])
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")


@app.get("/")
def read_root():
    # Health check endpoint
    return {"status": "ok", "service": "Agent 2 - RAG"}


@app.post("/ask")
def ask(query: dict, user_role: str = Depends(get_user_role)):
    if 'admin' not in user_role:
        raise HTTPException(status_code=403, detail="You do not have permission to access this resource.")
    try:
        question = query.get("query")
        if not question:
            raise HTTPException(status_code=400, detail="Query parameter is required.")
        answer = agent_pipeline.run(question)
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")
