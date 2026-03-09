import urllib.request
import json

base = 'http://localhost/api/v1'

# Login
req = urllib.request.Request(f'{base}/auth/login', data=b'username=admin@attendance.local&password=changeme123', headers={'Content-Type': 'application/x-www-form-urlencoded'})
res = urllib.request.urlopen(req)
token = json.loads(res.read())['access_token']

headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
emps = [
    {"rfid_uid":"CC8899AA","name":"Sarah Jenkins","email":"s.jenkins@sentinel.com","department":"Engineering","position":"Senior Developer","phone":"+15550101"},
    {"rfid_uid":"BB776655","name":"David Chen","email":"d.chen@sentinel.com","department":"Operations","position":"Operations Manager","phone":"+15550102"},
    {"rfid_uid":"AA554433","name":"Emily Roberts","email":"e.roberts@sentinel.com","department":"Human Resources","position":"HR Specialist","phone":"+15550103"}
]

for e in emps:
    req = urllib.request.Request(f'{base}/employees', data=json.dumps(e).encode(), headers=headers)
    res = urllib.request.urlopen(req)
    print(res.status, res.read())
