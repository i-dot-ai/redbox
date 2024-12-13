# Use the existing image as the base image
FROM quay.io/unstructured-io/unstructured-api:latest

# Expose port 8080
EXPOSE 8080

CMD ["uvicorn", "app:main", "--host", "0.0.0.0", "--port", "8080"]
