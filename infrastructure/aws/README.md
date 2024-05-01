# Infrastructure FAQs 

## Architecture
<img src="architecture_diagram.svg" width="50%"/>

### Private infrastructure configuration
* Sensitive variables are stored in this private repository: https://github.com/i-dot-ai/redbox-copilot-infra-config
  * When applying terraform make sure that repo is cloned locally
* A local example can be found in (./example-input-params.tfvars)[./example-input-params.tfvars]