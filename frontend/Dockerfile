
FROM node:20-alpine

WORKDIR /app
COPY package.json package-lock.json tsconfig.json vite.config.ts index.html /app/
COPY src /app/src

RUN npm ci && npm run build

EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
