# api/test.py

def handler(request):
    """
    Vercel serverless function handler.
    This version returns a dictionary that Vercel converts into an HTTP response.
    """
    # The 'request' object here is a Vercel-specific object
    # It contains information like request.method, request.headers, request.query (for query parameters)

    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'text/plain',
            # Add CORS headers if your Neocities page is on a different domain
            'Access-Control-Allow-Origin': '*', # Adjust to your Neocities domain for production
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
        },
        'body': 'Hello from Vercel! (This one should work!)'
    }
