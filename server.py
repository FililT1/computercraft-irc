#!/usr/bin/env python3

import sys
import json
import argparse
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

from transliterate import translit
from ircagent import IRCAgent

debugmode = False
agent = None

class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        query_params = parse_qs(parsed_path.query)
        
        if parsed_path.path == "/":
            self.respond(200, "You were never here.")
        elif parsed_path.path == "/status":
            self.respond(200, "Not implemented")
        elif parsed_path.path == "/messages":
            start = query_params.get("start", [None])[0]
            end = query_params.get("end", [None])[0]
            print(f"Start: {start}, End: {end}")
            m = agent.getMessages(start, end)
            d = {row[0]: {"nick": row[1], "message": translit(row[2], 'ru', reversed=True)} for row in m}
            self.respond(200, json.dumps(d))
        elif parsed_path.path == "/users":
            users = agent.getUsers()
            d = {idx: row for idx, row in enumerate(users)}
            self.respond(200, json.dumps(d))
        elif parsed_path.path == "/ops":
            ops = agent.getOps()
            d = {idx: row for idx, row in enumerate(ops)}
            self.respond(200, json.dumps(d))
        elif parsed_path.path == "/halfops":
            halfops = agent.getHalfOps()
            d = {idx: row for idx, row in enumerate(halfops)}
            self.respond(200, json.dumps(d))
        elif parsed_path.path == "/voiced":
            voiced = agent.getVoiced()
            d = {idx: row for idx, row in enumerate(voiced)}
            self.respond(200, json.dumps(d))
        else:
            self.respond(404, "Not found")
    
    def do_POST(self):
        if self.path == "/sendmessage":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length).decode("utf-8")
            post_params = parse_qs(post_data)
            msg = post_params.get("msg", [None])[0]
            if msg:
                agent.sendMessage(msg)
                self.respond(200, "Message sent")
            else:
                self.respond(400, "Missing message parameter")
        else:
            self.respond(404, "Not found")
    
    def respond(self, status_code, message):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(message.encode("utf-8"))

def start(server, port, channel, nick, local, debug):
    global agent, debugmode
    debugmode = debug
    agent = IRCAgent(server, port, channel, nick)
    t = threading.Thread(target=agent.start, daemon=True)
    t.start()
    host = '127.0.0.1' if local or debug else '0.0.0.0'
    httpd = HTTPServer((host, 5001), RequestHandler)
    print(f"Starting server on {host}:5001")
    httpd.serve_forever()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Bridge IRC and HTTP')
    parser.add_argument('server', type=str, help='IRC server e.g. irc.freenode.net')
    parser.add_argument('port', type=int, help='IRC server port e.g. 6667')
    parser.add_argument('channel', type=str, help='IRC channel e.g. #test')
    parser.add_argument('-nick', type=str, nargs='?', default='mcagent', help='IRC agent nick (default: mcagent)')
    parser.add_argument('--local', action='store_true', help='Make server only visible to localhost')
    parser.add_argument('--debug', action='store_true', help='Use debug mode (forces --local)')
    args = parser.parse_args()
    start(args.server, args.port, "#B-IRC", args.nick, args.local, args.debug)
