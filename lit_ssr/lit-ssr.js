import express from "express";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { html, render } from "@lit-labs/ssr";
import { unsafeHTML } from "lit-html/directives/unsafe-html.js";
import DOMPurify from "dompurify";
import { JSDOM } from "jsdom";

const COMPONENTS_DIRECTORY = "../django_app/frontend/src/js/web-components";

let components = [];
const window = new JSDOM("").window;
const purify = DOMPurify(window);
const app = express();

// Import components
(() => {
  const __filename = fileURLToPath(import.meta.url);
  const __dirname = path.dirname(__filename);
  const directoryPath = path.join(__dirname, COMPONENTS_DIRECTORY);

  const capitalise = (str) => {
    return str.charAt(0).toUpperCase() + str.slice(1);
  };

  const readFiles = (dir) => {
    fs.readdirSync(dir).forEach((file) => {
      const filePath = path.join(dir, file);
      const stat = fs.statSync(filePath);

      if (stat.isDirectory()) {
        // Recursively read sub-directory
        readFiles(filePath);
      } else if (stat.isFile()) {
        if (!filePath.endsWith(".mjs")) {
          return;
        }

        // Get component tag, so we can tell DomPurify to allow it
        const componentTag = path.basename(filePath).replace(".mjs", ""); // Get the filename without the full path
        components.push(componentTag);

        // Dynamically import componentName from filePath
        import(filePath)
          .then((module) => {
            console.log(`Imported <${componentTag}> from ${filePath}`);
          })
          .catch((error) => {
            console.error(`Failed to import component from ${filePath}`, error);
          });
      }
    });
  };

  readFiles(directoryPath);
})();

app.use((req, res, next) => {
  res.setHeader("Access-Control-Allow-Origin", "*");
  next();
});

app.get("/", async (req, res) => {
  //console.log("Input", req.query.data);
  const renderedHtml = [...render(html`${unsafeHTML(req.query.data)}`)]
    .join("")
    .replace(/<template shadowroot="open" shadowrootmode="open">/g, "")
    .replace(/<\/template>/g, "");

  const sanitisedHtml = purify.sanitize(renderedHtml, {
    ADD_TAGS: components,
  });

  //console.log("Output", sanitisedHtml);
  res.send(sanitisedHtml);
});

app.listen(3002, () => {
  console.log("Server is running on port 3002");
});
