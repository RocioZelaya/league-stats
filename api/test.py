# api/test.py

def handler(request, response):
    """
    Vercel serverless function handler for a simple text response.
    """
    response.status_code = 200
    response.headers['Content-Type'] = 'text/plain'
    response.send("Hello from Vercel! (Corrected)")
