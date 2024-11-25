# AI Tests

This workspace runs Redbox over a set of prompts and documents to allow investigating decision making and responses.

The setup is:

* Create a csv with prompts,documents fields in data/
* Drop all your test documents in data/documents
* Fill out the csv with a prompt and list of documents per row (is a list of document names separated by |)
* Run the test to produce traces in Langfuse and logs in data/output


