import requests, json, time
# from dataingestion.web.rest import service_rest

data = {}
data['values']  = "{'RightsLicense': 'CC0', 'CSVfilePath': '/home/suresh/Desktop/Plants_1/media_records.csv'}"
url = 'http://127.0.0.1:32601/services/ingest'
r = requests.post(url, data=data)
print json.dumps(data)
print r.text
