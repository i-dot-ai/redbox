ARG NODE_VERSION=21.3.0

FROM node:${NODE_VERSION}-alpine as base
WORKDIR /usr/src/app
EXPOSE 3000
COPY . .
RUN npm install

CMD npm run dev