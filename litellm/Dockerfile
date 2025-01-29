# The only point of this tedious process is to add the config.yml to the image,
# better ideas are very welcome.
#
# Code borrowed from https://docs.litellm.ai/docs/proxy/deploy#use-litellm-as-a-base-image

# Use the provided base image
FROM ghcr.io/berriai/litellm:main-latest

# Set the working directory to /app
WORKDIR /app

# Copy the configuration file into the container at /app
COPY litellm/config.yml .

# Make sure your docker/entrypoint.sh is executable
RUN chmod +x ./docker/entrypoint.sh

# Expose the necessary port
EXPOSE 4000/tcp

# Override the CMD instruction with your desired command and arguments
# WARNING: FOR PROD DO NOT USE `--detailed_debug` it slows down response times, instead use the following CMD
# CMD ["--port", "4000", "--config", "config.yml"]

CMD ["--port", "4000", "--config", "config.yml", "--detailed_debug"]