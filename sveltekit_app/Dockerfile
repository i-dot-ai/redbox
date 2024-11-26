FROM node:20

WORKDIR /app

COPY sveltekit_app/package.json  ./
RUN npm install

COPY sveltekit_app/ ./
RUN npm run build

USER node:node

ENV PORT=3001
EXPOSE 3001

CMD ["node", "build/index.js"]
