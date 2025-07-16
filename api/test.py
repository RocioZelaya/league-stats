from http.server import BaseHTTPRequestHandler

def handler(request, response):
    response.status_code = 200
    response.headers['Content-Type'] = 'text/plain'
    response.send('Hello from Vercel!')
