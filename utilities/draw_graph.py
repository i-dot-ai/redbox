from redbox.app import Redbox

app = Redbox()

for g in ["root", "search/agentic", "chat/documents"]:
    app.draw(graph_to_draw=g, output_path=f"../docs/architecture/graph/{g.replace('/', '_')}.png")
