import express from 'express';
import { html, render } from '@lit-labs/ssr';
import { unsafeHTML } from 'lit-html/directives/unsafe-html.js';

// import components
// TO DO: How can we import these automatically?
import { ActivityButton } from '../django_app/frontend/src/js/web-components/chats/activity-button-lit.mjs';

const app = express();

app.use((req, res, next) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  next();
});

app.get('/', async (req, res) => {
  //console.log("Input", req.query.data);
  const rendered = [...render(html`${unsafeHTML(req.query.data)}`)]
    .join("")
    .replace(/<template shadowroot="open" shadowrootmode="open">/g, '')
    .replace(/<\/template>/g, '')
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace("<?>", "");
  //console.log("Output", rendered);
  res.send(rendered);
});

app.listen(3002, () => {
  console.log('Server is running on port 3002');
});
