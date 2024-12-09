from redbox.app import Redbox

app = Redbox()

for g in ["root", "chat/documents", "chat/documents/large"]:
    app.draw(graph_to_draw=g, output_path=f"../docs/architecture/graph/{g.replace('/', '_')}.png")
