FROM python:3.14
WORKDIR /usr/local/app

# Install the application dependencies
COPY requirements.txt ./

RUN apt update
RUN apt install libusb-dev -y


RUN pip install --no-cache-dir -r requirements.txt
RUN pip install "setuptools<=80.10.2"
# Copy in the source code
COPY src/main.py ./app/main.py
COPY src/test.py ./app/test.py
COPY src/customtypes.py ./app/customtypes.py
COPY src/models.py ./app/models.py
COPY src/utils ./app/utils
EXPOSE 8000

# CMD ["sleep", "1000000"]
CMD ["python", "./app/main.py"]
