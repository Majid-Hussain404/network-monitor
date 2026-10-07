from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def home():
    return {"message": "Network Monitor is running"}