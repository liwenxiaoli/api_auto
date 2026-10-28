from common.client import HttpClient
from config.settings import BASE_URL, TIMEOUT

http = HttpClient(BASE_URL, TIMEOUT)     # ← 造对象（conftest 里替你干的那件事）
print(http.base_url,http.timeout)

resp = http.get("/products/1")
print(resp.status_code)
print(resp.json()["title"])

http.close()