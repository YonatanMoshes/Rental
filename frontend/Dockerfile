# Frontend Docker Image
# 
# Multi-stage build:
#   1. Build stage: Node.js - compiles React/TypeScript to static files
#   2. Runtime stage: Nginx - serves static files
# 
# This approach keeps final image size small (~100MB vs 500MB+ with Node.js)
# 
# Build: docker build -f frontend/Dockerfile -t rental-frontend .
# Run:   docker run -p 80:80 rental-frontend

# Stage 1: Build React application
FROM node:22-alpine AS build

WORKDIR /app

# Copy package files and install dependencies
COPY package.json package-lock.json ./
RUN npm ci

# Copy source files and config
COPY index.html tsconfig.json tsconfig.node.json vite.config.ts ./
COPY src ./src

# Build optimized production bundle
RUN npm run build

# Stage 2: Runtime - Nginx server
FROM nginx:1.27-alpine

# Copy Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built files from build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Expose HTTP port
EXPOSE 80
