"""Local deterministic chatbot fixture; never use it to assess model quality."""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

ANSWERS = {"What is the capital of France?": "Paris is the capital of France.",
           "What is two plus two?": "Two plus two is four."}


class Handler(BaseHTTPRequestHandler):
    # Purpose: return fixed answers independently of evaluation ground truths.
    def do_POST(self):
        request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        response = json.dumps({"response": ANSWERS.get(request.get("question"), "I do not know.")}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)


if __name__ == "__main__":
    print("Demo chatbot listening at http://127.0.0.1:8765/chat", flush=True)
    HTTPServer(("127.0.0.1", 8765), Handler).serve_forever()
