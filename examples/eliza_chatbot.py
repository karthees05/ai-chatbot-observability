"""HTTP adapter for NLTK's open-source ELIZA; no dataset or expected answers are loaded."""
import argparse
import json
import random
from http.server import BaseHTTPRequestHandler, HTTPServer
from nltk.chat.eliza import eliza_chatbot


class ElizaHandler(BaseHTTPRequestHandler):
    # Purpose: expose the actual NLTK conversational algorithm through both supported HTTP protocols.
    def do_POST(self):
        if self.path not in {"/chat", "/v1/chat/completions"}:
            self.send_error(404)
            return
        try:
            payload = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
            question = payload["messages"][-1]["content"] if "messages" in payload else payload["question"]
            if not isinstance(question, str) or not question.strip():
                raise ValueError("question must be nonempty text")
            # Fixed seed makes the upstream rule's choice reproducible. The server is serial.
            random.seed(0)
            answer = eliza_chatbot.respond(question)
            body = {"response": answer, "model": "nltk-eliza", "implementation": "rule-based"}
            if self.path == "/v1/chat/completions":
                body = {"model": "nltk-eliza", "choices": [{"message": {"role": "assistant", "content": answer}}]}
            encoded = json.dumps(body).encode()
        except (ValueError, KeyError, IndexError, TypeError):
            self.send_error(400, "Expected a question or chat messages")
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    # Purpose: avoid logging conversational data in the test endpoint console.
    def log_message(self, format, *args):
        pass


# Purpose: start a local-only sample chatbot endpoint using the upstream ELIZA implementation.
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()
    with HTTPServer(("127.0.0.1", args.port), ElizaHandler) as server:
        print(f"NLTK ELIZA listening at http://127.0.0.1:{args.port}/chat", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()
