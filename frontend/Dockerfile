FROM node:20-slim
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build
EXPOSE 3000
ENV PORT=3000
CMD ["node", "build"]
