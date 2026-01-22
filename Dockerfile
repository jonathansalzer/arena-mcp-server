FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .

# first install the deps, as a separate call to keep as much docker layer cache as possible
RUN pip install -e .

COPY src/ src/

# now setup the call to server, not installing the deps
RUN pip install --no-deps .

CMD ["arena-mcp-server"]
