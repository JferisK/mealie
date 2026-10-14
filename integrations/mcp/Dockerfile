FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml /app/
RUN pip install --no-cache-dir 'mcp==1.26.0' 'httpx==0.28.1' 'uvicorn==0.34.3'
COPY server.py /app/
ENV MCP_TRANSPORT=streamable-http
USER 65534:65534
EXPOSE 8080
CMD ["python", "server.py"]
