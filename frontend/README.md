# Getting Started with Create React App

This project was bootstrapped with [Vite](https://github.com/vitejs/vite).

## Setup Server

### Install Nvm

```
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.2/install.sh | bash
```

### Install node 20.12.2 and set default

```
nvm install 20.12.2\
nvm alias default 20.12.2
```

### Install Packages

```
npm install
```

## To Build Files for NGINX to Serve

```
npm run build
```

Builds the app to the `build` folder. Allows nginx to serve files. Rerun the command upon changing the frontend files to see changes on site.
