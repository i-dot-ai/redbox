import express from 'express';
import { html, render } from '@lit-labs/ssr';
import { unsafeHTML } from 'lit-html/directives/unsafe-html.js';
import DOMPurify from 'dompurify';
import { JSDOM } from 'jsdom';

// import components
// TO DO: How can we import these automatically?
import { ActivityButton } from '../django_app/frontend/src/js/web-components/chats/activity-button-lit.mjs';
import { ActionButtons } from '../django_app/frontend/src/js/web-components/chats/action-buttons.mjs';

const window = new JSDOM('').window;
const purify = DOMPurify(window);

const app = express();

app.use((req, res, next) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  next();
});

app.get('/', async (req, res) => {
  //console.log("Input", req.query.data);
  const renderedHtml = [...render(html`${unsafeHTML(req.query.data)}`)]
    .join("")
    .replace(/<template shadowroot="open" shadowrootmode="open">/g, '')
    .replace(/<\/template>/g, '');

  const sanitisedHtml = purify.sanitize(renderedHtml, {
    ADD_TAGS: ['activity-button', 'action-buttons'],
  });
  
  //console.log("Output", sanitisedHtml);
  res.send(sanitisedHtml);
});

app.listen(3002, () => {
  console.log('Server is running on port 3002');
});
