import requests

url = "https://dfsrioreporting.doverfs.com/ctrlproducao/pt/helpdeskconsultax.asp"
data = {
    "calend1": "01/01/2025",
    "calend2": "31/01/2025",
    "nf": "SIM",
    "excel": "SIM"
}
headers = {
    "Host": "evil.com",  # Test with a non-standard host
    "User-Agent": "Mozilla/5.0",
    "Content-Type": "application/x-www-form-urlencoded"
}
response = requests.post(url, headers=headers, data=data, verify=True)
print(response.status_code)
print(response.text[:500])  # Print first 500 chars of response