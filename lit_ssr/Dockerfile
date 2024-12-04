FROM node:20

WORKDIR /app

COPY lit_ssr/package.json  ./
RUN npm install

COPY lit_ssr/lit-ssr.js  ./server/lit-ssr.js
COPY django_app/frontend/src/js/web-components  ./django_app/frontend/src/js/web-components

USER node:node

ENV PORT=3002
EXPOSE 3002

CMD ["node", "./server/lit-ssr.js"]
