"""Keep render/server errors, allowing an expected disconnect during a clean local shutdown."""
import re
ERROR=re.compile(r"/(ERROR|FATAL)\]|Exception")
DISCONNECT=re.compile(r"^\[\d\d:\d\d:\d\d\] \[Server thread/INFO\]: Woodwalker lost connection: Internal Exception: java\.nio\.channels\.ClosedChannelException$")

def client_errors(log):
    lines=log.splitlines()
    stop=next((i for i,line in enumerate(lines) if line.endswith("[Render thread/INFO]: Stopping!")),len(lines))
    saved=next((i for i,line in enumerate(lines) if i>stop and "All dimensions are saved" in line),-1)
    return [line for i,line in enumerate(lines) if ERROR.search(line) and
            not (stop<i<saved and DISCONNECT.fullmatch(line))][:20]

def saved_without_errors(record, folder):
    if not record["logErrors"]: return True
    log=(folder/"client.log").read_text()
    original=[line for line in log.splitlines() if ERROR.search(line)][:20]
    return original==record["logErrors"] and not client_errors(log)
