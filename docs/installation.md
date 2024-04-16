# Installation

## Requirements
-  [Docker](https://docs.docker.com/get-docker/)
-  [Docker Compose](https://docs.docker.com/compose/install/)

## Installation
1. Clone the repository
    ```bash
    git clone git@github.com:i-dot-ai/redbox-copilot.git
    cd redbox-copilot
    ```
2. Create a `.env` file in the root directory of the project and add the following environment variables
    ```bash
    cp .env.example .env
    ```
    - `OPENAI_API_KEY` - OpenAI API key
    - `ANTHROPIC_API_KEY` - Anthropic API key
3. Build the docker containers
    ```bash
    docker-compose build
    ```
4. Run the docker containers
    ```bash
    make run
    ```

## Development Recommended Tools
- [Python 3.11](https://www.python.org/downloads/)
- [poetry](https://python-poetry.org/docs/)
- [Visual Studio Code](https://code.visualstudio.com/)
- [Git](https://git-scm.com/)
- [Make](https://www.gnu.org/software/make/)
