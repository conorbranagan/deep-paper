FROM node:18-alpine

WORKDIR /app

# Copy frontend code
COPY frontend/ .

# Install dependencies
RUN npm ci

# Build the Next.js application
RUN npm run build

# Railway automatically assigns port via PORT env variable
EXPOSE ${PORT:-3000}

# Command to run the application
CMD npm start -- -p ${PORT:-3000}