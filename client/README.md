# Chemistry Dashboard Client

## AngularCLI Installation

1. Install nodejs and npm:
```
curl -sL https://deb.nodesource.com/setup_14.x | sudo -E bash -
sudo apt-get install -y nodejs
```

2. Create npm globals folder:
```
mkdir ~/.npm-global
npm config set prefix '~/.npm-global'
```

3. Edit profile to point to npm globals:
```
nano ~/.profile

then add this line at the bottom of the file:
export PATH=~/.npm-global/bin:$PATH
```

4. Install the node packages and angularCLI:
```
source ~/.profile
npm install -g node-gyp
npm install -g @angular/cli
```

5. Install node_modules into the project:
```
cd ~/chemistry-dashboard/client
npm install
```

If any of the previous commands state that you do not have write access to .npm or .npm-global, do the following:
```
sudo chmod -R 777 ~/.npm
sudo chmod -R 777 ~/.npm-global
```

## Development server

Using the following command will allow you to rebuild whenever a file is changed.  The new build will automatically be served by the server (provided it is running - discussion_capture.service).
Note: you will need to refresh your browser and set it to not cache in order to see changes after rebuilding.

```
$ ng build --watch
```

Before committing changes to the repository, it is recommended that you perform a production build (See "Build" section below) as this will have stricter policies and catch additional errors.

## Code scaffolding

Run `ng generate component component-name` to generate a new component. You can also use `ng generate directive|pipe|service|class|guard|interface|enum|module`.

## Build

Run `ng build --aot --prod` to make a production build.

## Running unit tests

Run `ng test` to execute the unit tests via [Karma](https://karma-runner.github.io).

## Running end-to-end tests

Run `ng e2e` to execute the end-to-end tests via [Protractor](http://www.protractortest.org/).

## Further help

To get more help on the Angular CLI use `ng help` or go check out the [Angular CLI README](https://github.com/angular/angular-cli/blob/master/README.md).
