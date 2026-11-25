# Multi-stage Dockerfile for React Frontend

# Stage 1: Build the React application with Vite
FROM node:20-alpine AS builder

WORKDIR /app

# Build-time argument for backend API base URL
ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

# Stage 2: Serve production assets via Nginx
FROM nginx:alpine AS runner

# Copy custom nginx configuration for SPA routing
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy compiled static assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
