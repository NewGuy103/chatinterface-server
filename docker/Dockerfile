FROM python:3.12
LABEL org.opencontainers.image.source=https://github.com/newguy103/chatinterface-server
LABEL org.opencontainers.image.licenses=MPL-2.0

WORKDIR /app

RUN mkdir /opt/chatinterface-server
COPY app /app/app/

COPY requirements.txt /app/
COPY static /app/static

COPY templates /app/templates

RUN pip install --no-cache-dir --no-input -r requirements.txt
EXPOSE 8000

ENTRYPOINT [ "fastapi", "run", "app/main.py" ]
CMD [ "--host", "0.0.0.0", "--port", "8000" ]
