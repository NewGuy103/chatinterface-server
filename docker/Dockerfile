FROM python:3.12
WORKDIR /app

RUN mkdir /opt/chatinterface-server
COPY chatinterface_server /app/chatinterface_server/

COPY requirements.txt /app/
COPY static /app/static

COPY templates /app/templates

RUN pip install --no-cache-dir --no-input -r requirements.txt
EXPOSE 8000

ENTRYPOINT [ "uvicorn", "chatinterface_server.main:app" ]
CMD [ "--host", "0.0.0.0", "--port", "8000" ]
