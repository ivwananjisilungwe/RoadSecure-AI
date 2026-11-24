from app import app
c=app.test_client()
for p in ['/', '/events', '/simulate', '/incidents', '/evaluation', '/api/summary']:
 r=c.get(p); assert r.status_code==200,(p,r.status_code)
print('PASS: all primary pages and JSON API return HTTP 200')
