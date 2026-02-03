FROM node:20-alpine

WORKDIR /app

RUN apk add --no-cache git

COPY package.json package-lock.json* ./
RUN npm install --omit=dev

COPY . ./

CMD ["npm", "start"]
