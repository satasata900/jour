FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Just keep the container running if something fails so we can debug, 
# but normally this should just start vite.
CMD ["npm", "run", "dev", "--", "--host"]
