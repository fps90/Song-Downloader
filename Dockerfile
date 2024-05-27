FROM python:3.9
WORKDIR /app
COPY . /app/
RUN pip3 install --no-cache-dir -U -r requirements.txt
CMD ["python", "bot.py"]
