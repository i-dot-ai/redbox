from langchain_core.runnables import RunnablePassthrough

from redbox.app import Redbox

app = Redbox(retriever=RunnablePassthrough())

for g in ["root", "chat/documents"]:
    app.draw(graph_to_draw=g, output_path=f"../docs/architecture/graph/{g.replace('/', '_')}.png")
