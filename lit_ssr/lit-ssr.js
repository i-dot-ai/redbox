import express from 'express';
import { html, render } from '@lit-labs/ssr';
import { unsafeHTML } from 'lit-html/directives/unsafe-html.js';

// import components
import { ActivityButton } from '../django_app/frontend/src/js/web-components/chats/activity-button-lit.mjs';
import { CurrentTime } from '../django_app/frontend/src/js/web-components/chats/current-time.mjs';

const app = express();

app.use((req, res, next) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  next();
});

//app.use(express.json());

app.get('/', async (req, res) => {
  const myValue = `<h1>Test</h1>${req.query.data}<h2>A second component</h2><current-time></current-time><activity-button></activity-button>`;

  const rendered = [...render(html`${unsafeHTML(myValue)}`)]
    .join("")
    .replace(/<template shadowroot="open" shadowrootmode="open">/g, '')
    .replace(/<\/template>/g, '')
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace("<?>", "");
  console.log(rendered);
 
  res.send(rendered);
});

/*
app.post('/', (req, res) => {
  console.log(req.body);
  const html = res.json(req.body).data;
  console.log("Getting data from sender:");
  console.log(html);

  const rendered = render(html`${html}`)
    .join("")
    .replace('<template shadowroot="open" shadowrootmode="open">', '')
    .replace('</template>', '');

  console.log("Sending rendered data:");
  console.log(rendered);
 
  res.send(rendered);
});
*/

app.listen(3002, () => {
  console.log('Server is running on port 3002');
});



/**
 * fetch("http://localhost:3000/", {
  method: 'POST',
  headers: {
    'Content-Type': 'text/json',
  },
  body: "{data: '<activity-button></activity-button>'}"
})
 */
