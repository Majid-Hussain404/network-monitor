from fastapi import FastAPI

from backend.checks import check_http, check_port, get_system_metrics, ping_host

app = FastAPI()


@app.get("/")
def home():
    return {"message": "Network Monitor is running"}


@app.get("/ping/{host}")
def ping(host: str):
    return ping_host(host)


@app.get("/http-check")
def http_check(url: str):
    return check_http(url)


@app.get("/port-check")
def port_check(host: str, port: int):
    return check_port(host, port)


@app.get("/system")
def system():
    return get_system_metrics()