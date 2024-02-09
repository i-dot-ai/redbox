# Ask AI/Redbox Frontend Prototype

Using the Prototype Kit to move Redbox Copilot over to the gov.uk design system. The intention is to also allow for future merging with Ask AI.

## How to run

Ensure you have a recent version of Node.js installed (v16 or greater). Then run:
`npm install`

To start development server:
`npm run dev`

Start at http://localhost:3000/

## Notes

* The sign-in and sign-up process shows the required steps, but doesn't require any input, to enable quick access to the main prototypes.
* The upload documents journey is functional, but doesn't actually upload documents anywhere. It just stores the filenames locally.
* AI responses are just demo generic responses.
* The original prototype has been kept in for reference, but doesn't have most of the functionality contained in the 2 new prototypes.

## How to deploy to a new Beanstalk instance

1. create an initial build to deploy `make zip`
2. follow this guide https://www.freecodecamp.org/news/how-to-use-elastic-beanstalk-to-deploy-node-js-app/, upload your `deployment.zip` from step 1 as your initial code.
3. set your environment variables to be:
   * `NODE_ENV=development` (not production unless you have a domain and SSL certificate)
   * `PORT=8080`