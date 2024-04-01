import requests

url = 'http://192.168.19.130:8000/page-babo.php'

cookies = {'user':'babo_dg'}

response = requests.post(url, cookies=cookies, allow_redirects=False)
print(response.status_code)
print(response.text)
