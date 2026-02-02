# Multi-stage build for React frontend

# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Build for production
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx config template
COPY nginx.conf /etc/nginx/templates/default.conf.template

# Expose port (Railway sets $PORT)
EXPOSE 80

# nginx docker image automatically substitutes env vars in templates
CMD ["nginx", "-g", "daemon off;"]
